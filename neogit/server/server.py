"""Configuration management for GitHub README MCP Server."""

import os
import yaml
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import requests
from neogit.utils.prompt_utils import ascii_banner, select_menu, confirm_menu, text_input

console = Console()


@dataclass
class GitHubConfig:
    """GitHub configuration settings."""
    username: str
    token: str


@dataclass
class HuggingFaceConfig:
    api_key: str
    models: list  # keep as list for compatibility, but only one model will be stored
    default_model: str


@dataclass
class AIProvidersConfig:
    openai: Optional[Dict[str, str]] = None
    anthropic: Optional[Dict[str, str]] = None
    google: Optional[Dict[str, str]] = None
    huggingface: Optional[HuggingFaceConfig] = None
    ollama: Optional[Dict[str, str]] = None


@dataclass
class AppConfig:
    """Application configuration."""
    github: GitHubConfig
    alias: Optional[str] = None
    ai_providers: Optional[AIProvidersConfig] = None


class ConfigManager:
    """Manages application configuration and setup."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".github-readme-mcp"
        self.config_file = self.config_dir / "config.yaml"
        self.config: Optional[AppConfig] = None
        
    def setup(self) -> AppConfig:
        """Menu-driven interactive setup for configuration."""
        ascii_banner()
        # Load existing config if present
        try:
            current = self.load_config()
        except Exception:
            current = AppConfig(github=GitHubConfig(username="", token=""), alias=None, ai_providers=AIProvidersConfig())
        config = current
        while True:
            # Show current config summary
            self._print_config_summary(config)
            console.print(Panel.fit("[bold blue]MCP Configuration Menu[/bold blue]", border_style="blue"))
            choice = select_menu(
                "What would you like to do?",
                [
                    "Edit GitHub Credentials",
                    "Edit Alias",
                    "Edit AI Providers",
                    "Save & Exit",
                    "Cancel/Exit without saving"
                ]
            )
            if choice == "Edit GitHub Credentials":
                config.github = self._edit_github(config.github)
            elif choice == "Edit Alias":
                config.alias = self._edit_alias(config.alias)
            elif choice == "Edit AI Providers":
                config.ai_providers = self._edit_ai_providers(config.ai_providers)
            elif choice == "Save & Exit":
                self.save_config(config)
                self.config = config
                console.print(Panel.fit("[bold green]✅ Configuration saved![/bold green]", border_style="green"))
                return config
            elif choice == "Cancel/Exit without saving":
                console.print(Panel.fit("[bold yellow]Exited without saving changes.[/bold yellow]", border_style="yellow"))
                return current

    def _print_config_summary(self, config: AppConfig):
        from rich.table import Table
        table = Table(title="Current [bold magenta]NeoGit[/bold magenta] Configuration", show_header=True, header_style="bold magenta")
        table.add_column("Section")
        table.add_column("Value")
        table.add_row("GitHub Username", f"[cyan]{config.github.username}[/cyan]" if config.github.username else "[dim]Not set[/dim]")
        table.add_row("Alias", f"[magenta]{config.alias}[/magenta]" if config.alias else "[dim]Not set[/dim]")
        provs = []
        aip = config.ai_providers
        for prov in ["openai", "anthropic", "google", "huggingface", "ollama"]:
            val = getattr(aip, prov, None) if aip else None
            if prov == "huggingface" and val:
                provs.append(f"[green]{prov}[/green] (model: [yellow]{val.default_model}[/yellow], key: {'set' if val.api_key else 'not set'})")
            elif val:
                provs.append(f"[green]{prov}[/green] (key: {'set' if val.get('api_key') else 'not set'})")
        table.add_row("AI Providers", ", ".join(provs) if provs else "[dim]None configured[/dim]")
        console.print(table)

    def _edit_github(self, github: GitHubConfig) -> GitHubConfig:
        username = text_input("GitHub username", default=github.username or "")
        token = text_input("GitHub access token", password=True, default=github.token or "")
        skip_validation = confirm_menu("Skip GitHub credential validation?", default=False)
        if not skip_validation:
            if not self._validate_github_credentials(username, token):
                console.print("[red]Invalid GitHub credentials. Please check your username and token.[/red]")
                return self._edit_github(github)
        return GitHubConfig(username=username, token=token)

    def _edit_alias(self, alias: Optional[str]) -> Optional[str]:
        create_alias = confirm_menu("Would you like to set or change the alias?", default=bool(alias))
        if create_alias:
            alias_val = text_input("Enter your preferred alias name", default=alias or "grmcp")
            self._create_alias(alias_val)
            return alias_val
        return None

    def _edit_ai_providers(self, ai_providers: Optional[AIProvidersConfig]) -> AIProvidersConfig:
        if not ai_providers:
            ai_providers = AIProvidersConfig()
        while True:
            # Show current providers
            console.print(Panel.fit("[bold magenta]AI Providers Menu[/bold magenta]", border_style="magenta"))
            provider_labels = []
            provider_keys = ["openai", "anthropic", "google", "huggingface", "ollama"]
            for prov in provider_keys:
                val = getattr(ai_providers, prov, None)
                if prov == "huggingface" and val:
                    provider_labels.append(f"{prov} (models: {', '.join(val.models)}, default: {val.default_model})")
                elif val:
                    provider_labels.append(f"{prov} (configured)")
                else:
                    provider_labels.append(f"{prov} [not configured]")
            menu_choices = provider_labels + ["Add Provider", "Remove Provider", "Back to Main Menu"]
            choice = select_menu("Select an option", choices=menu_choices)
            if choice.startswith("openai"):
                ai_providers = self._edit_provider(ai_providers, "openai")
            elif choice.startswith("anthropic"):
                ai_providers = self._edit_provider(ai_providers, "anthropic")
            elif choice.startswith("google"):
                ai_providers = self._edit_provider(ai_providers, "google")
            elif choice.startswith("huggingface"):
                ai_providers = self._edit_provider(ai_providers, "huggingface")
            elif choice.startswith("ollama"):
                ai_providers = self._edit_provider(ai_providers, "ollama")
            elif choice == "Add Provider":
                prov = select_menu("Which provider to add?", choices=provider_keys)
                ai_providers = self._edit_provider(ai_providers, prov)
            elif choice == "Remove Provider":
                prov = select_menu("Which provider to remove?", choices=provider_keys)
                setattr(ai_providers, prov, None)
            elif choice == "Back to Main Menu":
                break
        return ai_providers

    def _edit_provider(self, ai_providers: AIProvidersConfig, prov: str) -> AIProvidersConfig:
        def confirm_credential(label, value):
            show = confirm_menu(f"Show {label} in plain text?", default=False)
            if show:
                console.print(f"[yellow]{label}: {value}[/yellow]")
            else:
                console.print(f"[yellow]{label}: {'*' * len(value)}[/yellow]")
            return confirm_menu(f"Is this {label} correct?", default=True)

        if prov == "openai":
            key = text_input("OpenAI API key", password=True)
            if not confirm_credential("OpenAI API key", key):
                return self._edit_provider(ai_providers, prov)
            if confirm_menu("Test OpenAI connection?", default=True):
                try:
                    import openai
                    client = openai.OpenAI(api_key=key)
                    client.models.list()
                    console.print("[green]OpenAI connection successful![/green]")
                except Exception as e:
                    console.print(f"[red]OpenAI connection failed: {e}[/red]")
                    if not confirm_menu("Continue anyway?", default=False):
                        return self._edit_provider(ai_providers, prov)
            ai_providers.openai = {"api_key": key}
        elif prov == "anthropic":
            key = text_input("Anthropic API key", password=True)
            if not confirm_credential("Anthropic API key", key):
                return self._edit_provider(ai_providers, prov)
            if confirm_menu("Test Anthropic connection?", default=True):
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=key)
                    client.models.list()
                    console.print("[green]Anthropic connection successful![/green]")
                except Exception as e:
                    console.print(f"[red]Anthropic connection failed: {e}[/red]")
                    if not confirm_menu("Continue anyway?", default=False):
                        return self._edit_provider(ai_providers, prov)
            ai_providers.anthropic = {"api_key": key}
        elif prov == "google":
            key = text_input("Google Gemini API key", password=True)
            if not confirm_credential("Google Gemini API key", key):
                return self._edit_provider(ai_providers, prov)
            # Prompt for model name
            model = text_input("Google Gemini model name (see API docs or use 'models/gemini-1.5-pro-latest')", default="models/gemini-1.5-pro-latest")
            if confirm_menu("Test Google Gemini connection?", default=True):
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=key)
                    # Try to list models or access the selected model
                    resp = requests.get(f"https://generativelanguage.googleapis.com/v1beta/{model}", params={"key": key})
                    if resp.status_code == 200:
                        console.print("[green]Google Gemini connection successful![/green]")
                    else:
                        console.print(f"[red]Google Gemini model may be invalid or not accessible. Status: {resp.status_code}")
                        if not confirm_menu("Continue anyway?", default=False):
                            return self._edit_provider(ai_providers, prov)
                except Exception as e:
                    console.print(f"[red]Google Gemini connection failed: {e}[/red]")
                    if not confirm_menu("Continue anyway?", default=False):
                        return self._edit_provider(ai_providers, prov)
            ai_providers.google = {"api_key": key, "model": model}
        elif prov == "huggingface":
            key = text_input("Hugging Face API key", password=True)
            if not confirm_credential("Hugging Face API key", key):
                return self._edit_provider(ai_providers, prov)
            # Prompt for model name with retry logic
            while True:
                model = text_input("Hugging Face model name (e.g. 'mistralai/Mistral-7B-Instruct-v0.2')", default="mistralai/Mistral-7B-Instruct-v0.2")
                # Fetch model info
                model_info = None
                try:
                    resp = requests.get(f"https://huggingface.co/api/models/{model}")
                    if resp.status_code == 200:
                        model_info = resp.json()
                        desc = model_info.get('cardData', {}).get('summary', '') or model_info.get('pipeline_tag', '')
                        license = model_info.get('license', 'unknown')
                        console.print(f"[green]Model found:[/green] [bold]{model}[/bold] | [cyan]{desc}[/cyan] | License: [magenta]{license}[/magenta]")
                        break  # Valid model, exit loop
                    else:
                        console.print(f"[red]Model '{model}' not found on Hugging Face Hub.[/red]")
                        if not confirm_menu("Try another model name?", default=True):
                            return self._edit_provider(ai_providers, prov)
                except Exception as e:
                    console.print(f"[red]Error fetching model info: {e}[/red]")
                    if not confirm_menu("Try another model name?", default=True):
                        return self._edit_provider(ai_providers, prov)
            # Test connection
            if confirm_menu("Test Hugging Face connection?", default=True):
                try:
                    headers = {"Authorization": f"Bearer {key}"}
                    test_resp = requests.get("https://huggingface.co/api/whoami-v2", headers=headers)
                    if test_resp.status_code == 200:
                        console.print("[green]Hugging Face API key is valid![/green]")
                    else:
                        console.print(f"[red]Hugging Face API key may be invalid or rate-limited. Status: {test_resp.status_code}[/red]")
                        if not confirm_menu("Continue anyway?", default=False):
                            return self._edit_provider(ai_providers, prov)
                except Exception as e:
                    console.print(f"[red]Hugging Face connection failed: {e}[/red]")
                    if not confirm_menu("Continue anyway?", default=False):
                        return self._edit_provider(ai_providers, prov)
            ai_providers.huggingface = HuggingFaceConfig(api_key=key, models=[model], default_model=model)
        elif prov == "ollama":
            endpoint = text_input("Ollama endpoint", default="http://localhost:11434")
            if not confirm_credential("Ollama endpoint", endpoint):
                return self._edit_provider(ai_providers, prov)
            if confirm_menu("Test Ollama connection?", default=True):
                try:
                    resp = requests.get(f"{endpoint}/api/tags")
                    if resp.status_code == 200:
                        tags = resp.json().get('models', [])
                        tag_list = ', '.join([t['name'] for t in tags]) if tags else 'No models found.'
                        console.print(f"[green]Ollama connection successful! Models: {tag_list}[/green]")
                    else:
                        console.print(f"[red]Ollama endpoint error: {resp.status_code}[/red]")
                        if not confirm_menu("Continue anyway?", default=False):
                            return self._edit_provider(ai_providers, prov)
                except Exception as e:
                    console.print(f"[red]Ollama connection failed: {e}[/red]")
                    if not confirm_menu("Continue anyway?", default=False):
                        return self._edit_provider(ai_providers, prov)
            ai_providers.ollama = {"endpoint": endpoint}
        return ai_providers

    def load_config(self) -> AppConfig:
        """Load configuration from file."""
        if self.config:
            return self.config
        if not self.config_file.exists():
            raise FileNotFoundError(
                "Configuration not found. Please run 'github-readme-mcp setup' first."
            )
        with open(self.config_file, 'r') as f:
            data = yaml.safe_load(f)
        github_config = GitHubConfig(
            username=data['github']['username'],
            token=data['github']['token']
        )
        aip = data.get('ai_providers', {})
        ai_providers = AIProvidersConfig(
            openai=aip.get('openai'),
            anthropic=aip.get('anthropic'),
            google=aip.get('google'),
            huggingface=HuggingFaceConfig(
                api_key=aip['huggingface']['api_key'],
                models=[aip['huggingface']['model']],
                default_model=aip['huggingface']['model']
            ) if aip.get('huggingface') else None,
            ollama=aip.get('ollama')
        )
        self.config = AppConfig(
            github=github_config,
            alias=data.get('alias'),
            ai_providers=ai_providers
        )
        return self.config
    
    def save_config(self, config: AppConfig) -> None:
        """Save configuration to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        # Serialize AI providers
        aip = config.ai_providers
        data = {
            'github': {
                'username': config.github.username,
                'token': config.github.token
            },
            'alias': config.alias,
            'ai_providers': {
                'openai': dict(aip.openai) if aip and aip.openai else None,
                'anthropic': dict(aip.anthropic) if aip and aip.anthropic else None,
                'google': dict(aip.google) if aip and aip.google else None,
                'huggingface': {
                    'api_key': aip.huggingface.api_key,
                    'model': aip.huggingface.default_model
                } if aip and aip.huggingface else None,
                'ollama': dict(aip.ollama) if aip and aip.ollama else None,
            }
        }
        with open(self.config_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
        self.config_file.chmod(0o600)
    
    def _validate_github_credentials(self, username: str, token: str) -> bool:
        """Validate GitHub credentials by making a test API call."""
        try:
            from github import Github
            g = Github(token)
            user = g.get_user()
            return user.login == username
        except Exception as e:
            console.print(f"[red]Error validating credentials: {e}[/red]")
            return False
    
    def _create_alias(self, alias: str) -> None:
        """Create a shell alias for the command."""
        shell = os.environ.get('SHELL', '/bin/bash')
        
        if 'bash' in shell:
            rc_file = Path.home() / ".bashrc"
        elif 'zsh' in shell:
            rc_file = Path.home() / ".zshrc"
        else:
            console.print("[yellow]Could not determine shell. Please add alias manually.[/yellow]")
            return
        
        alias_line = f'alias {alias}="github-readme-mcp run"\n'
        
        # Check if alias already exists
        if rc_file.exists():
            with open(rc_file, 'r') as f:
                content = f.read()
                if alias_line.strip() in content:
                    console.print(f"[yellow]Alias '{alias}' already exists.[/yellow]")
                    return
        
        # Add alias to shell rc file
        with open(rc_file, 'a') as f:
            f.write(f"\n# GitHub README MCP Server alias\n{alias_line}")
        
        console.print(f"[green]✅ Alias '{alias}' created successfully![/green]")
        console.print(f"[yellow]Please restart your terminal or run 'source {rc_file}' to use the alias.[/yellow]")
    
    def get_github_config(self) -> GitHubConfig:
        """Get GitHub configuration."""
        config = self.load_config()
        return config.github
    
    def get_openai_key(self) -> Optional[str]:
        """Get OpenAI API key if configured."""
        config = self.load_config()
        return config.ai_providers.openai.get(config.alias)
    
    def update_token(self, new_token: str) -> None:
        """Update GitHub token."""
        config = self.load_config()
        config.github.token = new_token
        self.save_config(config)
        self.config = config