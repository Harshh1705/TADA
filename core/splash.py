import platform
from pathlib import Path

from rich.console import Console
from rich.text import Text
from rich.style import Style

VERSION = "0.1.0"

try:
    import pyfiglet
    _LOGO = pyfiglet.figlet_format("tada", font="slant")
except Exception:
    _LOGO = (
        "    _______       __      \n"
        "   /__  __/____ _/ /______\n"
        "    / / / ___/ / __/ ___/\n"
        "   / / / /  / / /_(__  ) \n"
        "  /_/ /_/  /_/\\__/____/  \n"
        "                         \n"
    )


def _blue_cyan_gradient(ratio: float) -> str:
    r = int(30 + 0 * ratio)
    g = int(120 + 135 * ratio)
    b = int(255 + 0 * ratio)
    return f"{r:02x}{g:02x}{b:02x}"


def _detect_color_system(console: Console) -> str:
    try:
        cs = console._color_system
        if cs == "truecolor":
            return "truecolor"
        if cs in ("256", "standard", "eight"):
            return "ansi"
    except Exception:
        pass
    return "none"


def _separator(console: Console, style="dim"):
    width = min(console.width, 72)
    line = Text("  " + "-" * (width - 4), style=style)
    return line


def show_splash():
    console = Console()
    color_system = _detect_color_system(console)

    lines = _LOGO.rstrip("\n").split("\n")
    n = len(lines)
    logo = Text()

    if color_system == "truecolor":
        for i, line in enumerate(lines):
            ratio = i / max(n - 1, 1)
            hex_color = _blue_cyan_gradient(ratio)
            styled_line = Text(line, style=Style(color=f"#{hex_color}"))
            if i < n - 1:
                styled_line.append("\n")
            logo.append(styled_line)
    elif color_system == "ansi":
        for i, line in enumerate(lines):
            c = "cyan" if i >= n // 2 else "blue"
            styled_line = Text(line, style=Style(color=c))
            if i < n - 1:
                styled_line.append("\n")
            logo.append(styled_line)
    else:
        for i, line in enumerate(lines):
            logo.append(line)
            if i < n - 1:
                logo.append("\n")

    th = Text("\n")
    console.print(th)
    console.print(logo, justify="center")

    py_ver = platform.python_version()
    cwd = Path.cwd().resolve()
    display_cwd = str(cwd)
    if len(display_cwd) > 40:
        parts = cwd.parts
        if len(parts) > 2:
            display_cwd = "..." + str(Path(*parts[-2:]))
    status_line = Text()
    status_line.append(f"  v{VERSION}", style="dim")
    status_line.append("  |  ", style="bold")
    status_line.append(f"Python {py_ver}", style="dim")
    status_line.append("  |  ", style="bold")
    status_line.append(display_cwd, style="dim")
    console.print(status_line, justify="center")

    console.print(_separator(console), justify="center")

    welcome = Text()
    welcome.append("\n  Welcome to ", style="bold white")
    welcome.append("tada", style="bold cyan")
    welcome.append(".\n", style="bold white")
    desc = Text(
        "  Technical AI-Diligence Agent - analyze pitch decks, verify data moats,\n"
        "  check cross-border compliance, match talent, and map your portfolio.\n",
        style="white",
    )
    console.print(welcome)
    console.print(desc)

    console.print(_separator(console), justify="center")

    quickstart_header = Text("  Quick Start", style="bold yellow")
    console.print(quickstart_header)
    console.print()

    cmds = [
        ("tada run <deck.pdf>", "Standard diligence (claim extraction + verdict)"),
        ("tada audit <deck.pdf>", "Full audit: data moat, infra, talent, cross-ref"),
        ("tada batch <decks_dir/>", "Batch portfolio mapping across multiple decks"),
        ("tada diff <v1.pdf> <v2.pdf>", "Compare claims across deck versions"),
        ("tada config set --help", "Configure API credentials"),
        ("tada config show", "Show current config"),
    ]
    for cmd, desc_text in cmds:
        line = Text()
        line.append(f"    {cmd:45}", style="bold cyan")
        line.append(f"  {desc_text}", style="white")
        console.print(line)

    console.print()
    console.print(_separator(console), justify="center")

    bottom = Text()
    bottom.append("  Session: Ready", style="bold green")
    bottom.append("  |  ", style="bold")
    bottom.append(f"Directory: {display_cwd}", style="dim")
    console.print(bottom, justify="center")

    console.print()
