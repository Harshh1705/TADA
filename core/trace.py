from datetime import datetime

from rich.console import Console
from rich.theme import Theme

_theme = Theme(
    {
        "info": "bold cyan",
        "success": "bold green",
        "warn": "yellow",
        "debug": "dim white",
        "label": "bold white",
    }
)
_console = Console(theme=_theme)


class Tracer:
    def __init__(self, verbose: bool = False):
        self._steps: list[dict] = []
        self._verbose = verbose

    def step(self, label: str, **details):
        ts = datetime.now().strftime("%H:%M:%S")
        detail_str = " ".join(f"{k}={v}" for k, v in details.items())
        line = f"{label}" + (f" ({detail_str})" if detail_str else "")
        _console.print(f"  [{ts}] {line}", style="info")
        self._steps.append({"label": label, "timestamp": ts, "level": "info", **details})

    def ok(self, label: str, **details):
        ts = datetime.now().strftime("%H:%M:%S")
        detail_str = " ".join(f"{k}={v}" for k, v in details.items())
        line = f"{label}" + (f" ({detail_str})" if detail_str else "")
        _console.print(f"  [{ts}] {line}", style="success")
        self._steps.append({"label": label, "timestamp": ts, "level": "success", **details})

    def debug(self, label: str, **details):
        if not self._verbose:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        detail_str = " ".join(f"{k}={v}" for k, v in details.items())
        line = f"{label}" + (f" ({detail_str})" if detail_str else "")
        _console.print(f"  [{ts}] {line}", style="debug")
        self._steps.append({"label": label, "timestamp": ts, "level": "debug", **details})

    def get_steps(self) -> list[dict]:
        return list(self._steps)
