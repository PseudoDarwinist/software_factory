"""
Repository Processing Service
GitPython-based repository operations with system map generation
"""

import os
import shutil
import tempfile
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter

import git
from git import Repo, InvalidGitRepositoryError, GitCommandError

try:
    from ..models import SystemMap, Project, db
    from .background import JobContext, JobResult
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from models import SystemMap, Project, db
    from services.background import JobContext, JobResult


class RepositoryAnalysisError(Exception):
    """Custom exception for repository analysis errors"""
    pass


class SystemMapGenerator:
    """
    System map generator that analyzes repository structure and creates
    comprehensive system maps similar to the Node.js worker functionality
    """
    
    # File extensions to language mapping
    LANGUAGE_EXTENSIONS = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.jsx': 'React JSX',
        '.tsx': 'React TSX',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.cs': 'C#',
        '.php': 'PHP',
        '.rb': 'Ruby',
        '.go': 'Go',
        '.rs': 'Rust',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.html': 'HTML',
        '.css': 'CSS',
        '.scss': 'SCSS',
        '.sass': 'SASS',
        '.less': 'LESS',
        '.vue': 'Vue.js',
        '.svelte': 'Svelte',
        '.sql': 'SQL',
        '.sh': 'Shell Script',
        '.bash': 'Bash',
        '.zsh': 'Zsh',
        '.fish': 'Fish',
        '.ps1': 'PowerShell',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.json': 'JSON',
        '.xml': 'XML',
        '.toml': 'TOML',
        '.ini': 'INI',
        '.cfg': 'Config',
        '.conf': 'Config',
        '.md': 'Markdown',
        '.rst': 'reStructuredText',
        '.txt': 'Text',
        '.dockerfile': 'Docker',
        '.r': 'R',
        '.m': 'MATLAB',
        '.pl': 'Perl',
        '.lua': 'Lua',
        '.dart': 'Dart',
        '.elm': 'Elm',
        '.ex': 'Elixir',
        '.exs': 'Elixir',
        '.clj': 'Clojure',
        '.cljs': 'ClojureScript',
        '.hs': 'Haskell',
        '.ml': 'OCaml',
        '.fs': 'F#',
        '.jl': 'Julia'
    }
    
    # Framework detection patterns
    FRAMEWORK_PATTERNS = {
        'React': ['package.json', 'react', 'jsx', 'tsx'],
        'Vue.js': ['package.json', 'vue', '.vue'],
        'Angular': ['package.json', 'angular', '@angular'],
        'Svelte': ['package.json', 'svelte', '.svelte'],
        'Next.js': ['next.config.js', 'next.config.ts', 'pages/', 'app/'],
        'Nuxt.js': ['nuxt.config.js', 'nuxt.config.ts'],
        'Express.js': ['package.json', 'express'],
        'Fastify': ['package.json', 'fastify'],
        'Koa': ['package.json', 'koa'],
        'Flask': ['requirements.txt', 'flask', 'app.py'],
        'Django': ['requirements.txt', 'django', 'manage.py', 'settings.py'],
        'FastAPI': ['requirements.txt', 'fastapi', 'main.py'],
        'Spring Boot': ['pom.xml', 'build.gradle', 'spring-boot'],
        'Laravel': ['composer.json', 'artisan', 'laravel'],
        'Ruby on Rails': ['Gemfile', 'rails', 'config/application.rb'],
        'ASP.NET': ['.csproj', '.sln', 'Program.cs', 'Startup.cs'],
        'Gin': ['go.mod', 'gin-gonic'],
        'Echo': ['go.mod', 'echo'],
        'Actix': ['Cargo.toml', 'actix-web'],
        'Rocket': ['Cargo.toml', 'rocket'],
        'Phoenix': ['mix.exs', 'phoenix'],
        'Docker': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'],
        'Kubernetes': ['*.yaml', '*.yml', 'kind:', 'apiVersion:'],
        'Terraform': ['*.tf', '*.tfvars'],
        'Ansible': ['playbook.yml', 'ansible.cfg', 'inventory'],
        'Webpack': ['webpack.config.js', 'webpack.config.ts'],
        'Vite': ['vite.config.js', 'vite.config.ts'],
        'Rollup': ['rollup.config.js', 'rollup.config.ts'],
        'Parcel': ['package.json', 'parcel'],
        'Gatsby': ['gatsby-config.js', 'gatsby-node.js'],
        'Electron': ['package.json', 'electron'],
        'Tauri': ['src-tauri/', 'tauri.conf.json'],
        'Unity': ['*.unity', 'Assets/', 'ProjectSettings/'],
        'Unreal': ['*.uproject', 'Source/', 'Content/'],
        'Jupyter': ['*.ipynb', 'requirements.txt', 'jupyter'],
        'Streamlit': ['requirements.txt', 'streamlit', '*.py'],
        'Dash': ['requirements.txt', 'dash', '*.py'],
        'Gradio': ['requirements.txt', 'gradio', '*.py']
    }
    
    # Directories to ignore during analysis
    IGNORE_DIRECTORIES = {
        '.git', '.svn', '.hg', '.bzr',
        'node_modules', '__pycache__', '.pytest_cache',
        'venv', 'env', '.env', '.venv',
        'target', 'build', 'dist', 'out',
        '.idea', '.vscode', '.vs',
        'coverage', '.coverage', '.nyc_output',
        'logs', 'log', 'tmp', 'temp',
        '.DS_Store', 'Thumbs.db'
    }
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.logger = logging.getLogger(__name__)
    
    def generate_system_map(self) -> Dict[str, Any]:
        """
        Generate a comprehensive system map for the repository
        
        Returns:
            Dictionary containing the system map data
        """
        start_time = time.time()
        
        try:
            # Basic repository information
            system_map = {
                'timestamp': datetime.utcnow().isoformat(),
                'repository_path': str(self.repo_path),
                'status': 'completed',
                'generation_time_seconds': 0,
                'structure': {
                    'directories': [],
                    'files': [],
                    'languages': {},
                    'frameworks': [],
                    'file_count': 0,
                    'total_size_bytes': 0
                },
                'analysis': {
                    'file_types': {},
                    'directory_structure': {},
                    'largest_files': [],
                    'code_metrics': {
                        'total_lines': 0,
                        'code_lines': 0,
                        'comment_lines': 0,
                        'blank_lines': 0
                    }
                },
                'dependencies': {
                    'package_managers': [],
                    'config_files': [],
                    'build_tools': []
                },
                'git_info': {}
            }
            
            # Analyze repository structure
            self._analyze_structure(system_map)
            
            # Detect languages and frameworks
            self._detect_languages_and_frameworks(system_map)
            
            # Analyze dependencies and configuration
            self._analyze_dependencies(system_map)
            
            # Get Git information if available
            self._analyze_git_info(system_map)
            
            # Calculate generation time
            generation_time = time.time() - start_time
            system_map['generation_time_seconds'] = round(generation_time, 2)
            
            self.logger.info(f"System map generated in {generation_time:.2f} seconds")
            return system_map
            
        except Exception as e:
            self.logger.error(f"System map generation failed: {e}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'repository_path': str(self.repo_path),
                'status': 'error',
                'error': str(e),
                'generation_time_seconds': round(time.time() - start_time, 2)
            }
    
    def _analyze_structure(self, system_map: Dict[str, Any]):
        """Analyze the basic file and directory structure"""
        directories = []
        files = []
        file_sizes = []
        total_size = 0
        
        for root, dirs, filenames in os.walk(self.repo_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRECTORIES]
            
            # Get relative path from repository root
            rel_root = os.path.relpath(root, self.repo_path)
            if rel_root != '.':
                directories.append(rel_root)
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_file_path = os.path.relpath(file_path, self.repo_path)
                
                try:
                    file_size = os.path.getsize(file_path)
                    files.append(rel_file_path)
                    file_sizes.append((rel_file_path, file_size))
                    total_size += file_size
                except (OSError, IOError):
                    # Skip files that can't be accessed
                    continue
        
        # Sort and store results
        system_map['structure']['directories'] = sorted(directories)
        system_map['structure']['files'] = sorted(files)
        system_map['structure']['file_count'] = len(files)
        system_map['structure']['total_size_bytes'] = total_size
        
        # Store largest files (top 10)
        largest_files = sorted(file_sizes, key=lambda x: x[1], reverse=True)[:10]
        system_map['analysis']['largest_files'] = [
            {'path': path, 'size_bytes': size} for path, size in largest_files
        ]
    
    def _detect_languages_and_frameworks(self, system_map: Dict[str, Any]):
        """Detect programming languages and frameworks used in the repository"""
        language_counts = Counter()
        file_type_counts = Counter()
        detected_frameworks = set()
        
        # Analyze file extensions
        for file_path in system_map['structure']['files']:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext:
                file_type_counts[file_ext] += 1
                
                # Map extension to language
                if file_ext in self.LANGUAGE_EXTENSIONS:
                    language = self.LANGUAGE_EXTENSIONS[file_ext]
                    language_counts[language] += 1
        
        # Store language statistics
        system_map['structure']['languages'] = dict(language_counts)
        system_map['analysis']['file_types'] = dict(file_type_counts)
        
        # Detect frameworks
        all_files_lower = [f.lower() for f in system_map['structure']['files']]
        all_dirs_lower = [d.lower() for d in system_map['structure']['directories']]
        
        for framework, patterns in self.FRAMEWORK_PATTERNS.items():
            framework_detected = False
            
            for pattern in patterns:
                # Check for exact file matches
                if pattern in all_files_lower:
                    framework_detected = True
                    break
                
                # Check for directory matches
                if pattern.endswith('/') and pattern[:-1] in all_dirs_lower:
                    framework_detected = True
                    break
                
                # Check for pattern matches in file contents (for package.json, etc.)
                if pattern in ['react', 'vue', 'angular', 'express', 'flask', 'django']:
                    for file_path in system_map['structure']['files']:
                        if file_path.lower() in ['package.json', 'requirements.txt', 'pom.xml', 'build.gradle', 'composer.json', 'gemfile']:
                            try:
                                full_path = self.repo_path / file_path
                                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read().lower()
                                    if pattern in content:
                                        framework_detected = True
                                        break
                            except (IOError, OSError):
                                continue
                
                if framework_detected:
                    break
            
            if framework_detected:
                detected_frameworks.add(framework)
        
        system_map['structure']['frameworks'] = sorted(list(detected_frameworks))
    
    def _analyze_dependencies(self, system_map: Dict[str, Any]):
        """Analyze dependency management and configuration files"""
        package_managers = []
        config_files = []
        build_tools = []
        
        dependency_files = {
            'package.json': 'npm/yarn',
            'package-lock.json': 'npm',
            'yarn.lock': 'yarn',
            'requirements.txt': 'pip',
            'pipfile': 'pipenv',
            'poetry.lock': 'poetry',
            'pom.xml': 'maven',
            'build.gradle': 'gradle',
            'composer.json': 'composer',
            'gemfile': 'bundler',
            'cargo.toml': 'cargo',
            'go.mod': 'go modules',
            'mix.exs': 'mix'
        }
        
        config_file_patterns = [
            '.env', '.env.example', '.env.local',
            'config.json', 'config.yaml', 'config.yml',
            'settings.json', 'settings.yaml', 'settings.yml',
            'docker-compose.yml', 'docker-compose.yaml',
            'dockerfile', '.dockerignore',
            'makefile', 'cmake', 'build.sh',
            '.gitignore', '.gitattributes',
            'readme.md', 'license', 'changelog.md'
        ]
        
        build_file_patterns = [
            'webpack.config.js', 'vite.config.js', 'rollup.config.js',
            'gulpfile.js', 'gruntfile.js',
            'tsconfig.json', 'jsconfig.json',
            'babel.config.js', '.babelrc',
            'eslint.config.js', '.eslintrc',
            'prettier.config.js', '.prettierrc'
        ]
        
        for file_path in system_map['structure']['files']:
            file_name = Path(file_path).name.lower()
            
            # Check for dependency management files
            if file_name in dependency_files:
                package_manager = dependency_files[file_name]
                if package_manager not in package_managers:
                    package_managers.append(package_manager)
            
            # Check for configuration files
            if any(pattern in file_name for pattern in config_file_patterns):
                config_files.append(file_path)
            
            # Check for build tool files
            if any(pattern in file_name for pattern in build_file_patterns):
                build_tools.append(file_path)
        
        system_map['dependencies'] = {
            'package_managers': package_managers,
            'config_files': config_files[:20],  # Limit to first 20
            'build_tools': build_tools[:20]     # Limit to first 20
        }
    
    def _analyze_git_info(self, system_map: Dict[str, Any]):
        """Analyze Git repository information if available"""
        try:
            repo = Repo(self.repo_path)
            
            # Get basic repository info
            git_info = {
                'is_git_repo': True,
                'current_branch': repo.active_branch.name if repo.active_branch else None,
                'total_commits': len(list(repo.iter_commits())),
                'remote_urls': [remote.url for remote in repo.remotes],
                'last_commit': {
                    'hash': repo.head.commit.hexsha[:8],
                    'message': repo.head.commit.message.strip(),
                    'author': str(repo.head.commit.author),
                    'date': repo.head.commit.committed_datetime.isoformat()
                } if repo.head.commit else None
            }
            
            # Get branch information
            branches = []
            try:
                for branch in repo.branches:
                    branches.append(branch.name)
            except Exception:
                pass  # Skip if branches can't be accessed
            
            git_info['branches'] = branches[:10]  # Limit to first 10 branches
            
            system_map['git_info'] = git_info
            
        except (InvalidGitRepositoryError, Exception) as e:
            system_map['git_info'] = {
                'is_git_repo': False,
                'error': str(e)
            }


