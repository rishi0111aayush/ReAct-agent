# MiniGPT Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a learning-focused AI agent with a ReAct loop, three tools, and a live futuristic UI that exposes every agent step in real time.

**Architecture:** FastAPI backend runs a hand-written ReAct loop against a local Ollama LLM, streaming each thought/action/observation as SSE events. The frontend is a single index.html with a two-panel layout (chat + brain) that consumes the SSE stream.

**Tech Stack:** Python 3.10+, FastAPI, httpx, uvicorn, requests, beautifulsoup4, Ollama (local), vanilla HTML/CSS/JS, highlight.js (CDN)

---

## Prerequisites (do these manually before starting)

1. Install Ollama: https://ollama.com/download
2. Pull a model: `ollama pull llama3` (or `ollama pull mistral` if RAM < 16GB)
3. Verify Ollama runs: `ollama run llama3 "say hello"` — should print a response
4. Install Python deps:
   ```bash
   pip install fastapi uvicorn httpx requests beautifulsoup4 python-multipart
   ```

---

### Task 1: Project Scaffold

**Files:**
- Create: `main.py`
- Create: `agent.py`
- Create: `tools.py`
- Create: `prompts.py`
- Create: `static/index.html`

**Step 1: Create the directory structure**

```bash
cd C:\Users\aryan\Desktop\minigpt
mkdir -p static
```

**Step 2: Create empty placeholder files**

Create each file listed above with a single comment line so git can track them. We'll fill them in subsequent tasks.

`main.py`:
```python
# FastAPI entry point
```

`agent.py`:
```python
# ReAct agent loop
```

`tools.py`:
```python
# Tool implementations
```

`prompts.py`:
```python
# System prompt and ReAct prompt template
```

`static/index.html`:
```html
<!-- MiniGPT frontend -->
```

**Step 3: Verify structure**

```bash
ls -R C:\Users\aryan\Desktop\minigpt
```
Expected: main.py, agent.py, tools.py, prompts.py, static/index.html all present.

**Step 4: Commit**

```bash
cd C:\Users\aryan\Desktop\minigpt
git init
git add main.py agent.py tools.py prompts.py static/index.html
git commit -m "chore: scaffold project structure"
```

---

### Task 2: Prompts

**Files:**
- Modify: `prompts.py`

**Step 1: Write prompts.py**

```python
SYSTEM_PROMPT = """You are MiniGPT, an expert AI assistant specialising in technology fields:
programming, computer science, AI/ML, networking, cybersecurity, databases, and software engineering.

You have access to the following tools:

web_search(query: str) -> str
    Search the web using DuckDuckGo. Use for current information, documentation, or facts.

code_exec(code: str) -> str
    Execute Python code and return stdout. Use for calculations, data processing, or demonstrations.

calculator(expr: str) -> str
    Evaluate a mathematical expression safely. Use for quick arithmetic.

RESPONSE FORMAT — you MUST follow this exactly:

To use a tool:
Thought: <your reasoning about what to do next>
Action: <tool_name>(<argument>)

After receiving an Observation, continue with another Thought/Action or give the final answer:
Thought: <reasoning>
Final Answer: <your complete response to the user>

Rules:
- Always start with a Thought
- Never skip the Thought step
- Use Final Answer only when you have enough information to fully answer
- Keep tool arguments concise
- If a tool returns an error, try a different approach
"""

REACT_TEMPLATE = """{system}

Conversation so far:
{history}

User: {user_message}

{scratchpad}"""
```

**Step 2: Commit**

```bash
git add prompts.py
git commit -m "feat: add system prompt and ReAct template"
```

---

### Task 3: Tools

**Files:**
- Modify: `tools.py`

**Step 1: Write tools.py**

