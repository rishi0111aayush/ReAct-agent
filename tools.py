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
