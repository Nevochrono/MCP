import rich_click as click
click.rich_click.MAX_WIDTH = 100
click.rich_click.USE_RICH_MARKUP = True
import requests
from neogit.ai.project_analyzer import ProjectAnalyzer
from rich.prompt import Prompt
from rich.progress import Progress
from neogit.config.manager import ConfigManager
from neogit.github.manager import GitHubManager, deploy_to_github
from neogit.ai.readme_generator import READMEGenerator
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from pathlib import Path
from neogit.utils.prompt_utils import ascii_banner, select_menu, confirm_menu, text_input

console = Console()

CONTEXT_SETTINGS = dict(
    help_option_names=["-h", "--help"],
    max_content_width=100
)

HELP_HEADER = """
[bold blue]NeoGit CLI[/bold blue] - [green]Automate README creation and GitHub deployment with style![/green]
[dim]Usage: neogit [OPTIONS] COMMAND [ARGS]...[/dim]
"""

HELP_EPILOG = """
[bold]Tips:[/bold]

- Use [cyan]neogit setup[/cyan] to configure your GitHub and AI provider credentials.

- Use [cyan]neogit generate-readme[/cyan] to create a professional README.md for your project.

- Use [cyan]neogit create-gitignore[/cyan] to generate a .gitignore file tailored to your project and protect sensitive files.

- Use [cyan]neogit deploy[/cyan] to push your project and README to GitHub.

- Use [cyan]neogit run[/cyan] to do it all in one go!

- Use [cyan]neogit COMMAND --help[/cyan] for details on any command.
"""

@click.group(context_settings=CONTEXT_SETTINGS, help=HELP_HEADER, epilog=HELP_EPILOG)
def cli():
    """NeoGit CLI: Automate README creation and GitHub deployment with style!"""
    pass

@cli.command(help="Interactive setup for NeoGit configuration (GitHub, AI providers, etc.)")
def setup():
    ConfigManager().setup()

@cli.command(name="generate-readme", help="Analyze your project and generate a professional README.md using an AI provider.")
def generate_readme():
    ascii_banner()
    project_path = text_input("\U0001F4C1 Project path (enter '.' for current directory)")
    project_path = Path(project_path.strip()).expanduser().resolve()
    readme_type = select_menu("\U0001F4C4 README type", ["simple", "advanced", "installation"])
    config = ConfigManager()
    settings = config.load_config()
    ai_providers = settings.ai_providers
    available_providers = []
    provider_labels = []
    for prov in ["openai", "anthropic", "google", "huggingface", "ollama"]:
        val = getattr(ai_providers, prov, None)
        if prov == "huggingface" and val:
            available_providers.append(prov)
            provider_labels.append(f"Hugging Face (model: {val.default_model})")
        elif val:
            available_providers.append(prov)
            provider_labels.append(f"{prov.capitalize()} (key set)")
    if not available_providers:
        console.print("[red]No AI providers configured. Please run setup or reconfigure.[/red]")
        return
    if len(available_providers) == 1:
        selected_provider = available_providers[0]
    else:
        selected_label = select_menu("\U0001F916 Select AI provider", provider_labels)
        selected_provider = available_providers[provider_labels.index(selected_label)]

    if not project_path.exists():
        console.print(f"[red]Project path {project_path} does not exist.[/red]")
        return

    analyzer = ProjectAnalyzer(project_path)
    project_info = analyzer.analyze()

    generator = READMEGenerator(
        ai_providers={prov: getattr(ai_providers, prov, None) for prov in available_providers},
        selected_provider=selected_provider
    )
    readme_content = generator.generate_readme(project_info, readme_type)
    readme_path = project_path / 'README.md'
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    console.print(f"[green]README.md generated at {readme_path}! \U0001F389[/green]")

@cli.command(help="Deploy your project and generated README.md to GitHub.")
def deploy():
    ascii_banner()
    deploy_to_github()

