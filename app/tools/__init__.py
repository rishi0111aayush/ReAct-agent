"""
tools/__init__.py — Tool registry and dispatcher for the ReAct agent.
"""
import re

from app.tools.web    import web_search, wikipedia_search, get_weather
from app.tools.code   import code_exec, calculator
from app.tools.rag    import rag_ingest, rag_search
from app.tools.memory import remember, recall, set_user_context
from app.tools.misc   import datetime_now, plot

TOOLS: dict = {
    "web_search":       web_search,
    "code_exec":        code_exec,
    "calculator":       calculator,
    "rag_ingest":       rag_ingest,
    "rag_search":       rag_search,
    "plot":             plot,
    "remember":         remember,
    "recall":           recall,
    "datetime_now":     datetime_now,
    "wikipedia_search": wikipedia_search,
    "get_weather":      get_weather,
}


def dispatch_tool(action_str: str) -> str:
    """Parse 'tool_name(argument)' and call the matching tool."""
    match = re.match(r"(\w+)\((.+)\)", action_str.strip(), re.DOTALL)
    if not match:
        return f"Could not parse action: {action_str}"
    tool_name, arg = match.group(1), match.group(2).strip().strip("\"'")
    tool = TOOLS.get(tool_name)
    if not tool:
        return f"Unknown tool: {tool_name}. Available: {list(TOOLS.keys())}"
    return tool(arg)
