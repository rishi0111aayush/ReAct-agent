"""
agent.py — ReAct agent loop for Boozo.ai.

Orchestrates the Thought → Action → Observation cycle.
Yields SSE-ready event dicts consumed by the /chat route.
"""
import re
import time
from typing import Generator

from app import config
from app.providers import call_groq_stream, call_llm
from app.prompts import SYSTEM_PROMPT, REACT_TEMPLATE
from app.tools import dispatch_tool, set_user_context


def _parse_llm_output(text: str) -> dict:
    """Parse LLM output into structured parts (thought / action / final_answer)."""
    thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|Final Answer:|$)', text, re.DOTALL)
    action_match  = re.search(r'Action:\s*(.+?)(?=Thought:|Observation:|Final Answer:|$)', text, re.DOTALL)
    answer_match  = re.search(r'Final Answer:\s*(.+)', text, re.DOTALL)
    return {
        "thought":      thought_match.group(1).strip() if thought_match else None,
        "action":       action_match.group(1).strip()  if action_match  else None,
        "final_answer": answer_match.group(1).strip()  if answer_match  else None,
    }


def run_agent(
    user_message:   str,
    history:        list[dict],
    image_data_url: str | None = None,
    image_mime:     str | None = None,
    selected_model: str | None = None,
    user_id:        str | None = None,
) -> Generator[dict, None, None]:
    """
    Run the ReAct agent loop. Yields SSE-ready event dicts:
      {type: "thought"|"action"|"observation"|"answer_token"|"done"|"error", content: str}
    """
    set_user_context(user_id)

    history_str = ""
    for turn in history[-10:]:
        history_str += f"User: {turn['user']}\nAssistant: {turn['assistant']}\n\n"

    scratchpad = ""

    for iteration in range(config.MAX_ITERATIONS):
        prompt = REACT_TEMPLATE.format(
            system=SYSTEM_PROMPT,
            history=history_str,
            user_message=user_message,
            scratchpad=scratchpad,
        )

        yield {"type": "iteration", "n": iteration + 1, "max": config.MAX_ITERATIONS}
        yield {"type": "tokens",    "used": len(prompt) // 4, "limit": config.NUM_CTX}

        t0             = time.time()
        img            = image_data_url if iteration == 0 else None
        llm_output     = ""
        model_used     = None
        streamed_final = False
        _FINAL         = "Final Answer:"

        use_stream = config.GROQ_API_KEY and (
            not selected_model or selected_model.startswith("groq:")
        )

        if use_stream:
            try:
                _in_final = False
                for token in call_groq_stream(prompt, img):
                    llm_output += token
                    if not _in_final and _FINAL in llm_output:
                        _in_final      = True
                        streamed_final = True
                        after = llm_output[llm_output.index(_FINAL) + len(_FINAL):].lstrip("\n ")
                        if after:
                            yield {"type": "answer_token", "content": after}
                    elif _in_final:
                        yield {"type": "answer_token", "content": token}
                model_used = f"groq:{config.GROQ_MODEL}"
            except Exception as stream_err:
                llm_output     = ""
                streamed_final = False
                if "429" in str(stream_err):
                    yield {"type": "error", "content": "Groq rate limit hit. Please wait a moment."}
                    return

        if not llm_output:
            try:
                llm_output, model_used = call_llm(prompt, img, selected_model)
            except Exception as e:
                msg = str(e)
                if "429" in msg:
                    yield {"type": "error", "content": "Rate limit hit on all providers. Please wait."}
                elif "10061" in msg or "connection refused" in msg.lower():
                    yield {"type": "error", "content": "All cloud providers failed. Check your API keys."}
                else:
                    yield {"type": "error", "content": f"All LLM providers failed: {e}"}
                return

        yield {"type": "timing",     "who": "llm", "ms": int((time.time() - t0) * 1000)}
        yield {"type": "model_used", "content": model_used}

        parsed = _parse_llm_output(llm_output)

        if parsed["thought"]:
            yield {"type": "thought",    "content": parsed["thought"]}
            scratchpad += f"Thought: {parsed['thought']}\n"
            yield {"type": "scratchpad", "content": scratchpad}

        if parsed["final_answer"]:
            answer = parsed["final_answer"]
            if not streamed_final:
                for char in answer:
                    yield {"type": "answer_token", "content": char}
            yield {"type": "done", "content": answer}
            return

        if parsed["action"]:
            yield {"type": "action", "content": parsed["action"]}
            scratchpad += f"Action: {parsed['action']}\n"

            tool_name   = parsed["action"].split("(")[0].strip()
            t0          = time.time()
            observation = dispatch_tool(parsed["action"])
            yield {"type": "timing", "who": tool_name, "ms": int((time.time() - t0) * 1000)}

            if observation.startswith("CHART:"):
                yield {"type": "chart",      "content": observation[6:]}
                scratchpad += "Observation: Chart rendered.\n\n"
            else:
                yield {"type": "observation", "content": observation}
                scratchpad += f"Observation: {observation}\n\n"
            yield {"type": "scratchpad", "content": scratchpad}
        else:
            answer = llm_output.strip()
            if not answer:
                yield {"type": "error", "content": "Agent produced no action or final answer."}
                return
            if not streamed_final:
                for char in answer:
                    yield {"type": "answer_token", "content": char}
            yield {"type": "done", "content": answer}
            return

    yield {"type": "error", "content": "Agent reached maximum iterations without a final answer."}
