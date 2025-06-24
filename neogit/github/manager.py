from github import Github
from pathlib import Path
from rich.console import Console
import base64
import os
from neogit.utils.file_utils import is_binary
from github import InputGitTreeElement
import mimetypes
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.prompt import Prompt

console = Console()

EXCLUDE_PATTERNS = ['.git', 'node_modules', '__pycache__', 'venv', '.DS_Store', '.mypy_cache']
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

class GitHubManager:
    def __init__(self, token, username):
        self.token = token
        self.username = username
        self.client = Github(token)

    def deploy_project(self, project_path: Path, readme_path: Path, project_info, branch: str = 'main', private: bool = False):
        repo_name = project_info.name.replace(' ', '-').replace('_', '-')
        repo_name = ''.join(c for c in repo_name if c.isalnum() or c in '-_')
        repo = self._get_or_create_repo(repo_name, project_info.description, private=private)
        if not repo:
            console.print(f"[red]Failed to get or create repository: {repo_name}[/red]")
            return
        self._upload_files(repo, project_path, readme_path, branch=branch)

    def _get_or_create_repo(self, repo_name, description, private=False):
        user = self.client.get_user()
        try:
            repo = user.get_repo(repo_name)
            console.print(f"[yellow]Repository {repo_name} exists. Updating...[/yellow]")
            return repo
        except Exception:
            try:
                repo = user.create_repo(
                    name=repo_name,
                    description=description,
                    private=private
                )
                console.print(f"[green]Created new repository: {repo_name}[/green]")
                return repo
            except Exception as e:
                console.print(f"[red]Error creating repository: {e}[/red]")
                return None

    def _upload_files(self, repo, project_path: Path, readme_path: Path, branch: str = 'main'):
        # Gather all files to upload
        files_to_upload = []
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_PATTERNS and not d.startswith('.')]
            for file in files:
                if file.startswith('.') or file in EXCLUDE_PATTERNS:
                    continue
                file_path = Path(root) / file
                rel_path = file_path.relative_to(project_path)
                if file_path == readme_path:
                    rel_path = 'README.md'
                if file_path.stat().st_size > MAX_FILE_SIZE:
                    console.print(f"[yellow]Skipping large file: {rel_path}[/yellow]")
                    continue
                files_to_upload.append((file_path, str(rel_path)))

        # Ensure branch exists
        try:
            ref = repo.get_git_ref(f'heads/{branch}')
            latest_commit = repo.get_git_commit(ref.object.sha)
            base_tree = repo.get_git_tree(latest_commit.tree.sha)
        except Exception as e:
            # Handle empty repository (409 error)
            if hasattr(e, 'status') and e.status == 409 or 'Git Repository is empty' in str(e):
                # Find the README file to use as the first commit
                readme_tuple = next(((fp, rp) for fp, rp in files_to_upload if str(rp).lower() == 'readme.md'), None)
                if not readme_tuple:
                    console.print("[red]Cannot initialize empty repository: README.md not found in project.[/red]")
                    return
                file_path, rel_path = readme_tuple
                with open(file_path, 'rb') as f:
                    content = f.read()
                    repo.create_file(rel_path, f"Initial commit: {rel_path}", content.decode('utf-8'), branch=branch)
                    console.print(f"[green]Initialized repository with {rel_path} on branch {branch}.[/green]")
                # Remove README from upload list (already uploaded)
                files_to_upload = [t for t in files_to_upload if t != readme_tuple]
                # Now the branch exists, re-fetch refs
                ref = repo.get_git_ref(f'heads/{branch}')
                latest_commit = repo.get_git_commit(ref.object.sha)
                base_tree = repo.get_git_tree(latest_commit.tree.sha)
            else:
                # Branch does not exist, create it from main or default branch
                try:
                    master_ref = repo.get_git_ref('heads/main')
                except Exception:
                    master_ref = repo.get_git_ref(f'heads/{repo.default_branch}')
                ref = repo.create_git_ref(ref=f'refs/heads/{branch}', sha=master_ref.object.sha)
                latest_commit = repo.get_git_commit(master_ref.object.sha)
                base_tree = repo.get_git_tree(latest_commit.tree.sha)

        tree_elements = []
        with Progress(SpinnerColumn(), BarColumn(), TextColumn("{task.description}"), console=console) as progress:
            upload_task = progress.add_task("[cyan]Uploading files...", total=len(files_to_upload))
            for file_path, rel_path in files_to_upload:
                while True:
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read()
                            mime, _ = mimetypes.guess_type(file_path)
                            is_bin = is_binary(content)
                            icon = "📄" if not is_bin else ("🖼️" if mime and mime.startswith('image') else "💾")
                            if is_bin:
                                # Prepare binary file for commit as blob
                                blob = repo.create_git_blob(base64.b64encode(content).decode('utf-8'), 'base64')
                                tree_elements.append(InputGitTreeElement(rel_path, '100644', 'blob', sha=blob.sha))
                                progress.console.print(f"{icon} [cyan]Prepared binary file for upload:[/cyan] {rel_path}")
                            else:
                                # Text file: check if it exists, then create or update
                                try:
                                    contents = repo.get_contents(rel_path, ref=branch)
                                    # File exists, update
                                    repo.update_file(rel_path, f"Update {rel_path}", content.decode('utf-8'), contents.sha, branch=branch)
                                    progress.console.print(f"{icon} [yellow]Updated text file:[/yellow] {rel_path}")
                                except Exception as e:
                                    if '404' in str(e) or 'Not Found' in str(e):
                                        # File does not exist, create
                                        repo.create_file(rel_path, f"Add {rel_path}", content.decode('utf-8'), branch=branch)
                                        progress.console.print(f"{icon} [green]Uploaded text file:[/green] {rel_path}")
                                    else:
                                        raise e
                        break
                    except Exception as e:
                        progress.console.print(f"[red]Error uploading {rel_path}: {e}[/red]")
                        action = None
                        while action not in ["r", "s", "a"]:
                            action = Prompt.ask(f"[red]Retry (r), Skip (s), or Abort (a)?[/red]", choices=["r", "s", "a"], default="s")
                        if action == "r":
                            continue
                        elif action == "s":
                            break
                        elif action == "a":
                            progress.console.print("[red]Aborted upload process by user.[/red]")
                            return
                    finally:
                        progress.advance(upload_task)
        # Commit binary files if any
        if tree_elements:
            try:
                # Re-fetch latest commit/tree for branch after text file updates
                ref = repo.get_git_ref(f'heads/{branch}')
                latest_commit = repo.get_git_commit(ref.object.sha)
                base_tree = repo.get_git_tree(latest_commit.tree.sha)
                new_tree = repo.create_git_tree(tree_elements, base_tree)
                commit_message = "Add/update binary files"
                new_commit = repo.create_git_commit(commit_message, new_tree, [latest_commit])
                ref.edit(new_commit.sha)
                console.print(f"[green]Committed binary files to branch {branch}.[/green]")
            except Exception as e:
                console.print(f"[red]Error committing binary files: {e}[/red]")

def deploy_to_github():
    print("Project deployed to GitHub (placeholder).") 