import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from pathlib import Path

console = Console()

ASCII_ART_PATH = Path(__file__).parent.parent / "components" / "ascii_art.txt"
DEFAULT_BANNER = '''
[bold cyan] _   _                 ____ _ _   [/bold cyan]
[bold cyan]| \ | | ___  ___  ___  / ___(_) |_ [/bold cyan]
[bold cyan]|  \| |/ _ \/ _ \/ _ \| |  _| | __|[/bold cyan]
[bold cyan]| |\  |  __/  __/  __/ |_| | | |_ [/bold cyan]
[bold cyan]|_| \_|\___|\___|\___|\____|_|\__|[/bold cyan]
[bold magenta]           N E O G I T[/bold magenta]
'''

def ascii_banner():
    try:
        if ASCII_ART_PATH.exists():
            art = ASCII_ART_PATH.read_text(encoding="utf-8")
            panel = Panel.fit(Text.from_markup(art), style="bold cyan", border_style="magenta")
            console.print(panel)
            return
    except Exception:
        pass
    panel = Panel.fit(Text.from_markup(DEFAULT_BANNER), style="bold cyan", border_style="magenta")
    console.print(panel)

def select_menu(message, choices):
    """Show an arrow-key menu and return the selected value."""
    return questionary.select(message, choices=choices, qmark="👉").ask()

def confirm_menu(message, default=True):
    """Show a yes/no confirmation with emoji."""
    return questionary.confirm(f"{message} 😊", default=default).ask()

def text_input(message, default=None, password=False):
    """Show a text input prompt, optionally with a default and password masking."""
    if password:
        return questionary.password(message, qmark="🔑").ask()
    else:
        if default is not None:
            return questionary.text(message, default=default, qmark="✏️").ask()
        else:
            return questionary.text(message, qmark="✏️").ask() 