class RepositoryService:
    """
    Repository processing service that handles cloning, analysis, and system map generation
    Replaces the Node.js worker functionality with Python-based implementation
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.temp_dir = None
    
    def process_repository(self, context: JobContext, project_id: int, repository_url: str) -> JobResult:
        """
        Main repository processing function that handles the complete workflow:
        1. Clone repository
        2. Analyze structure
        3. Generate system map
        4. Store results in database
        
        Args:
            context: Job context for progress tracking
            project_id: ID of the project being processed
            repository_url: URL of the repository to process
        
        Returns:
            JobResult with success/failure status and data
        """
        start_time = time.time()
        
        try:
            context.update_progress(5, "Starting repository processing")
            
            # Validate inputs
            if not repository_url or not repository_url.strip():
                raise RepositoryAnalysisError("Repository URL is required")
            
            # Get project from database
            project = Project.query.get(project_id)
            if not project:
                raise RepositoryAnalysisError(f"Project {project_id} not found")
            
            context.update_progress(10, "Cloning repository")
            
            # Clone repository to temporary directory
            repo_path = self._clone_repository(repository_url, context)
            
            context.update_progress(40, "Analyzing repository structure")
            
            # Generate system map
            system_map_data = self._generate_system_map(repo_path, context)
            
            context.update_progress(80, "Storing system map in database")
            
            # Store system map in database
            generation_time = round(time.time() - start_time, 2)
            system_map = SystemMap.create_for_project(
                project_id=project_id,
                content=system_map_data,
                version='2.0',  # New Python-based version
                generation_time_seconds=generation_time
            )
            
            context.update_progress(85, "Processing repository for semantic search")
            
            # Process repository for vector search
            self._process_repository_for_vector_search(repo_path, project_id, context)
            
            # Update project status
            project.status = 'analyzed'
            project.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            context.update_progress(100, "Repository processing completed")
            
            result_data = {
                'system_map_id': system_map.id,
                'generation_time_seconds': generation_time,
                'repository_url': repository_url,
                'file_count': system_map_data.get('structure', {}).get('file_count', 0),
                'languages': list(system_map_data.get('structure', {}).get('languages', {}).keys()),
                'frameworks': system_map_data.get('structure', {}).get('frameworks', [])
            }
            
            self.logger.info(f"Repository processing completed for project {project_id} in {generation_time:.2f}s")
            return JobResult(success=True, data=result_data)
            
        except Exception as e:
            error_msg = f"Repository processing failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            # Update project status to error
            try:
                project = Project.query.get(project_id)
                if project:
                    project.update_status('error')
            except Exception:
                pass  # Don't fail on status update error
            
            return JobResult(success=False, error=error_msg)
        
        finally:
            # Cleanup temporary directory
            self._cleanup_temp_directory()
    
    def _clone_repository(self, repository_url: str, context: JobContext) -> str:
        """
        Clone repository to temporary directory with progress tracking
        
        Args:
            repository_url: URL of the repository to clone
            context: Job context for progress updates
        
        Returns:
            Path to the cloned repository
        """
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix='repo_analysis_')
            repo_path = os.path.join(self.temp_dir, 'repository')
            
            self.logger.info(f"Cloning repository {repository_url} to {repo_path}")
            
            # Clone with depth 1 for faster cloning (shallow clone)
            context.update_progress(15, "Initializing git clone")
            
            repo = Repo.clone_from(
                repository_url,
                repo_path,
                depth=1,  # Shallow clone for faster processing
                single_branch=True  # Only clone the default branch
            )
            
            context.update_progress(35, "Repository cloned successfully")
            
            # Verify the repository was cloned successfully
            if not os.path.exists(repo_path) or not os.listdir(repo_path):
                raise RepositoryAnalysisError("Repository clone appears to be empty")
            
            self.logger.info(f"Successfully cloned repository to {repo_path}")
            return repo_path
            
        except GitCommandError as e:
            raise RepositoryAnalysisError(f"Git clone failed: {str(e)}")
        except Exception as e:
            raise RepositoryAnalysisError(f"Repository cloning error: {str(e)}")
    
    def _generate_system_map(self, repo_path: str, context: JobContext) -> Dict[str, Any]:
        """
        Generate system map for the cloned repository
        
        Args:
            repo_path: Path to the cloned repository
            context: Job context for progress updates
        
        Returns:
            System map data dictionary
        """
        try:
            context.update_progress(45, "Initializing system map generator")
            
            generator = SystemMapGenerator(repo_path)
            
            context.update_progress(50, "Analyzing repository structure")
            
            system_map_data = generator.generate_system_map()
            
            context.update_progress(75, "System map generation completed")
            
            # Validate system map data
            if not system_map_data or system_map_data.get('status') == 'error':
                error_msg = system_map_data.get('error', 'Unknown system map generation error')
                raise RepositoryAnalysisError(f"System map generation failed: {error_msg}")
            
            self.logger.info(f"System map generated successfully with {system_map_data.get('structure', {}).get('file_count', 0)} files")
            return system_map_data
            
        except Exception as e:
            raise RepositoryAnalysisError(f"System map generation error: {str(e)}")
    
    def _process_repository_for_vector_search(self, repo_path: str, project_id: int, context: JobContext):
        """
        Process repository files for vector search and semantic indexing
        
        Args:
            repo_path: Path to the cloned repository
            project_id: ID of the project being processed
            context: Job context for progress updates
        """
        try:
            # Import vector service
            from .vector_service import get_vector_service
            vector_service = get_vector_service()
            
            if not vector_service:
                self.logger.warning("Vector service not available, skipping semantic indexing")
                return
            
            context.update_progress(87, "Indexing repository for semantic search")
            
            # Process the repository for vector search
            success = vector_service.process_code_repository(repo_path, str(project_id))
            
            if success:
                context.update_progress(95, "Repository indexed for semantic search")
                self.logger.info(f"Repository {project_id} successfully indexed for semantic search")
            else:
                self.logger.warning(f"Failed to index repository {project_id} for semantic search")
            
        except Exception as e:
            self.logger.warning(f"Vector search processing failed for project {project_id}: {e}")
            # Don't fail the entire job if vector processing fails
    
    def _cleanup_temp_directory(self):
        """Clean up temporary directory used for repository cloning"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.logger.debug(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temporary directory {self.temp_dir}: {e}")
            finally:
                self.temp_dir = None
    
    def get_repository_info(self, repository_url: str) -> Dict[str, Any]:
        """
        Get basic repository information without full cloning (for validation)
        
        Args:
            repository_url: URL of the repository
        
        Returns:
            Basic repository information
        """
        try:
            # For now, just validate the URL format
            # In the future, this could use git ls-remote to get basic info
            if not repository_url or not repository_url.strip():
                raise ValueError("Repository URL is required")
            
            # Basic URL validation
            if not (repository_url.startswith('http://') or 
                   repository_url.startswith('https://') or 
                   repository_url.startswith('git@')):
                raise ValueError("Invalid repository URL format")
            
            return {
                'url': repository_url,
                'valid': True,
                'accessible': None  # Would need actual git command to verify
            }
            
        except Exception as e:
            return {
                'url': repository_url,
                'valid': False,
                'error': str(e)
            }


# Global repository service instance
repository_service = RepositoryService()


def get_repository_service() -> RepositoryService:
    """Get the global repository service instance"""
    return repository_service