"""
agent.py — ReAct agent loop and LLM provider routing for Boozo.ai.

Providers (with automatic fallback): Groq → Cerebras → Gemini → Ollama
"""
import os
import re
import time
import httpx
from typing import Generator
from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT, REACT_TEMPLATE
from tools import dispatch_tool

load_dotenv()

GROQ_API_KEY     = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")

GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL    = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
CEREBRAS_URL  = "https://api.cerebras.ai/v1/chat/completions"
OLLAMA_URL    = "http://localhost:11434/api/generate"

MODEL          = "llama-3.3-70b-versatile"
VISION_MODEL   = "meta-llama/llama-4-scout-17b-16e-instruct"
GEMINI_MODEL   = "gemini-2.0-flash"
CEREBRAS_MODEL = "llama-3.3-70b"
OLLAMA_MODEL   = "llama3.2"

MAX_ITERATIONS = 5
NUM_CTX = 8192


def call_groq(prompt: str, image_data_url: str | None = None) -> str:
    """Call Groq API. Raises on any error."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    if image_data_url:
        content = [
            {"type": "image_url", "image_url": {"url": image_data_url}},
            {"type": "text", "text": prompt},
        ]
        model = VISION_MODEL
    else:
        content = prompt
        model = MODEL

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    resp = httpx.post(GROQ_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def call_cerebras(prompt: str) -> str:
    """Call Cerebras Cloud via OpenAI-compatible endpoint."""
    headers = {
        "Authorization": f"Bearer {CEREBRAS_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": CEREBRAS_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    resp = httpx.post(CEREBRAS_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def call_gemini(prompt: str) -> str:
    """Call Google AI Studio (Gemini) via OpenAI-compatible endpoint."""
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GEMINI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    resp = httpx.post(GEMINI_URL, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def call_ollama(prompt: str) -> str:
    """Call local Ollama as fallback."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 1024, "num_ctx": NUM_CTX},
    }
    resp = httpx.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["response"]


def call_llm(prompt: str, image_data_url: str | None = None, selected_model: str | None = None) -> tuple[str, str]:
    """
    Call the selected model. Fallback chain: Groq → Cerebras → Gemini → Ollama.
    selected_model format: "groq:<model>", "cerebras:<model>", "gemini:<model>", "ollama:<model>"
    Returns (response_text, label_for_ui).
    """
    global MODEL, GEMINI_MODEL, CEREBRAS_MODEL, OLLAMA_MODEL

    if selected_model:
        provider, _, model_name = selected_model.partition(":")
        if provider == "ollama":
            OLLAMA_MODEL = model_name
            return call_ollama(prompt), f"ollama:{model_name}"
        elif provider == "gemini" and model_name:
            GEMINI_MODEL = model_name
            return call_gemini(prompt), f"gemini:{model_name}"
        elif provider == "cerebras" and model_name:
            CEREBRAS_MODEL = model_name
            return call_cerebras(prompt), f"cerebras:{model_name}"
        elif provider == "groq" and model_name:
            MODEL = model_name

    # Groq → Cerebras → Gemini → Ollama fallback chain
    try:
        text = call_groq(prompt, image_data_url)
        return text, f"groq:{MODEL}"
    except Exception:
        pass

    try:
        text = call_cerebras(prompt)
        return text, f"cerebras:{CEREBRAS_MODEL}"
    except Exception:
        pass

    try:
        text = call_gemini(prompt)
        return text, f"gemini:{GEMINI_MODEL}"
    except Exception:
        return call_ollama(prompt), f"ollama:{OLLAMA_MODEL}"


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


def run_agent(user_message: str, history: list[dict], image_data_url: str | None = None, image_mime: str | None = None, selected_model: str | None = None) -> Generator[dict, None, None]:
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

        # Emit iteration start + token estimate
        yield {"type": "iteration", "n": iteration + 1, "max": MAX_ITERATIONS}
        yield {"type": "tokens", "used": len(prompt) // 4, "limit": NUM_CTX}

        try:
            t0 = time.time()
            img = image_data_url if iteration == 0 else None
            llm_output, model_used = call_llm(prompt, img, selected_model)
            yield {"type": "timing", "who": "llm", "ms": int((time.time() - t0) * 1000)}
            yield {"type": "model_used", "content": model_used}
        except Exception as e:
            yield {"type": "error", "content": f"All LLM providers failed: {e}"}
            return

        parsed = parse_llm_output(llm_output)

        # Emit thought
        if parsed["thought"]:
            yield {"type": "thought", "content": parsed["thought"]}
            scratchpad += f"Thought: {parsed['thought']}\n"
            yield {"type": "scratchpad", "content": scratchpad}

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

            tool_name = parsed["action"].split("(")[0].strip()
            t0 = time.time()
            observation = dispatch_tool(parsed["action"])
            yield {"type": "timing", "who": tool_name, "ms": int((time.time() - t0) * 1000)}

            if observation.startswith("CHART:"):
                chart_json = observation[6:]
                yield {"type": "chart", "content": chart_json}
                scratchpad += f"Observation: Chart rendered.\n\n"
            else:
                yield {"type": "observation", "content": observation}
                scratchpad += f"Observation: {observation}\n\n"
            yield {"type": "scratchpad", "content": scratchpad}
        else:
            # No action and no final answer — force finish
            yield {"type": "error", "content": "Agent produced no action or final answer."}
            return

    # Hit max iterations
    yield {"type": "error", "content": "Agent reached maximum iterations without a final answer."}