```python
import ast
import io
import sys
import re
import requests
from bs4 import BeautifulSoup


def web_search(query: str) -> str:
    """Search DuckDuckGo and return top results as plain text."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for r in soup.select(".result__body")[:4]:
            title = r.select_one(".result__title")
            snippet = r.select_one(".result__snippet")
            if title and snippet:
                results.append(f"- {title.get_text(strip=True)}: {snippet.get_text(strip=True)}")
        if not results:
            return "No results found."
        return "\n".join(results)
    except Exception as e:
        return f"Search error: {e}"


def code_exec(code: str) -> str:
    """Execute Python code in a restricted sandbox and return stdout."""
    safe_globals = {
        "__builtins__": {
            "print": print, "range": range, "len": len, "int": int,
            "float": float, "str": str, "list": list, "dict": dict,
            "sum": sum, "max": max, "min": min, "abs": abs,
            "round": round, "sorted": sorted, "enumerate": enumerate,
            "zip": zip, "map": map, "filter": filter, "isinstance": isinstance,
        }
    }
    stdout_capture = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_capture
    try:
        exec(code, safe_globals)  # noqa: S102
        output = stdout_capture.getvalue()
        return output.strip() if output.strip() else "(no output)"
    except Exception as e:
        return f"Error: {e}"
    finally:
        sys.stdout = old_stdout


def calculator(expr: str) -> str:
    """Safely evaluate a mathematical expression."""
    # Allow only safe math characters
    if not re.match(r'^[\d\s\+\-\*\/\(\)\.\%\*\*]+$', expr):
        return "Error: only basic math operators allowed (+, -, *, /, **, %, parentheses)"
    try:
        # Use compile + eval with empty globals for safety
        code = compile(expr, "<string>", "eval")
        result = eval(code, {"__builtins__": {}})  # noqa: S307
        return str(result)
    except Exception as e:
        return f"Error: {e}"


TOOLS = {
    "web_search": web_search,
    "code_exec": code_exec,
    "calculator": calculator,
}


def dispatch_tool(action_str: str) -> str:
    """Parse 'tool_name(argument)' and call the matching tool."""
    match = re.match(r'(\w+)\((.+)\)', action_str.strip(), re.DOTALL)
    if not match:
        return f"Could not parse action: {action_str}"
    tool_name, arg = match.group(1), match.group(2).strip().strip('"\'')
    tool = TOOLS.get(tool_name)
    if not tool:
        return f"Unknown tool: {tool_name}. Available: {list(TOOLS.keys())}"
    return tool(arg)
```

**Step 2: Quick manual test (no pytest needed for tools)**

```bash
python -c "
from tools import web_search, calculator, code_exec
print('calculator:', calculator('2 ** 10'))
print('code_exec:', code_exec('print(sum(range(10)))'))
print('web_search:', web_search('python fastapi')[:80])
"
```

Expected:
```
calculator: 1024
code_exec: 45
web_search: - FastAPI: ...
```

**Step 3: Commit**

```bash
git add tools.py
git commit -m "feat: implement web_search, code_exec, calculator tools"
```

---

### Task 4: ReAct Agent Loop

**Files:**
- Modify: `agent.py`

**Step 1: Write agent.py**

```python
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
```

**Step 2: Quick smoke test**

```bash
python -c "
from agent import run_agent
for event in run_agent('What is 2+2?', []):
    print(event)
    if event['type'] == 'done':
        break
"
```

Expected: sequence of thought/action/observation/done dicts printed (Ollama must be running).

**Step 3: Commit**

```bash
git add agent.py
git commit -m "feat: implement ReAct agent loop with Ollama"
```

---

### Task 5: FastAPI Backend + SSE Endpoint

**Files:**
- Modify: `main.py`

**Step 1: Write main.py**

```python
import json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from agent import run_agent

app = FastAPI(title="MiniGPT")
app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")


@app.post("/chat")
async def chat(req: ChatRequest):
    def event_stream():
        for event in run_agent(req.message, req.history):
            data = json.dumps(event)
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}
```

**Step 2: Test the server starts**

```bash
cd C:\Users\aryan\Desktop\minigpt
uvicorn main:app --reload --port 8000
```

Expected: `Uvicorn running on http://127.0.0.1:8000` — no errors.
Stop with Ctrl+C.

**Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add FastAPI server with SSE /chat endpoint"
```

---

### Task 6: Frontend — HTML Structure + CSS

**Files:**
- Modify: `static/index.html`

**Step 1: Write the full index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>MiniGPT</title>
  <link rel="stylesheet"
    href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css" />
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:        #050816;
      --surface:   #0d1224;
      --border:    #1e2a4a;
      --cyan:      #00e5ff;
      --purple:    #7c3aed;
      --pink:      #e040fb;
      --text:      #e2e8f0;
      --muted:     #64748b;
      --success:   #10b981;
      --warning:   #f59e0b;
    }

    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Segoe UI', system-ui, sans-serif;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    /* ── Header ── */
    header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 24px;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      flex-shrink: 0;
    }
    .logo {
      font-size: 1.3rem;
      font-weight: 700;
      background: linear-gradient(90deg, var(--cyan), var(--purple));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: 1px;
    }
    .model-badge {
      font-size: 0.7rem;
      background: rgba(0,229,255,0.1);
      color: var(--cyan);
      border: 1px solid rgba(0,229,255,0.3);
      border-radius: 20px;
      padding: 2px 10px;
    }
    .status-dot {
      width: 8px; height: 8px;
      border-radius: 50%;
      background: var(--success);
      margin-left: auto;
      box-shadow: 0 0 6px var(--success);
    }
    .status-dot.thinking {
      background: var(--warning);
      box-shadow: 0 0 6px var(--warning);
      animation: pulse 1s infinite;
    }
    #status-text {
      font-size: 0.75rem;
      color: var(--muted);
    }

    /* ── Main layout ── */
    .main {
      display: flex;
      flex: 1;
      overflow: hidden;
    }

    /* ── Chat panel ── */
    .chat-panel {
      flex: 1;
      display: flex;
      flex-direction: column;
      border-right: 1px solid var(--border);
    }
    .messages {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .message {
      max-width: 80%;
      padding: 12px 16px;
      border-radius: 12px;
      line-height: 1.6;
      font-size: 0.9rem;
      animation: fadeSlideIn 0.3s ease;
    }
    .message.user {
      align-self: flex-end;
      background: linear-gradient(135deg, rgba(124,58,237,0.3), rgba(0,229,255,0.15));
      border: 1px solid rgba(124,58,237,0.4);
    }
    .message.assistant {
      align-self: flex-start;
      background: var(--surface);
      border: 1px solid var(--border);
    }
    .message.assistant pre {
      margin-top: 8px;
      border-radius: 8px;
      overflow-x: auto;
    }
    .message.assistant code:not(pre code) {
      background: rgba(0,229,255,0.1);
      color: var(--cyan);
      padding: 1px 6px;
      border-radius: 4px;
      font-size: 0.85em;
    }

    .input-area {
      padding: 16px 24px;
      background: var(--surface);
      border-top: 1px solid var(--border);
      display: flex;
      gap: 10px;
      align-items: flex-end;
    }
    textarea {
      flex: 1;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      color: var(--text);
      padding: 12px 16px;
      font-size: 0.9rem;
      font-family: inherit;
      resize: none;
      min-height: 44px;
      max-height: 120px;
      outline: none;
      transition: border-color 0.2s;
    }
    textarea:focus { border-color: var(--cyan); }
    textarea::placeholder { color: var(--muted); }

    button#send-btn {
      background: linear-gradient(135deg, var(--cyan), var(--purple));
      border: none;
      border-radius: 10px;
      color: #fff;
      font-weight: 600;
      padding: 12px 20px;
      cursor: pointer;
      font-size: 0.9rem;
      transition: opacity 0.2s, transform 0.1s;
      white-space: nowrap;
    }
    button#send-btn:hover { opacity: 0.85; }
    button#send-btn:active { transform: scale(0.97); }
    button#send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

    /* ── Brain panel ── */
    .brain-panel {
      width: 380px;
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      position: relative;
    }
    .brain-panel.active::before {
      content: '';
      position: absolute;
      inset: 0;
      border-left: 2px solid transparent;
      background: linear-gradient(var(--bg), var(--bg)) padding-box,
                  linear-gradient(180deg, var(--cyan), var(--purple), var(--pink)) border-box;
      pointer-events: none;
      animation: borderGlow 2s ease infinite alternate;
    }
    .brain-header {
      padding: 14px 20px;
      font-size: 0.7rem;
      letter-spacing: 2px;
      text-transform: uppercase;
      color: var(--muted);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }
    .brain-header .dot {
      width: 6px; height: 6px;
      border-radius: 50%;
      background: var(--purple);
    }
    .brain-steps {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .step {
      border-radius: 10px;
      padding: 10px 14px;
      font-size: 0.8rem;
      line-height: 1.5;
      animation: fadeSlideIn 0.35s ease;
      word-break: break-word;
    }
    .step .step-label {
      font-size: 0.65rem;
      font-weight: 700;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      margin-bottom: 4px;
    }
    .step.thought {
      background: rgba(124,58,237,0.12);
      border: 1px solid rgba(124,58,237,0.3);
    }
    .step.thought .step-label { color: var(--purple); }

    .step.action {
      background: rgba(0,229,255,0.08);
      border: 1px solid rgba(0,229,255,0.3);
    }
    .step.action .step-label { color: var(--cyan); }
    .step.action.running {
      animation: fadeSlideIn 0.35s ease, toolPulse 1s ease infinite alternate;
    }

    .step.observation {
      background: rgba(16,185,129,0.08);
      border: 1px solid rgba(16,185,129,0.25);
    }
    .step.observation .step-label { color: var(--success); }

    .step.error-step {
      background: rgba(239,68,68,0.1);
      border: 1px solid rgba(239,68,68,0.3);
    }
    .step.error-step .step-label { color: #f87171; }

    .empty-brain {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-direction: column;
      gap: 8px;
      color: var(--muted);
      font-size: 0.8rem;
      text-align: center;
      padding: 24px;
    }
    .empty-brain .icon { font-size: 2rem; opacity: 0.3; }

    /* ── Animations ── */
    @keyframes fadeSlideIn {
      from { opacity: 0; transform: translateY(8px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }
    @keyframes toolPulse {
      from { box-shadow: 0 0 0 0 rgba(0,229,255,0.3); }
      to   { box-shadow: 0 0 12px 4px rgba(0,229,255,0.15); }
    }
    @keyframes borderGlow {
      from { opacity: 0.6; }
      to   { opacity: 1; }
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
  </style>
</head>
<body>

<header>
  <span class="logo">&#9670; MiniGPT</span>
  <span class="model-badge">llama3 · local</span>
  <span id="status-text">Ready</span>
  <span class="status-dot" id="status-dot"></span>
</header>

<div class="main">

  <!-- Chat panel -->
  <div class="chat-panel">
    <div class="messages" id="messages">
      <div class="message assistant">
        Hello! I'm MiniGPT — a local AI agent with access to web search, code execution, and a calculator.
        Ask me anything about tech, programming, AI, or science.
      </div>
    </div>
    <div class="input-area">
      <textarea id="input" placeholder="Ask me anything about tech..." rows="1"></textarea>
      <button id="send-btn">Send &#9654;</button>
    </div>
  </div>

  <!-- Brain panel -->
  <div class="brain-panel" id="brain-panel">
    <div class="brain-header">
      <span class="dot"></span>
      Agent Brain
    </div>
    <div class="brain-steps" id="brain-steps">
      <div class="empty-brain">
        <span class="icon">&#129504;</span>
        Agent internals will appear here as it thinks
      </div>
    </div>
  </div>

</div>

<script>
const messagesEl = document.getElementById('messages');
const brainSteps = document.getElementById('brain-steps');
const brainPanel = document.getElementById('brain-panel');
const inputEl    = document.getElementById('input');
const sendBtn    = document.getElementById('send-btn');
const statusDot  = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');

let history = [];
let currentActionStep = null;

function setStatus(thinking) {
  if (thinking) {
    statusDot.classList.add('thinking');
    statusText.textContent = 'Thinking...';
    brainPanel.classList.add('active');
  } else {
    statusDot.classList.remove('thinking');
    statusText.textContent = 'Ready';
    brainPanel.classList.remove('active');
  }
}

function addMessage(role, text) {
  const div = document.createElement('div');
  div.className = `message ${role}`;

  // Render markdown-ish: code blocks and inline code
  let html = escapeHtml(text)
    .replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
      const highlighted = lang && hljs.getLanguage(lang)
        ? hljs.highlight(unescapeHtml(code), { language: lang }).value
        : hljs.highlightAuto(unescapeHtml(code)).value;
      return `<pre><code class="hljs">${highlighted}</code></pre>`;
    })
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>');
  div.innerHTML = html;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function addBrainStep(type, content) {
  // Remove empty-brain placeholder
  const empty = brainSteps.querySelector('.empty-brain');
  if (empty) empty.remove();

  const div = document.createElement('div');
  div.className = `step ${type}`;

  const labels = {
    thought:     '&#x1F4AD; Thought',
    action:      '&#x1F527; Action',
    observation: '&#x1F441; Observation',
    'error-step':'&#x26A0; Error',
  };

  div.innerHTML = `<div class="step-label">${labels[type] || type}</div><div>${escapeHtml(content)}</div>`;
  brainSteps.appendChild(div);
  brainSteps.scrollTop = brainSteps.scrollHeight;
  return div;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
function unescapeHtml(str) {
  return str
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"');
}

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;

  inputEl.value = '';
  sendBtn.disabled = true;
  setStatus(true);

  // Clear brain panel for new query
  brainSteps.innerHTML = '';

  // Add user message
  addMessage('user', text);

  // Add empty assistant bubble for streaming
  const aMsg = addMessage('assistant', '');
  let fullAnswer = '';

  try {
    const resp = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history }),
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop(); // keep incomplete chunk

      for (const line of lines) {
        if (!line.startsWith('data:')) continue;
        const json = line.slice(5).trim();
        if (!json) continue;

        let event;
        try { event = JSON.parse(json); } catch { continue; }

        if (event.type === 'thought') {
          addBrainStep('thought', event.content);
        } else if (event.type === 'action') {
          currentActionStep = addBrainStep('action', event.content);
          currentActionStep.classList.add('running');
        } else if (event.type === 'observation') {
          if (currentActionStep) {
            currentActionStep.classList.remove('running');
            currentActionStep = null;
          }
          addBrainStep('observation', event.content.slice(0, 300) + (event.content.length > 300 ? '...' : ''));
        } else if (event.type === 'answer_token') {
          fullAnswer += event.content;
          // Re-render with simple text (fast path during streaming)
          aMsg.textContent = fullAnswer;
          messagesEl.scrollTop = messagesEl.scrollHeight;
        } else if (event.type === 'done') {
          // Final render with code highlighting
          aMsg.innerHTML = '';
          const finalEl = addMessage('assistant', event.content);
          aMsg.replaceWith(finalEl);
          history.push({ user: text, assistant: event.content });
        } else if (event.type === 'error') {
          addBrainStep('error-step', event.content);
          aMsg.textContent = 'Sorry, something went wrong. Check that Ollama is running.';
        }
      }
    }
  } catch (e) {
    aMsg.textContent = `Connection error: ${e.message}`;
  }

  setStatus(false);
  sendBtn.disabled = false;
  inputEl.focus();
}

sendBtn.addEventListener('click', sendMessage);
inputEl.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Auto-resize textarea
inputEl.addEventListener('input', () => {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
});
</script>
</body>
</html>
```

