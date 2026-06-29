# MiniGPT Agent — Design Document
Date: 2026-06-28

## Goal

Build a small-scale AI agent to understand how LLMs + ReAct agent loops work,
with an outstanding AI-themed UI that exposes the agent's internals in real time.
Learning-first: every component is written from scratch, no agent frameworks.

---

## Stack

- **Backend**: Python + FastAPI
- **LLM**: Ollama (local, free) — llama3 or mistral
- **Frontend**: Single `index.html` — pure HTML + CSS + vanilla JS (no build tools)
- **Streaming**: Server-Sent Events (SSE) for real-time event push

---

## Architecture

```
Browser (HTML/JS)
  ├── Chat Panel         — displays conversation, streams final answer
  └── Agent Brain Panel  — live ReAct loop (thought → action → observation)
        │
        │ SSE stream
        ▼
FastAPI Backend
  ├── /chat endpoint     — accepts user message, opens SSE stream
  ├── ReAct Agent Loop   — Reason → Act → Observe → Repeat (max 5 iterations)
  ├── Tool Dispatcher
  │     ├── web_search   — DuckDuckGo (no API key)
  │     ├── code_exec    — Python sandbox (exec with restricted globals)
  │     └── calculator   — safe math eval
  └── Ollama client      — HTTP calls to local Ollama server
```

---

## ReAct Agent Loop

Each iteration:
1. Build prompt: system prompt + conversation history + tool definitions + prior steps
2. Call Ollama — parse output for `Thought:` / `Action:` / `Final Answer:`
3. Emit SSE event: `{type: "thought" | "action" | "observation" | "answer", content: "..."}`
4. If action: dispatch tool, get observation, append to context, loop
5. If final answer: stream tokens one by one via SSE, close stream

Max iterations: 5 (prevents infinite loops)

---

## Tools

| Tool | Implementation | Purpose |
|------|---------------|---------|
| `web_search(query)` | DuckDuckGo HTML scrape, no key | Search the web |
| `code_exec(code)` | Python `exec()` with restricted `__builtins__` | Run Python code |
| `calculator(expr)` | `ast.literal_eval` safe math | Evaluate math expressions |

---

## UI/UX Design

**Theme**: Dark (deep navy/black), cyan + purple accent glows

**Layout**: Two-panel split
- Left: Chat panel — conversation history + streaming answer
- Right: Agent Brain panel — live ReAct steps with fade-in animations

**AI-themed features**:
- Typewriter streaming effect for final answer
- Each ReAct step slides in with fade animation
- Pulsing glow on tool calls while running
- Animated gradient border on brain panel during thinking
- Syntax highlighting for code blocks (highlight.js via CDN)
- Model name + status indicator in header

---

## File Structure

```
minigpt/
├── main.py           # FastAPI app, /chat SSE endpoint
├── agent.py          # ReAct loop logic
├── tools.py          # web_search, code_exec, calculator
├── prompts.py        # system prompt + ReAct prompt template
└── static/
    └── index.html    # entire frontend
```

---

## Success Criteria

- Send a tech question → see Thought/Action/Observation steps appear live in the brain panel
- Final answer streams character by character in the chat panel
- All three tools demonstrably callable by the agent
- Runs fully offline after initial Ollama model pull
