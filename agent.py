import re
import httpx
from typing import Generator
from prompts import SYSTEM_PROMPT, REACT_TEMPLATE
from tools import dispatch_tool

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"
MAX_ITERATIONS = 5


def call_ollama(prompt: str) -> str:
    """Call Ollama synchronously and return the full response text."""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 1024},
    }
    resp = httpx.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["response"]


def parse_llm_output(text: str) -> dict:
    """
    Parse LLM output into structured parts.
    Returns dict with keys: thought, action, final_answer (any can be None).
    """
    thought = None
    action = None
    final_answer = None

    thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|Final Answer:|$)', text, re.DOTALL)
    action_match = re.search(r'Action:\s*(.+?)(?=Thought:|Observation:|Final Answer:|$)', text, re.DOTALL)
    answer_match = re.search(r'Final Answer:\s*(.+)', text, re.DOTALL)

    if thought_match:
        thought = thought_match.group(1).strip()
    if action_match:
        action = action_match.group(1).strip()
    if answer_match:
        final_answer = answer_match.group(1).strip()

    return {"thought": thought, "action": action, "final_answer": final_answer}


def run_agent(user_message: str, history: list[dict]) -> Generator[dict, None, None]:
    """
    Run the ReAct agent loop. Yields SSE-ready event dicts:
      {type: "thought" | "action" | "observation" | "answer_token" | "done" | "error", content: str}
    """
    # Build conversation history string
    history_str = ""
    for turn in history:
        history_str += f"User: {turn['user']}\nAssistant: {turn['assistant']}\n\n"

    scratchpad = ""

    for iteration in range(MAX_ITERATIONS):
        prompt = REACT_TEMPLATE.format(
            system=SYSTEM_PROMPT,
            history=history_str,
            user_message=user_message,
            scratchpad=scratchpad,
        )

        try:
            llm_output = call_ollama(prompt)
        except Exception as e:
            yield {"type": "error", "content": f"Ollama error: {e}"}
            return

        parsed = parse_llm_output(llm_output)

        # Emit thought
        if parsed["thought"]:
            yield {"type": "thought", "content": parsed["thought"]}
            scratchpad += f"Thought: {parsed['thought']}\n"

        # Final answer — stream it token by token
        if parsed["final_answer"]:
            answer = parsed["final_answer"]
            for char in answer:
                yield {"type": "answer_token", "content": char}
            yield {"type": "done", "content": answer}
            return

        # Tool call
        if parsed["action"]:
            yield {"type": "action", "content": parsed["action"]}
            scratchpad += f"Action: {parsed['action']}\n"

            observation = dispatch_tool(parsed["action"])
            yield {"type": "observation", "content": observation}
            scratchpad += f"Observation: {observation}\n\n"
        else:
            # No action and no final answer — force finish
            yield {"type": "error", "content": "Agent produced no action or final answer."}
            return

    # Hit max iterations
    yield {"type": "error", "content": "Agent reached maximum iterations without a final answer."}