**Step 2: Verify the file saved**

Open `http://127.0.0.1:8000` after starting the server — you should see the two-panel UI.

**Step 3: Commit**

```bash
git add static/index.html
git commit -m "feat: add futuristic two-panel AI chat frontend"
```

---

### Task 7: End-to-End Test

**Step 1: Start Ollama (in a separate terminal)**

```bash
ollama serve
```

**Step 2: Start the FastAPI server**

```bash
cd C:\Users\aryan\Desktop\minigpt
uvicorn main:app --reload --port 8000
```

**Step 3: Open the app**

Open `http://127.0.0.1:8000` in your browser.

**Step 4: Test each tool manually**

Send these messages one by one and verify the brain panel shows the ReAct steps:

1. `What is 1234 * 5678?` — should use `calculator`
2. `Write and run Python code to print the first 10 Fibonacci numbers` — should use `code_exec`
3. `What is the latest version of Python?` — should use `web_search`

**Step 5: Final commit**

```bash
git add .
git commit -m "chore: complete MiniGPT v1 — all tools and UI working"
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ollama: command not found` | Download from https://ollama.com/download |
| `model not found` | Run `ollama pull llama3` |
| Agent loops without answer | Model may need a clearer prompt — try `mistral` instead |
| CORS error in browser | Make sure you open `http://127.0.0.1:8000` (via FastAPI), not the file directly |
| `httpx.ConnectError` | Ollama is not running — start it with `ollama serve` |