@cli.command(help="Analyze, generate README, ensure .gitignore is present and up-to-date, and deploy your project to GitHub in one go.")
def run():
    ascii_banner()
    project_path = text_input("\U0001F4C1 Project path (enter '.' for current directory)")
    project_path = Path(project_path.strip()).expanduser().resolve()
    readme_type = select_menu("\U0001F4C4 README type", ["simple", "advanced", "installation"])
    config = ConfigManager()
    settings = config.load_config()
    ai_providers = settings.ai_providers
    available_providers = []
    provider_labels = []
    for prov in ["openai", "anthropic", "google", "huggingface", "ollama"]:
        val = getattr(ai_providers, prov, None)
        if prov == "huggingface" and val:
            available_providers.append(prov)
            provider_labels.append(f"Hugging Face (model: {val.default_model})")
        elif val:
            available_providers.append(prov)
            provider_labels.append(f"{prov.capitalize()} (key set)")
    if not available_providers:
        console.print("[red]No AI providers configured. Please run setup or reconfigure.[/red]")
        return
    if len(available_providers) == 1:
        selected_provider = available_providers[0]
    else:
        selected_label = select_menu("\U0001F916 Select AI provider", provider_labels)
        selected_provider = available_providers[provider_labels.index(selected_label)]

    github_token = settings.github.token
    github_username = settings.github.username

    if not github_token or not github_username:
        console.print("[red]GitHub credentials not found. Please run setup first.[/red]")
        return

    if not project_path.exists():
        console.print(f"[red]Project path {project_path} does not exist.[/red]")
        return

    # Ensure .gitignore is present and up-to-date
    gitignore_path = project_path / '.gitignore'
    required_patterns = ['mcp_client.config', '.env', '*.secret', '.venv', 'node_modules']
    needs_update = False
    if not gitignore_path.exists():
        needs_update = True
    else:
        with open(gitignore_path, 'r') as f:
            content = f.read()
        for pattern in required_patterns:
            if pattern not in content:
                needs_update = True
                break
    if needs_update:
        console.print("[yellow]Ensuring .gitignore is present and up-to-date...[/yellow]")
        # Use the same logic as create-gitignore
        try:
            analyzer = ProjectAnalyzer(project_path)
            project_info = analyzer.analyze()
            detected = project_info.language.lower() if project_info.language else "python"
        except Exception:
            detected = "python"
        techs = detected
        url = f"https://www.toptal.com/developers/gitignore/api/{techs}"
        with Progress() as progress:
            task = progress.add_task("Fetching from gitignore.io...", total=1)
            try:
                resp = requests.get(url)
                progress.update(task, advance=1)
                if resp.status_code == 200:
                    content = resp.text.rstrip()
                    if 'mcp_client.config' not in content:
                        content += '\n# NeoGit config file\nmcp_client.config'
                    for pattern in required_patterns[1:]:
                        if pattern not in content:
                            content += f"\n{pattern}"
                    content += '\n'
                    with open(gitignore_path, 'w') as f:
                        f.write(content)
                    console.print(f"[green].gitignore created/updated at {gitignore_path}![/green]")
                else:
                    console.print(f"[red]Failed to fetch .gitignore (status {resp.status_code})[/red]")
            except Exception as e:
                console.print(f"[red]Error fetching .gitignore: {e}[/red]")

    branch = select_menu("\U0001F33F Branch to upload to", ["main", "side"])
    private = confirm_menu("\U0001F512 Should the repository be private?", default=False)

    analyzer = ProjectAnalyzer(project_path)
    project_info = analyzer.analyze()

    generator = READMEGenerator(
        ai_providers={prov: getattr(ai_providers, prov, None) for prov in available_providers},
        selected_provider=selected_provider
    )
    readme_content = generator.generate_readme(project_info, readme_type)
    readme_path = project_path / 'README.md'
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    console.print(f"[green]README.md generated at {readme_path}! \U0001F389[/green]")

    github = GitHubManager(token=github_token, username=github_username)
    github.deploy_project(project_path, readme_path, project_info, branch=branch, private=private)
    console.print("[green]Project deployed to GitHub! \U0001F680[/green]")

@cli.command(help="Re-run the interactive setup to reconfigure NeoGit.")
def reconfigure():
    ascii_banner()
    ConfigManager().setup()

@cli.command(help="Create a .gitignore file for your project based on its main language and tools. Always protects common secrets and config files.")
def create_gitignore():
    ascii_banner()
    project_path = text_input("\U0001F4C1 Project path (enter '.' for current directory)")
    project_path = Path(project_path.strip()).expanduser().resolve()
    if not project_path.exists():
        console.print(f"[red]Project path {project_path} does not exist.[/red]")
        return
    # Try to detect language
    try:
        analyzer = ProjectAnalyzer(project_path)
        project_info = analyzer.analyze()
        detected = project_info.language.lower() if project_info.language else "python"
    except Exception:
        detected = "python"
    console.print(f"[cyan]Detected main language:[/cyan] [bold]{detected}[/bold]")
    techs = Prompt.ask("Enter comma-separated technologies/tools for .gitignore (or press Enter to use detected)", default=detected)
    techs = techs.replace(' ', '').lower()
    url = f"https://www.toptal.com/developers/gitignore/api/{techs}"
    console.print(f"[yellow]Fetching .gitignore for: {techs} ...[/yellow]")
    with Progress() as progress:
        task = progress.add_task("Fetching from gitignore.io...", total=1)
        try:
            resp = requests.get(url)
            progress.update(task, advance=1)
            if resp.status_code == 200:
                gitignore_path = project_path / '.gitignore'
                content = resp.text.rstrip()
                # Always append mcp_client.config if not present
                if 'mcp_client.config' not in content:
                    content += '\n# NeoGit config file\nmcp_client.config'
                # Always append .env, *.secret, .venv, node_modules if not present
                always_patterns = ['.env', '*.secret', '.venv', 'node_modules']
                for pattern in always_patterns:
                    if pattern not in content:
                        content += f"\n{pattern}"
                content += '\n'
                with open(gitignore_path, 'w') as f:
                    f.write(content)
                console.print(f"[green].gitignore created at {gitignore_path}![/green]")
            else:
                console.print(f"[red]Failed to fetch .gitignore (status {resp.status_code})[/red]")
        except Exception as e:
            console.print(f"[red]Error fetching .gitignore: {e}[/red]")

def main():
    cli()

if __name__ == '__main__':
    main() 