"""
tools/misc.py — Miscellaneous tools: datetime_now, plot.
"""
import json


def datetime_now(tz: str = "UTC") -> str:
    """Return the current date, time, weekday, and timezone."""
    from datetime import datetime, timezone
    import zoneinfo
    try:
        zi  = zoneinfo.ZoneInfo(tz) if tz and tz != "UTC" else timezone.utc
        now = datetime.now(zi)
        return now.strftime(f"%A, %d %B %Y — %H:%M:%S {tz}")
    except Exception:
        now = datetime.now(timezone.utc)
        return now.strftime("%A, %d %B %Y — %H:%M:%S UTC")


def plot(json_spec: str) -> str:
    """
    Render an interactive chart in the UI.
    json_spec must be a JSON object with keys:
      type     — "bar" | "line" | "pie" | "doughnut" | "radar"
      title    — chart title string
      labels   — list of category strings
      datasets — list of {label, data} objects
    """
    try:
        spec    = json.loads(json_spec)
        missing = {"type", "labels", "datasets"} - spec.keys()
        if missing:
            return f"Plot error: missing keys {missing}"
        if spec["type"] not in {"bar", "line", "pie", "doughnut", "radar"}:
            return f"Plot error: unsupported type '{spec['type']}'. Use bar/line/pie/doughnut/radar."
        return f"CHART:{json.dumps(spec)}"
    except Exception as e:
        return f"Plot error: {e}"
