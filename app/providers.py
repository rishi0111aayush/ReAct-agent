"""
providers.py — LLM provider calls for Boozo.ai.

Supported providers (automatic fallback chain):
  Groq (streaming) → Cerebras → Gemini → Ollama

selected_model format: "provider:model_name"
  e.g. "groq:llama-3.3-70b-versatile", "gemini:gemini-2.0-flash"
"""
import json

import httpx

from app import config

# Mutable runtime model names — overridden when user picks a model
_models: dict[str, str] = {
    "groq":     config.GROQ_MODEL,
    "vision":   config.VISION_MODEL,
    "gemini":   config.GEMINI_MODEL,
    "cerebras": config.CEREBRAS_MODEL,
    "ollama":   config.OLLAMA_MODEL,
}


def call_groq(prompt: str, image_data_url: str | None = None) -> str:
    """Call Groq API (non-streaming). Raises on any error."""
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }
    if image_data_url:
        content = [
            {"type": "image_url", "image_url": {"url": image_data_url}},
            {"type": "text",      "text": prompt},
        ]
        model = _models["vision"]
    else:
        content = prompt
        model   = _models["groq"]

    payload = {
        "model":       model,
        "messages":    [{"role": "user", "content": content}],
        "temperature": config.LLM_TEMPERATURE,
        "max_tokens":  config.LLM_MAX_TOKENS,
    }
    resp = httpx.post(config.GROQ_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def call_groq_stream(prompt: str, image_data_url: str | None = None):
    """Stream tokens from Groq. Yields string tokens one at a time."""
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }
    content = prompt
    model   = _models["groq"]
    if image_data_url:
        content = [
            {"type": "image_url", "image_url": {"url": image_data_url}},
            {"type": "text",      "text": prompt},
        ]
        model = _models["vision"]

    payload = {
        "model":       model,
        "messages":    [{"role": "user", "content": content}],
        "temperature": config.LLM_TEMPERATURE,
        "max_tokens":  config.LLM_MAX_TOKENS,
        "stream":      True,
    }
    with httpx.stream("POST", config.GROQ_URL, json=payload, headers=headers, timeout=60) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data.strip() == "[DONE]":
                break
            try:
                token = json.loads(data)["choices"][0]["delta"].get("content") or ""
                if token:
                    yield token
            except Exception:
                continue


def call_cerebras(prompt: str) -> str:
    """Call Cerebras Cloud via OpenAI-compatible endpoint."""
    headers = {
        "Authorization": f"Bearer {config.CEREBRAS_API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       _models["cerebras"],
        "messages":    [{"role": "user", "content": prompt}],
        "temperature": config.LLM_TEMPERATURE,
        "max_tokens":  config.LLM_MAX_TOKENS,
    }
    resp = httpx.post(config.CEREBRAS_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def call_gemini(prompt: str) -> str:
    """Call Google AI Studio (Gemini) via OpenAI-compatible endpoint."""
    headers = {
        "Authorization": f"Bearer {config.GEMINI_API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       _models["gemini"],
        "messages":    [{"role": "user", "content": prompt}],
        "temperature": config.LLM_TEMPERATURE,
        "max_tokens":  config.LLM_MAX_TOKENS,
    }
    resp = httpx.post(config.GEMINI_URL, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def call_ollama(prompt: str) -> str:
    """Call local Ollama as last-resort fallback."""
    payload = {
        "model":   _models["ollama"],
        "prompt":  prompt,
        "stream":  False,
        "options": {
            "temperature": config.LLM_TEMPERATURE,
            "num_predict": 1_024,
            "num_ctx":     config.NUM_CTX,
        },
    }
    resp = httpx.post(config.OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["response"]


def call_llm(
    prompt:         str,
    image_data_url: str | None = None,
    selected_model: str | None = None,
) -> tuple[str, str]:
    """
    Route to the selected model. Fallback chain: Groq → Cerebras → Gemini → Ollama.
    Returns (response_text, model_label).
    """
    if selected_model:
        provider, _, model_name = selected_model.partition(":")
        if provider == "ollama":
            _models["ollama"] = model_name
            return call_ollama(prompt), f"ollama:{model_name}"
        if provider == "gemini" and model_name:
            _models["gemini"] = model_name
            return call_gemini(prompt), f"gemini:{model_name}"
        if provider == "cerebras" and model_name:
            _models["cerebras"] = model_name
            return call_cerebras(prompt), f"cerebras:{model_name}"
        if provider == "groq" and model_name:
            _models["groq"] = model_name

    providers = [
        (lambda: call_groq(prompt, image_data_url), f"groq:{_models['groq']}"),
        (lambda: call_cerebras(prompt),              f"cerebras:{_models['cerebras']}"),
        (lambda: call_gemini(prompt),                f"gemini:{_models['gemini']}"),
        (lambda: call_ollama(prompt),                f"ollama:{_models['ollama']}"),
    ]
    for fn, label in providers:
        try:
            return fn(), label
        except Exception:
            continue

    raise RuntimeError(
        "All providers failed. Check GROQ_API_KEY, CEREBRAS_API_KEY, "
        "GEMINI_API_KEY, or ensure Ollama is running."
    )
