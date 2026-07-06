"""
tools/code.py — Code execution tools: code_exec, calculator.
"""
import ast
import io
import re
import subprocess
import sys


def code_exec(code: str) -> str:
    """Execute Python code in a restricted sandbox and return stdout."""
    try:
        tree = ast.parse(code, mode="exec")
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
    old_stdout     = sys.stdout
    sys.stdout     = stdout_capture
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
    if not re.match(r"^[\d\s\+\-\*\/\(\)\.\%\*\*]+$", expr):
        return "Error: only basic math operators allowed (+, -, *, /, **, %, parentheses)"
    try:
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c",
             f"print(eval(compile({repr(expr)}, '<string>', 'eval'), {{'__builtins__': {{}}}}))"],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode != 0:
            return f"Error: {result.stderr.strip()}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Error: expression took too long to evaluate"
    except Exception as e:
        return f"Error: {e}"
