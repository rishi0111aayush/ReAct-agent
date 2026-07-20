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
        # Validate AST to allow only numeric literals and safe operators
        node = ast.parse(expr, mode='eval')
        for n in ast.walk(node):
            if isinstance(n, (ast.Call, ast.Attribute, ast.Subscript, ast.Name, ast.Lambda, ast.FunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)):
                return "Error: disallowed expression"
            if isinstance(n, ast.BinOp) and not isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow)):
                return "Error: disallowed operator"
            if isinstance(n, ast.UnaryOp) and not isinstance(n.op, (ast.UAdd, ast.USub)):
                return "Error: disallowed operator"
        result_value = eval(compile(node, '<string>', 'eval'), {'__builtins__': {}}, {})
        return str(result_value)
    except subprocess.TimeoutExpired:
        return "Error: expression took too long to evaluate"
    except Exception as e:
        return f"Error: {e}"
