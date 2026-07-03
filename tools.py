"""
tools.py — Tool implementations for the Boozo.ai ReAct agent.

Tools:
  web_search  — DuckDuckGo HTML scraping (no API key)
  code_exec   — AST-validated Python sandbox
  calculator  — Subprocess-isolated math evaluator
  rag_ingest  — Ingest URLs or text into ChromaDB knowledge base
  rag_search  — Semantic search over ingested documents
"""
import ast
import io
import re
import subprocess
import sys

import chromadb
import requests
from bs4 import BeautifulSoup
from chromadb.utils import embedding_functions


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
    # AST validation: reject any attribute access (blocks __class__.__bases__ escape)
    try:
        tree = ast.parse(code, mode='exec')
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                return "Error: attribute access is not allowed in the sandbox"
    except SyntaxError as e:
        return f"Syntax error: {e}"

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
        exec(compile(tree, "<sandbox>", "exec"), safe_globals)  # noqa: S102
        output = stdout_capture.getvalue()
        return output.strip() if output.strip() else "(no output)"
    except Exception as e:
        return f"Error: {e}"
    finally:
        sys.stdout = old_stdout


def calculator(expr: str) -> str:
    """Safely evaluate a mathematical expression."""
    if not re.match(r'^[\d\s\+\-\*\/\(\)\.\%\*\*]+$', expr):
        return "Error: only basic math operators allowed (+, -, *, /, **, %, parentheses)"
    try:
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", f"print(eval(compile({repr(expr)}, '<string>', 'eval'), {{'__builtins__': {{}}}}) )"],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode != 0:
            return f"Error: {result.stderr.strip()}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Error: expression took too long to evaluate"
    except Exception as e:
        return f"Error: {e}"


# ── RAG: in-memory vector store ──────────────────────────────────────────────
_chroma_client = chromadb.Client()
_embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
_rag_collection = _chroma_client.get_or_create_collection(
    name="boozo_rag", embedding_function=_embed_fn
)
_rag_doc_counter = [0]  # mutable counter for unique IDs


def rag_ingest(source: str) -> str:
    """
    Ingest text or a URL into the RAG knowledge base.
    Pass plain text directly, or a URL starting with http/https.
    """
    try:
        if source.startswith("http://") or source.startswith("https://"):
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(source, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            label = source
        else:
            text = source
            label = f"text-{_rag_doc_counter[0]}"

        # Split into ~300-char chunks with 50-char overlap
        chunk_size, overlap = 300, 50
        chunks, start = [], 0
        while start < len(text):
            chunks.append(text[start: start + chunk_size])
            start += chunk_size - overlap

        for i, chunk in enumerate(chunks):
            _rag_collection.upsert(
                documents=[chunk],
                ids=[f"doc-{_rag_doc_counter[0]}-chunk-{i}"],
                metadatas=[{"source": label}],
            )
        _rag_doc_counter[0] += 1
        return f"Ingested {len(chunks)} chunks from '{label}' into knowledge base."
    except Exception as e:
        return f"Ingest error: {e}"


def rag_search(query: str) -> str:
    """Search the RAG knowledge base for chunks relevant to the query."""
    try:
        count = _rag_collection.count()
        if count == 0:
            return "Knowledge base is empty. Use rag_ingest(text_or_url) first."
        results = _rag_collection.query(
            query_texts=[query],
            n_results=min(3, count),
        )
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        if not docs:
            return "No relevant results found."
        parts = []
        for doc, meta in zip(docs, metas):
            src = meta.get("source", "unknown")
            parts.append(f"[source: {src}]\n{doc}")
        return "\n\n---\n\n".join(parts)
    except Exception as e:
        return f"Search error: {e}"


def plot(json_spec: str) -> str:
    """
    Render an interactive chart in the UI.
    json_spec must be a JSON object with keys:
      type    — "bar" | "line" | "pie" | "doughnut" | "radar"
      title   — chart title string
      labels  — list of category strings
      datasets — list of {label, data} objects
    Example: {"type":"bar","title":"Sales","labels":["Q1","Q2"],"datasets":[{"label":"Revenue","data":[100,200]}]}
    """
    import json as _json
    try:
        spec = _json.loads(json_spec)
        required = {"type", "labels", "datasets"}
        missing = required - spec.keys()
        if missing:
            return f"Plot error: missing keys {missing}"
        if spec["type"] not in {"bar", "line", "pie", "doughnut", "radar"}:
            return f"Plot error: unsupported type '{spec['type']}'. Use bar/line/pie/doughnut/radar."
        return f"CHART:{_json.dumps(spec)}"
    except Exception as e:
        return f"Plot error: {e}"


TOOLS = {
    "web_search": web_search,
    "code_exec": code_exec,
    "calculator": calculator,
    "rag_ingest": rag_ingest,
    "rag_search": rag_search,
    "plot": plot,
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
