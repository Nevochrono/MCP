import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class ProjectInfo:
    name: str
    description: str
    language: str
    framework: Optional[str]
    dependencies: List[str]
    files: List[str]
    structure: Dict[str, Any]
    has_tests: bool
    has_docs: bool
    has_license: bool
    has_requirements: bool

class ProjectAnalyzer:
    def __init__(self, project_path: Path):
        self.project_path = project_path

    def analyze(self) -> ProjectInfo:
        files = self._get_project_files()
        language = self._detect_language(files)
        framework = self._detect_framework(files, language)
        dependencies = self._extract_dependencies(files, language)
        return ProjectInfo(
            name=self.project_path.name,
            description=self._generate_description(),
            language=language,
            framework=framework,
            dependencies=dependencies,
            files=files,
            structure=self._analyze_structure(),
            has_tests=self._has_tests(files),
            has_docs=self._has_docs(files),
            has_license=self._has_license(files),
            has_requirements=self._has_requirements(files, language)
        )

    def _get_project_files(self) -> List[str]:
        files = []
        for root, dirs, filenames in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', '.git']]
            for filename in filenames:
                if not filename.startswith('.') and not filename.endswith(('.pyc', '.log', '.tmp')):
                    rel_path = os.path.relpath(os.path.join(root, filename), self.project_path)
                    files.append(rel_path)
        return files

    def _detect_language(self, files: List[str]) -> str:
        extensions = {}
        for file in files:
            ext = Path(file).suffix.lower()
            if ext:
                extensions[ext] = extensions.get(ext, 0) + 1
        if '.py' in extensions:
            return 'Python'
        elif '.js' in extensions or '.ts' in extensions:
            return 'JavaScript/TypeScript'
        elif '.java' in extensions:
            return 'Java'
        elif '.cpp' in extensions or '.c' in extensions:
            return 'C/C++'
        elif '.go' in extensions:
            return 'Go'
        elif '.rs' in extensions:
            return 'Rust'
        elif '.rb' in extensions:
            return 'Ruby'
        elif '.php' in extensions:
            return 'PHP'
        else:
            return 'Unknown'

    def _detect_framework(self, files: List[str], language: str) -> Optional[str]:
        if language == 'Python':
            if any('django' in f.lower() for f in files):
                return 'Django'
            elif any('flask' in f.lower() for f in files):
                return 'Flask'
            elif any('fastapi' in f.lower() for f in files):
                return 'FastAPI'
            elif any('requirements.txt' in f for f in files):
                return 'Python'
        elif language == 'JavaScript/TypeScript':
            if any('package.json' in f for f in files):
                return 'Node.js'
            elif any('react' in f.lower() for f in files):
                return 'React'
            elif any('vue' in f.lower() for f in files):
                return 'Vue.js'
            elif any('angular' in f.lower() for f in files):
                return 'Angular'
        return None

    def _extract_dependencies(self, files: List[str], language: str) -> List[str]:
        dependencies = []
        if language == 'Python':
            req_files = [f for f in files if 'requirements' in f.lower() or f.endswith('.txt')]
            for req_file in req_files:
                try:
                    with open(self.project_path / req_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                dependencies.append(line.split('==')[0].split('>=')[0].split('<=')[0])
                except:
                    pass
        elif language == 'JavaScript/TypeScript':
            if 'package.json' in files:
                import json
                try:
                    with open(self.project_path / 'package.json', 'r') as f:
                        data = json.load(f)
                        if 'dependencies' in data:
                            dependencies.extend(data['dependencies'].keys())
                        if 'devDependencies' in data:
                            dependencies.extend(data['devDependencies'].keys())
                except:
                    pass
        return list(set(dependencies))[:10]

    def _generate_description(self) -> str:
        name = self.project_path.name
        description = name.replace('-', ' ').replace('_', ' ').title()
        return f"A {description.lower()} project"

    def _analyze_structure(self) -> Dict[str, Any]:
        structure = {
            'src_dirs': [],
            'config_files': [],
            'build_files': [],
            'test_dirs': []
        }
        for item in self.project_path.iterdir():
            if item.is_dir():
                if item.name in ['src', 'app', 'lib', 'source']:
                    structure['src_dirs'].append(item.name)
                elif 'test' in item.name.lower():
                    structure['test_dirs'].append(item.name)
            elif item.is_file():
                if any(ext in item.name.lower() for ext in ['.json', '.yaml', '.yml', '.toml', '.ini']):
                    structure['config_files'].append(item.name)
                elif any(ext in item.name.lower() for ext in ['.lock', '.spec', 'build']):
                    structure['build_files'].append(item.name)
        return structure

    def _has_tests(self, files: List[str]) -> bool:
        return any('test' in f.lower() or 'spec' in f.lower() for f in files)

    def _has_docs(self, files: List[str]) -> bool:
        return any('readme' in f.lower() or 'docs' in f.lower() for f in files)

    def _has_license(self, files: List[str]) -> bool:
        return any('license' in f.lower() for f in files)

    def _has_requirements(self, files: List[str], language: str) -> bool:
        if language == 'Python':
            return any('requirements' in f.lower() or f.endswith('.txt') for f in files)
        elif language == 'JavaScript/TypeScript':
            return 'package.json' in files
        return False

# ... ProjectAnalyzer class and related logic from readme_generator.py ... 