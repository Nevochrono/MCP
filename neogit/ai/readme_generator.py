import json
from rich.console import Console
from rich.panel import Panel
import openai
import anthropic
import google.generativeai as genai
import requests
from neogit.ai.project_analyzer import ProjectInfo

console = Console()

class READMEGenerator:
    SYSTEM_PROMPT = (
        "You are an expert technical writer and open source documentation specialist. "
        "Your job is to create clear, comprehensive, and engaging README.md files for software projects. "
        "You follow best practices for open source documentation, ensuring the README is well-structured, easy to navigate, and provides all essential information for users and contributors. "
        "You highlight the project's unique features, architecture, setup instructions, usage examples, contribution guidelines, and licensing. "
        "Always use professional Markdown formatting, include badges if relevant, and tailor the content to the project's language and framework. "
        "If the project is a library or API, include usage examples and API reference. "
        "If the project is an application, include screenshots or demo instructions if possible. "
        "Be concise but thorough, and make the README welcoming for both new users and contributors."
    )

    def __init__(self, ai_providers=None, selected_provider: str = "openai"):
        self.ai_providers = ai_providers or {}
        self.selected_provider = selected_provider
        self.openai_client = None
        self.anthropic_client = None
        self.google_client = None
        self.hf_client = None
        self.ollama_client = None
        # Setup clients based on config
        prov = self.selected_provider
        if prov == "openai" and self.ai_providers.get("openai"):
            self.openai_client = openai.OpenAI(api_key=self.ai_providers["openai"].get("api_key"))
        elif prov == "anthropic" and self.ai_providers.get("anthropic"):
            self.anthropic_client = anthropic.Anthropic(api_key=self.ai_providers["anthropic"].get("api_key"))
        elif prov == "google" and self.ai_providers.get("google"):
            genai.configure(api_key=self.ai_providers["google"].get("api_key"))
            self.google_client = genai.GenerativeModel('gemini-pro')
        elif prov == "huggingface" and self.ai_providers.get("huggingface"):
            self.hf_client = requests.Session()
            self.hf_api_key = self.ai_providers["huggingface"].api_key
            self.hf_model = self.ai_providers["huggingface"].default_model
        elif prov == "ollama" and self.ai_providers.get("ollama"):
            self.ollama_client = requests.Session()
            self.ollama_endpoint = self.ai_providers["ollama"].get("endpoint")

    def generate_readme(self, project_info: ProjectInfo, readme_type: str = "advanced") -> str:
        prov = self.selected_provider
        if prov == "openai" and self.openai_client:
            return self._generate_openai_readme(project_info, readme_type)
        elif prov == "anthropic" and self.anthropic_client:
            return self._generate_anthropic_readme(project_info, readme_type)
        elif prov == "google" and self.google_client:
            return self._generate_google_readme(project_info, readme_type)
        elif prov == "huggingface" and self.hf_client:
            return self._generate_huggingface_readme(project_info, readme_type)
        elif prov == "ollama" and self.ollama_client:
            return self._generate_ollama_readme(project_info, readme_type)
        else:
            return self._generate_template_readme(project_info, readme_type)

    def _generate_openai_readme(self, project_info: ProjectInfo, readme_type: str) -> str:
        try:
            # Pre-check: verify OpenAI API key and model
            try:
                models = self.openai_client.models.list()
                model_names = [m.id for m in models.data]
                if "gpt-3.5-turbo" not in model_names:
                    console.print(f"[red]OpenAI model 'gpt-3.5-turbo' is not accessible with your API key.[/red]")
                    console.print("[yellow]You can test your key with this command:")
                    console.print("[bold]curl https://api.openai.com/v1/models -H 'Authorization: Bearer <your_openai_api_key>'[/bold]")
                    return self._generate_template_readme(project_info, readme_type)
            except Exception as e:
                console.print(f"[red]OpenAI API key/model check failed: {e}[/red]")
                console.print("[yellow]You can test your key with this command:")
                console.print("[bold]curl https://api.openai.com/v1/models -H 'Authorization: Bearer <your_openai_api_key>'[/bold]")
                return self._generate_template_readme(project_info, readme_type)
            prompt = self._create_ai_prompt(project_info, readme_type)
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            console.print(f"[red]Error generating OpenAI README: {e}[/red]")
            console.print("[yellow]Falling back to template-based generation.[/yellow]")
            return self._generate_template_readme(project_info, readme_type)

    def _generate_anthropic_readme(self, project_info: ProjectInfo, readme_type: str) -> str:
        try:
            # Pre-check: verify Anthropic API key and model
            try:
                models = self.anthropic_client.models.list()
                model_names = [m["id"] for m in models["data"]]
                if "claude-3-haiku-20240307" not in model_names:
                    console.print(f"[red]Anthropic model 'claude-3-haiku-20240307' is not accessible with your API key.[/red]")
                    console.print("[yellow]You can test your key with this command:")
                    console.print("[bold]curl https://api.anthropic.com/v1/models -H 'x-api-key: <your_anthropic_api_key>'[/bold]")
                    return self._generate_template_readme(project_info, readme_type)
            except Exception as e:
                console.print(f"[red]Anthropic API key/model check failed: {e}[/red]")
                console.print("[yellow]You can test your key with this command:")
                console.print("[bold]curl https://api.anthropic.com/v1/models -H 'x-api-key: <your_anthropic_api_key>'[/bold]")
                return self._generate_template_readme(project_info, readme_type)
            prompt = self._create_ai_prompt(project_info, readme_type)
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                temperature=0.7,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            console.print(f"[red]Error generating Anthropic README: {e}[/red]")
            console.print("[yellow]Falling back to template-based generation.[/yellow]")
            return self._generate_template_readme(project_info, readme_type)

    def _generate_google_readme(self, project_info: ProjectInfo, readme_type: str) -> str:
        try:
            # Pre-check: verify Google Gemini model access
            try:
                models = self.google_client.list_models()
                model_names = [m.name for m in models]
                if "models/gemini-pro" not in model_names:
                    console.print(f"[red]Google Gemini model 'gemini-pro' is not accessible with your API key.[/red]")
                    console.print("[yellow]You can test your key with this command:")
                    console.print("[bold]curl -H 'Authorization: Bearer <your_google_api_key>' 'https://generativelanguage.googleapis.com/v1beta/models?key=<your_google_api_key>'[/bold]")
                    return self._generate_template_readme(project_info, readme_type)
            except Exception as e:
                console.print(f"[red]Google Gemini API key/model check failed: {e}[/red]")
                console.print("[yellow]You can test your key with this command:")
                console.print("[bold]curl -H 'Authorization: Bearer <your_google_api_key>' 'https://generativelanguage.googleapis.com/v1beta/models?key=<your_google_api_key>'[/bold]")
                return self._generate_template_readme(project_info, readme_type)
            prompt = self._create_ai_prompt(project_info, readme_type)
            full_prompt = f"{self.SYSTEM_PROMPT}\n\n{prompt}"
            response = self.google_client.generate_content(full_prompt)
            return response.text
        except Exception as e:
            console.print(f"[red]Error generating Google README: {e}[/red]")
            console.print("[yellow]Falling back to template-based generation.[/yellow]")
            return self._generate_template_readme(project_info, readme_type)

    def _generate_huggingface_readme(self, project_info: ProjectInfo, readme_type: str) -> str:
        try:
            # Pre-check: verify model is accessible with the API key
            api_url = f"https://api-inference.huggingface.co/models/{self.hf_model}"
            headers = {
                "Authorization": f"Bearer {self.hf_api_key}",
                "Content-Type": "application/json"
            }
            check_resp = self.hf_client.get(api_url, headers=headers)
            if check_resp.status_code != 200:
                console.print(f"[red]Hugging Face model '{self.hf_model}' is not accessible (status {check_resp.status_code}). Please check the model name and your API key.[/red]")
                try:
                    error_body = check_resp.json()
                except Exception:
                    error_body = check_resp.text
                console.print(f"[yellow]Hugging Face API response:[/yellow] {error_body}")
                console.print("[yellow]You can test your model and key with this command:")
                console.print(f"[bold]curl -H 'Authorization: Bearer <your_hf_api_key>' https://api-inference.huggingface.co/models/{self.hf_model}[/bold]")
                return self._generate_template_readme(project_info, readme_type)
            prompt = self._create_ai_prompt(project_info, readme_type)
            full_prompt = f"{self.SYSTEM_PROMPT}\n\n{prompt}"
            payload = {
                "inputs": full_prompt,
                "parameters": {
                    "max_new_tokens": 2000,
                    "temperature": 0.7,
                    "do_sample": True,
                    "top_p": 0.95
                }
            }
            response = self.hf_client.post(api_url, headers=headers, json=payload)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('generated_text', '')
                elif isinstance(result, dict):
                    return result.get('generated_text', '')
                else:
                    return str(result)
            else:
                console.print(f"[red]Hugging Face API error: {response.status_code}[/red]")
                return self._generate_template_readme(project_info, readme_type)
        except Exception as e:
            console.print(f"[red]Error generating Hugging Face README: {e}[/red]")
            console.print("[yellow]Falling back to template-based generation.[/yellow]")
            return self._generate_template_readme(project_info, readme_type)

    def _generate_ollama_readme(self, project_info: ProjectInfo, readme_type: str) -> str:
        try:
            # Pre-check: verify Ollama endpoint and model
            try:
                tags_resp = self.ollama_client.get(f"{self.ollama_endpoint}/api/tags")
                if tags_resp.status_code != 200:
                    console.print(f"[red]Ollama endpoint '{self.ollama_endpoint}' is not accessible (status {tags_resp.status_code}).[/red]")
                    console.print(f"[yellow]Ollama API response:[/yellow] {tags_resp.text}")
                    console.print("[yellow]You can test your endpoint with this command:")
                    console.print(f"[bold]curl {self.ollama_endpoint}/api/tags[/bold]")
                    return self._generate_template_readme(project_info, readme_type)
                tags = tags_resp.json().get('models', [])
                model_names = [t['name'] for t in tags]
                if "codellama:7b-instruct" not in model_names:
                    console.print(f"[red]Ollama model 'codellama:7b-instruct' is not available at your endpoint.[/red]")
                    console.print("[yellow]You can test your endpoint with this command:")
                    console.print(f"[bold]curl {self.ollama_endpoint}/api/tags[/bold]")
                    return self._generate_template_readme(project_info, readme_type)
            except Exception as e:
                console.print(f"[red]Ollama endpoint/model check failed: {e}[/red]")
                console.print("[yellow]You can test your endpoint with this command:")
                console.print(f"[bold]curl {self.ollama_endpoint}/api/tags[/bold]")
                return self._generate_template_readme(project_info, readme_type)
            prompt = self._create_ai_prompt(project_info, readme_type)
            full_prompt = f"{self.SYSTEM_PROMPT}\n\n{prompt}"
            api_url = f"{self.ollama_endpoint}/api/generate"
            payload = {
                "model": "codellama:7b-instruct",
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "num_predict": 2000
                }
            }
            response = self.ollama_client.post(api_url, json=payload)
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                console.print(f"[red]Ollama API error: {response.status_code}[/red]")
                return self._generate_template_readme(project_info, readme_type)
        except Exception as e:
            console.print(f"[red]Error generating Ollama README: {e}[/red]")
            console.print("[yellow]Falling back to template-based generation.[/yellow]")
            return self._generate_template_readme(project_info, readme_type)

    def _create_ai_prompt(self, project_info: ProjectInfo, readme_type: str) -> str:
        type_instructions = {
            "simple": (
                "Write a concise README.md for this project. "
                "Include: project title, a short description, installation steps, basic usage example, and license section. "
                "Use clear Markdown formatting and bullet points where appropriate."
            ),
            "advanced": (
                "Write a comprehensive, professional README.md for this project. "
                "Include the following sections: project title, badges (if relevant), detailed description, key features, architecture overview (with diagram if possible), installation instructions, configuration, usage examples, API reference (if applicable), contribution guidelines, code of conduct, FAQ, and license. "
                "Use advanced Markdown formatting, tables, and code blocks where appropriate. "
                "Highlight what makes this project unique and provide links to documentation or related resources."
            ),
            "installation": (
                "Write a README.md focused on installation and setup. "
                "Include: project title, description, prerequisites, detailed installation steps for different platforms (if relevant), configuration instructions, troubleshooting tips, and license. "
                "Use step-by-step instructions, code blocks, and highlight common pitfalls."
            )
        }
        return f"""
Project Name: {project_info.name}
Description: {project_info.description}
Language: {project_info.language}
Framework: {project_info.framework or 'None'}
Dependencies: {', '.join(project_info.dependencies[:5])}
Has Tests: {project_info.has_tests}
Has Documentation: {project_info.has_docs}
Has License: {project_info.has_license}

Project Structure:
- Source directories: {project_info.structure['src_dirs']}
- Configuration files: {project_info.structure['config_files']}
- Test directories: {project_info.structure['test_dirs']}

Key Files: {project_info.files[:10]}

Requirements:
{type_instructions.get(readme_type, type_instructions['advanced'])}
"""

    def _generate_template_readme(self, project_info: ProjectInfo, readme_type: str) -> str:
        if readme_type == "simple":
            return self._simple_template(project_info)
        elif readme_type == "installation":
            return self._installation_template(project_info)
        else:
            return self._advanced_template(project_info)

    def _simple_template(self, project_info: ProjectInfo) -> str:
        return f"""# {project_info.name}

{project_info.description}

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd {project_info.name}

# Install dependencies
{self._get_install_command(project_info)}
```

## Usage

```bash
# Run the project
{self._get_run_command(project_info)}
```

## License

This project is licensed under the MIT License.
"""

    def _installation_template(self, project_info: ProjectInfo) -> str:
        return f"""# {project_info.name}

{project_info.description}

## Prerequisites

- {project_info.language}
{f'- {project_info.framework}' if project_info.framework else ''}

## Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd {project_info.name}
```

### Step 2: Install Dependencies

```bash
{self._get_install_command(project_info)}
```

### Step 3: Configuration

{self._get_configuration_section(project_info)}

### Step 4: Verify Installation

```bash
{self._get_verify_command(project_info)}
```

## Troubleshooting

### Common Issues

1. **Dependency conflicts**: Try updating your package manager
2. **Permission errors**: Use `sudo` for system-wide installation
3. **Path issues**: Ensure the project is in your PATH

### Getting Help

If you encounter issues:
1. Check the [Issues](link-to-issues) page
2. Review the documentation
3. Contact the maintainers

## License

This project is licensed under the MIT License.
"""

    def _advanced_template(self, project_info: ProjectInfo) -> str:
        # Language icons
        lang_icons = {
            'Python': '🐍',
            'JavaScript/TypeScript': '⚡️',
            'Java': '☕',
            'C/C++': '💻',
            'Go': '🦦',
            'Rust': '🦀',
            'Ruby': '💎',
            'PHP': '🐘',
            'Unknown': '❓'
        }
        lang_icon = lang_icons.get(project_info.language, '❓')
        framework = f" | {project_info.framework}" if project_info.framework and project_info.framework != project_info.language else ""
        # Badges (example)
        badges = f"""
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Language](https://img.shields.io/badge/language-{project_info.language.replace(' ', '%20')}-blue.svg)
"""
        # Tech stack
        tech_stack = f"{lang_icon} {project_info.language}{framework}"
        if project_info.dependencies:
            tech_stack += " | " + ", ".join(project_info.dependencies[:5])
        return f"""# {project_info.name}

{badges}

{project_info.description}

## 🚀 Table of Contents
- [Features](#features)
- [Getting Started](#getting-started)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Tech Stack](#tech-stack)
- [Screenshots](#screenshots)
- [API Reference](#api-reference)
- [Contributing](#contributing)
- [Contact](#contact)
- [License](#license)

## ✨ Features
- **Modern {project_info.language}**: Built with the latest {project_info.language} features
{f'- **{project_info.framework} Integration**: Leverages {project_info.framework} for enhanced functionality' if project_info.framework else ''}
- **Comprehensive Testing**: {project_info.has_tests and 'Includes unit and integration tests' or 'Test coverage planned'}
- **Documentation**: {project_info.has_docs and 'Complete documentation included' or 'Documentation in development'}

## 🏁 Getting Started

Follow these steps to get your development environment set up:

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd {project_info.name}
   ```
2. **Install dependencies**
   ```bash
   {self._get_install_command(project_info)}
   ```
3. **Run the application**
   ```bash
   {self._get_run_command(project_info)}
   ```

## ⚙️ Installation

### Requirements
- {lang_icon} {project_info.language} 3.8+{f' | {project_info.framework}' if project_info.framework else ''}

### Quick Start
```bash
# Clone the repository
git clone <repository-url>
cd {project_info.name}

# Install dependencies
{self._get_install_command(project_info)}

# Run the application
{self._get_run_command(project_info)}
```

## 🛠️ Usage

### Basic Usage
```bash
{self._get_basic_usage(project_info)}
```

### Advanced Configuration
{self._get_configuration_section(project_info)}

## 🧰 Tech Stack
- {tech_stack}

## 📸 Screenshots
Add screenshots here:
```
![Screenshot 1](link-to-screenshot-1)
![Screenshot 2](link-to-screenshot-2)
```

## 📚 API Reference
{self._get_api_reference(project_info)}

## 🤝 Contributing
We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Clone the repository
git clone <repository-url>
cd {project_info.name}

# Install development dependencies
{self._get_dev_install_command(project_info)}

# Run tests
{self._get_test_command(project_info)}
```

## 📬 Contact
For questions, suggestions, or support, please open an issue or contact the maintainers.

## 📝 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
"""

    def _get_install_command(self, project_info: ProjectInfo) -> str:
        if project_info.language == 'Python':
            return "pip install -r requirements.txt"
        elif project_info.language == 'JavaScript/TypeScript':
            return "npm install"
        else:
            return "# Install dependencies based on your project type"

    def _get_run_command(self, project_info: ProjectInfo) -> str:
        if project_info.language == 'Python':
            return "python main.py"
        elif project_info.language == 'JavaScript/TypeScript':
            return "npm start"
        else:
            return "# Run the application based on your project type"

    def _get_configuration_section(self, project_info: ProjectInfo) -> str:
        if project_info.structure['config_files']:
            return f"""
The project uses the following configuration files:
{chr(10).join(f'- `{file}`' for file in project_info.structure['config_files'])}

Edit these files to customize the application behavior.
"""
        else:
            return """
Configuration can be done through environment variables or by editing the source code.
"""

    def _get_verify_command(self, project_info: ProjectInfo) -> str:
        if project_info.has_tests:
            return self._get_test_command(project_info)
        else:
            return f"{self._get_run_command(project_info)} --version"

    def _get_test_command(self, project_info: ProjectInfo) -> str:
        if project_info.language == 'Python':
            return "python -m pytest"
        elif project_info.language == 'JavaScript/TypeScript':
            return "npm test"
        else:
            return "# Run tests based on your project type"

    def _get_dev_install_command(self, project_info: ProjectInfo) -> str:
        if project_info.language == 'Python':
            return "pip install -r requirements-dev.txt"
        elif project_info.language == 'JavaScript/TypeScript':
            return "npm install --include=dev"
        else:
            return self._get_install_command(project_info)

    def _get_basic_usage(self, project_info: ProjectInfo) -> str:
        return f"""
# Basic usage
{self._get_run_command(project_info)}

# With options
{self._get_run_command(project_info)} --help
"""

    def _get_api_reference(self, project_info: ProjectInfo) -> str:
        return """
### Core Functions

- `main()`: Entry point of the application
- `config()`: Load configuration settings
- `run()`: Execute the main application logic

For detailed API documentation, please refer to the source code or generated documentation.
""" 