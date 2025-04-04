"""
Development Tools for Quantum Cellular Computing.

This module provides utilities for QCC development, including:
- Cell template generation
- Code generation tools
- Development environment setup
- Testing utilities
- Configuration management
- Debugging helpers
"""

import os
import sys
import json
import shutil
import logging
import asyncio
import argparse
import datetime
import subprocess
import importlib.util
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable
from pathlib import Path
import re
import yaml
import jinja2
import colorama
from colorama import Fore, Style

# Initialize colorama for cross-platform colored terminal output
colorama.init()

# Set up logging
logger = logging.getLogger(__name__)

# Constants
CELL_TEMPLATE_DIR = Path(__file__).parent / "templates" / "cells"
PROJECT_TEMPLATE_DIR = Path(__file__).parent / "templates" / "projects"
CONFIG_TEMPLATE_DIR = Path(__file__).parent / "templates" / "configs"
QCC_ROOT = Path(__file__).parent.parent.parent


class TemplateRenderer:
    """
    Renders templates for code generation.
    
    Attributes:
        template_env: Jinja2 environment for template rendering
        template_dirs: Directories containing templates
    """
    
    def __init__(self, template_dirs: List[Path] = None):
        """
        Initialize the template renderer.
        
        Args:
            template_dirs: List of directories containing templates
        """
        if template_dirs is None:
            template_dirs = [CELL_TEMPLATE_DIR, PROJECT_TEMPLATE_DIR, CONFIG_TEMPLATE_DIR]
        
        self.template_dirs = template_dirs
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader([str(d) for d in template_dirs]),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        # Register custom filters
        self.template_env.filters['camel_case'] = self._to_camel_case
        self.template_env.filters['snake_case'] = self._to_snake_case
        self.template_env.filters['pascal_case'] = self._to_pascal_case
        self.template_env.filters['human_readable'] = self._to_human_readable
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of the template file
            context: Dictionary of variables to use in the template
            
        Returns:
            Rendered template as a string
        """
        try:
            template = self.template_env.get_template(template_name)
            return template.render(**context)
        except jinja2.exceptions.TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            all_templates = []
            for dir_path in self.template_dirs:
                if dir_path.exists():
                    all_templates.extend([f.name for f in dir_path.glob('*.j2')])
            logger.info(f"Available templates: {', '.join(all_templates)}")
            raise ValueError(f"Template not found: {template_name}")
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            raise
    
    def render_to_file(self, template_name: str, context: Dict[str, Any], output_path: Path) -> Path:
        """
        Render a template and save to a file.
        
        Args:
            template_name: Name of the template file
            context: Dictionary of variables to use in the template
            output_path: Path to save the rendered template
            
        Returns:
            Path to the created file
        """
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Render template
        content = self.render_template(template_name, context)
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Generated file: {output_path}")
        return output_path
    
    def _to_camel_case(self, s: str) -> str:
        """Convert string to camelCase."""
        s = re.sub(r'[^a-zA-Z0-9]', ' ', s)
        words = s.split()
        if not words:
            return ''
        return words[0].lower() + ''.join(word.capitalize() for word in words[1:])
    
    def _to_snake_case(self, s: str) -> str:
        """Convert string to snake_case."""
        s = re.sub(r'[^a-zA-Z0-9]', ' ', s)
        return '_'.join(s.lower().split())
    
    def _to_pascal_case(self, s: str) -> str:
        """Convert string to PascalCase."""
        s = re.sub(r'[^a-zA-Z0-9]', ' ', s)
        return ''.join(word.capitalize() for word in s.split())
    
    def _to_human_readable(self, s: str) -> str:
        """Convert string to Human Readable Format."""
        s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)  # Split camelCase
        s = re.sub(r'[_-]', ' ', s)  # Replace underscores and hyphens with spaces
        s = re.sub(r'\s+', ' ', s)  # Normalize spaces
        return s.strip().capitalize()


class CellGenerator:
    """
    Generates cell templates and scaffolding for QCC development.
    
    Attributes:
        template_renderer: Template renderer for code generation
        cells_dir: Directory to store generated cells
    """
    
    def __init__(self, cells_dir: Path = None, template_renderer: TemplateRenderer = None):
        """
        Initialize the cell generator.
        
        Args:
            cells_dir: Directory to store generated cells
            template_renderer: Template renderer for code generation
        """
        self.cells_dir = cells_dir or (QCC_ROOT / "src" / "cells")
        self.template_renderer = template_renderer or TemplateRenderer()
    
    def create_cell(
        self,
        name: str,
        capability: str,
        cell_type: str = "application",
        description: str = None,
        author: str = None,
        version: str = "1.0.0"
    ) -> Path:
        """
        Create a new cell with the specified parameters.
        
        Args:
            name: Name of the cell
            capability: Primary capability of the cell
            cell_type: Type of cell (system, middleware, application)
            description: Description of the cell
            author: Author of the cell
            version: Cell version
            
        Returns:
            Path to the created cell directory
        """
        # Sanitize name
        cell_name = self._sanitize_name(name)
        
        # Create context for templates
        context = {
            "name": cell_name,
            "capability": capability,
            "cell_type": cell_type,
            "description": description or f"A cell that provides {capability} capability",
            "author": author or "QCC Developer",
            "version": version,
            "created_at": datetime.datetime.now().isoformat(),
            "class_name": self._to_class_name(cell_name)
        }
        
        # Determine cell directory path
        cell_dir = self.cells_dir / cell_type / cell_name
        
        # Check if cell already exists
        if cell_dir.exists():
            logger.warning(f"Cell directory already exists: {cell_dir}")
            response = input(f"Cell '{cell_name}' already exists. Overwrite? (y/n): ")
            if response.lower() != 'y':
                logger.info("Cell creation cancelled")
                return cell_dir
            
            # Backup existing cell
            backup_dir = cell_dir.parent / f"{cell_name}_backup_{int(datetime.datetime.now().timestamp())}"
            shutil.copytree(cell_dir, backup_dir)
            logger.info(f"Created backup of existing cell: {backup_dir}")
        
        # Create cell directory
        cell_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate cell files
        self.template_renderer.render_to_file(
            "cell_main.py.j2", context, cell_dir / "main.py"
        )
        self.template_renderer.render_to_file(
            "cell_manifest.json.j2", context, cell_dir / "manifest.json"
        )
        self.template_renderer.render_to_file(
            "cell_readme.md.j2", context, cell_dir / "README.md"
        )
        
        # Create tests directory
        tests_dir = cell_dir / "tests"
        tests_dir.mkdir(exist_ok=True)
        self.template_renderer.render_to_file(
            "cell_test.py.j2", context, tests_dir / "test_cell.py"
        )
        
        # Create requirements file if it doesn't exist
        if not (cell_dir / "requirements.txt").exists():
            with open(cell_dir / "requirements.txt", 'w') as f:
                f.write(f"# Requirements for {cell_name} cell\n")
        
        logger.info(f"Created cell: {cell_name} in {cell_dir}")
        logger.info(f"Cell provides capability: {capability}")
        
        return cell_dir
    
    def generate_capabilities(self, cell_dir: Path, capabilities: List[str]) -> None:
        """
        Generate capability implementations for an existing cell.
        
        Args:
            cell_dir: Path to the cell directory
            capabilities: List of capabilities to implement
        """
        if not cell_dir.exists():
            logger.error(f"Cell directory does not exist: {cell_dir}")
            return
        
        # Read cell manifest
        manifest_path = cell_dir / "manifest.json"
        if not manifest_path.exists():
            logger.error(f"Cell manifest not found: {manifest_path}")
            return
        
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read cell manifest: {e}")
            return
        
        # Get cell information
        cell_name = manifest.get("name", cell_dir.name)
        existing_capabilities = [c["name"] for c in manifest.get("capabilities", [])]
        
        # Read main.py
        main_path = cell_dir / "main.py"
        if not main_path.exists():
            logger.error(f"Cell main.py not found: {main_path}")
            return
        
        with open(main_path, 'r') as f:
            main_content = f.read()
        
        # Create context for capability template
        context = {
            "name": cell_name,
            "capabilities": capabilities,
            "class_name": self._extract_class_name(main_content) or self._to_class_name(cell_name)
        }
        
        # Generate capability implementations
        for capability in capabilities:
            if capability in existing_capabilities:
                logger.warning(f"Capability {capability} already exists in cell {cell_name}")
                continue
            
            # Add capability to manifest
            manifest["capabilities"].append({
                "name": capability,
                "description": f"Provides {capability} functionality",
                "version": manifest.get("version", "1.0.0"),
                "parameters": [],
                "outputs": []
            })
            
            # Generate capability implementation
            capability_content = self.template_renderer.render_template(
                "cell_capability.py.j2",
                {"name": cell_name, "capability": capability, "class_name": context["class_name"]}
            )
            
            # Append to main.py
            with open(main_path, 'a') as f:
                f.write("\n\n")
                f.write(capability_content)
            
            logger.info(f"Added capability {capability} to cell {cell_name}")
        
        # Save updated manifest
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Updated cell manifest with new capabilities")
    
    def create_cell_package(self, cell_dir: Path, output_dir: Path = None) -> Path:
        """
        Create a deployable package for a cell.
        
        Args:
            cell_dir: Path to the cell directory
            output_dir: Directory to store the package
            
        Returns:
            Path to the created package
        """
        if not cell_dir.exists():
            logger.error(f"Cell directory does not exist: {cell_dir}")
            return None
        
        # Get cell information
        manifest_path = cell_dir / "manifest.json"
        if not manifest_path.exists():
            logger.error(f"Cell manifest not found: {manifest_path}")
            return None
        
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read cell manifest: {e}")
            return None
        
        cell_name = manifest.get("name", cell_dir.name)
        cell_version = manifest.get("version", "1.0.0")
        
        # Create package directory
        output_dir = output_dir or (QCC_ROOT / "dist" / "cells")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        package_name = f"{cell_name}-{cell_version}.qcc"
        package_path = output_dir / package_name
        
        # Create temporary directory for package contents
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Copy cell files
            for item in cell_dir.glob("**/*"):
                if item.is_file() and not item.name.endswith(('.pyc', '.pyo')):
                    relative_path = item.relative_to(cell_dir)
                    dest_path = temp_path / relative_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)
            
            # Create package file (ZIP archive)
            shutil.make_archive(str(package_path).replace('.qcc', ''), 'zip', temp_dir)
            
            # Rename to .qcc extension
            if package_path.with_suffix('.zip').exists():
                os.rename(package_path.with_suffix('.zip'), package_path)
        
        logger.info(f"Created cell package: {package_path}")
        return package_path
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize a cell name.
        
        Args:
            name: Cell name to sanitize
            
        Returns:
            Sanitized cell name
        """
        # Replace spaces and special characters with underscores
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        
        # Ensure name starts with a letter
        if not name[0].isalpha():
            name = 'cell_' + name
        
        # Convert to snake_case
        return self._to_snake_case(name)
    
    def _to_class_name(self, name: str) -> str:
        """
        Convert a cell name to a class name.
        
        Args:
            name: Cell name
            
        Returns:
            Class name in PascalCase
        """
        # Replace non-alphanumeric characters with spaces
        name = re.sub(r'[^a-zA-Z0-9]', ' ', name)
        
        # Convert to PascalCase
        return ''.join(word.capitalize() for word in name.split())
    
    def _to_snake_case(self, s: str) -> str:
        """Convert string to snake_case."""
        s = re.sub(r'[^a-zA-Z0-9]', ' ', s)
        return '_'.join(s.lower().split())
    
    def _extract_class_name(self, content: str) -> Optional[str]:
        """
        Extract the class name from cell main.py content.
        
        Args:
            content: Content of main.py
            
        Returns:
            Class name if found, None otherwise
        """
        class_match = re.search(r'class\s+(\w+)', content)
        if class_match:
            return class_match.group(1)
        return None


class DevelopmentEnvironment:
    """
    Manages the QCC development environment.
    
    Attributes:
        config: Development environment configuration
        qcc_root: Root directory of the QCC project
        template_renderer: Template renderer for code generation
    """
    
    def __init__(self, config_path: Path = None):
        """
        Initialize the development environment.
        
        Args:
            config_path: Path to the development configuration file
        """
        self.qcc_root = QCC_ROOT
        self.template_renderer = TemplateRenderer()
        self.config = self._load_config(config_path)
        
        # Initialize child services
        self.cell_generator = CellGenerator(
            cells_dir=self.qcc_root / "src" / "cells",
            template_renderer=self.template_renderer
        )
    
    def _load_config(self, config_path: Path = None) -> Dict[str, Any]:
        """
        Load the development configuration.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config_path = self.qcc_root / "config" / "development.yaml"
        config_path = config_path or default_config_path
        
        # Default configuration
        default_config = {
            "development_mode": True,
            "log_level": "debug",
            "local_provider_port": 8081,
            "local_assembler_port": 8080,
            "dashboard_port": 8082,
            "auto_test_on_build": True,
            "lint_on_build": True,
            "profile_performance": True,
            "cell_template_dir": str(CELL_TEMPLATE_DIR),
            "project_template_dir": str(PROJECT_TEMPLATE_DIR),
            "config_template_dir": str(CONFIG_TEMPLATE_DIR),
            "data_directory": str(self.qcc_root / "data"),
            "experimental_features_enabled": True
        }
        
        # Load configuration file if it exists
        config = default_config.copy()
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                
                # Update config with file values
                if file_config:
                    self._update_nested_dict(config, file_config)
                    
            except Exception as e:
                logger.error(f"Failed to load configuration from {config_path}: {e}")
                logger.warning("Using default configuration")
        else:
            logger.warning(f"Configuration file not found: {config_path}")
            logger.info("Using default configuration")
            
            # Create default configuration if it doesn't exist
            if config_path == default_config_path:
                self._create_default_config(default_config_path, default_config)
        
        return config
    
    def _update_nested_dict(self, d: Dict, u: Dict) -> Dict:
        """
        Update a nested dictionary with values from another dictionary.
        
        Args:
            d: Dictionary to update
            u: Dictionary with new values
            
        Returns:
            Updated dictionary
        """
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._update_nested_dict(d[k], v)
            else:
                d[k] = v
        return d
    
    def _create_default_config(self, config_path: Path, config: Dict[str, Any]) -> None:
        """
        Create a default configuration file.
        
        Args:
            config_path: Path to save the configuration
            config: Configuration dictionary
        """
        try:
            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write configuration
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            logger.info(f"Created default configuration: {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to create default configuration: {e}")
    
    def setup_dev_environment(self) -> bool:
        """
        Set up the development environment.
        
        Returns:
            True if setup is successful, False otherwise
        """
        logger.info("Setting up QCC development environment")
        
        try:
            # Create required directories
            self._create_directories()
            
            # Install dependencies if needed
            if self._should_install_dependencies():
                self._install_dependencies()
            
            # Generate configuration files
            self._generate_configs()
            
            # Set up local services
            self._setup_local_services()
            
            logger.info("Development environment setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up development environment: {e}", exc_info=True)
            return False
    
    def _create_directories(self) -> None:
        """Create required directories for development."""
        directories = [
            self.qcc_root / "data",
            self.qcc_root / "data" / "user_files",
            self.qcc_root / "data" / "cell-cache",
            self.qcc_root / "data" / "quantum-trail",
            self.qcc_root / "logs",
            self.qcc_root / "dist",
            self.qcc_root / "dist" / "cells"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
    
    def _should_install_dependencies(self) -> bool:
        """Check if dependencies should be installed."""
        # Check if requirements.txt exists
        requirements_path = self.qcc_root / "requirements.txt"
        if not requirements_path.exists():
            logger.warning("requirements.txt not found, skipping dependency installation")
            return False
        
        # Ask user if they want to install dependencies
        response = input("Do you want to install dependencies? (y/n): ")
        return response.lower() == 'y'
    
    def _install_dependencies(self) -> None:
        """Install project dependencies."""
        requirements_path = self.qcc_root / "requirements.txt"
        
        logger.info("Installing dependencies...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)],
                check=True
            )
            logger.info("Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies: {e}")
            raise
    
    def _generate_configs(self) -> None:
        """Generate configuration files for development."""
        # Check if config directory exists
        config_dir = self.qcc_root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Define configuration templates
        config_templates = [
            ("development.yaml.j2", "development.yaml"),
            ("production.yaml.j2", "production.yaml"),
            ("test.yaml.j2", "test.yaml"),
            ("logging.yaml.j2", "logging.yaml"),
            ("cell_config.yaml.j2", "cell_config.yaml")
        ]
        
        # Generate configuration files
        for template_name, output_name in config_templates:
            output_path = config_dir / output_name
            
            if not output_path.exists():
                try:
                    # Create configuration file from template
                    self.template_renderer.render_to_file(
                        template_name,
                        {"qcc_root": str(self.qcc_root)},
                        output_path
                    )
                    logger.info(f"Generated configuration file: {output_path}")
                except Exception as e:
                    logger.warning(f"Failed to generate configuration file {output_name}: {e}")
    
    def _setup_local_services(self) -> None:
        """Set up local services for development."""
        # Create .env file if it doesn't exist
        env_path = self.qcc_root / ".env"
        
        if not env_path.exists():
            env_content = [
                "# QCC Development Environment Variables",
                f"QCC_ROOT={str(self.qcc_root)}",
                f"QCC_ASSEMBLER_PORT={self.config.get('local_assembler_port', 8080)}",
                f"QCC_PROVIDER_PORT={self.config.get('local_provider_port', 8081)}",
                f"QCC_DASHBOARD_PORT={self.config.get('dashboard_port', 8082)}",
                "QCC_DEV_MODE=true",
                "QCC_LOG_LEVEL=debug",
                "QCC_DATA_DIR=./data",
                f"QCC_CONFIG_DIR={str(self.qcc_root / 'config')}",
                ""
            ]
            
            with open(env_path, 'w') as f:
                f.write('\n'.join(env_content))
            
            logger.info(f"Created .env file: {env_path}")
    
    def start_dev_server(self) -> subprocess.Popen:
        """
        Start the development server.
        
        Returns:
            Subprocess object for the server process
        """
        logger.info("Starting QCC development server")
        
        try:
            # Check if server.py exists
            server_path = self.qcc_root / "server.py"
            if not server_path.exists():
                logger.error(f"Server script not found: {server_path}")
                return None
            
            # Start server process
            process = subprocess.Popen(
                [sys.executable, str(server_path), "--dev"],
                env={
                    **os.environ,
                    "QCC_DEV_MODE": "true",
                    "QCC_ROOT": str(self.qcc_root),
                    "QCC_CONFIG": str(self.qcc_root / "config" / "development.yaml")
                }
            )
            
            logger.info(f"Development server started (PID: {process.pid})")
            return process
            
        except Exception as e:
            logger.error(f"Failed to start development server: {e}", exc_info=True)
            return None
    
    def create_project(self, name: str, output_dir: Path = None) -> Path:
        """
        Create a new QCC project.
        
        Args:
            name: Name of the project
            output_dir: Directory to create the project in
            
        Returns:
            Path to the created project directory
        """
        # Sanitize project name
        project_name = re.sub(r'[^a-zA-Z0-9_-]', '-', name).lower()
        
        # Determine output directory
        if output_dir is None:
            output_dir = Path.cwd() / project_name
        else:
            output_dir = output_dir / project_name
        
        logger.info(f"Creating QCC project: {project_name} in {output_dir}")
        
        # Check if directory already exists
        if output_dir.exists():
            logger.warning(f"Project directory already exists: {output_dir}")
            response = input(f"Project '{project_name}' already exists. Overwrite? (y/n): ")
            if response.lower() != 'y':
                logger.info("Project creation cancelled")
                return output_dir
        
        # Create project directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create project structure
        self._create_project_structure(project_name, output_dir)
        
        logger.info(f"Project created: {project_name} in {output_dir}")
        return output_dir
    
    def _create_project_structure(self, project_name: str, project_dir: Path) -> None:
        """
        Create the structure for a new QCC project.
        
        Args:
            project_name: Name of the project
            project_dir: Directory to create the project in
        """
        # Create context for templates
        context = {
            "project_name": project_name,
            "project_title": project_name.replace('-', ' ').title(),
            "qcc_version": "0.1.0",  # TODO: Get actual version
            "creation_date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "year": datetime.datetime.now().year
        }
        
        # Create project files
        project_files = [
            ("project_readme.md.j2", "README.md"),
            ("project_config.yaml.j2", "config.yaml"),
            ("project_gitignore.j2", ".gitignore"),
            ("project_main.py.j2", "main.py")
        ]
        
        for template_name, output_name in project_files:
            self.template_renderer.render_to_file(
                template_name, context, project_dir / output_name
            )
        
        # Create directories
        directories = [
            "cells",
            "data",
            "config",
            "logs"
        ]
        
        for directory in directories:
            (project_dir / directory).mkdir(exist_ok=True)
        
        # Create sample cell
        sample_cell_dir = project_dir / "cells" / "sample"
        sample_cell_dir.mkdir(exist_ok=True)
        
        self.template_renderer.render_to_file(
            "sample_cell.py.j2", context, sample_cell_dir / "main.py"
        )
        self.template_renderer.render_to_file(
            "sample_cell_manifest.json.j2", context, sample_cell_dir / "manifest.json"
        )
        
        # Create virtual environment if requested
        response = input("Create virtual environment for the project? (y/n): ")
        if response.lower() == 'y':
            try:
                subprocess.run(
                    [sys.executable, "-m", "venv", str(project_dir / "venv")],
                    check=True
                )
                logger.info(f"Created virtual environment: {project_dir / 'venv'}")
                
                # Create requirements.txt
                with open(project_dir / "requirements.txt", 'w') as f:
                    f.write("# QCC Project Dependencies\n")
                    f.write("qcc==0.1.0\n")  # TODO: Use actual version
                
                # Print activation instructions
                if os.name == 'nt':  # Windows
                    print(f"To activate the virtual environment, run: {project_dir / 'venv' / 'Scripts' / 'activate'}")
                else:  # Unix/Linux/Mac
                    print(f"To activate the virtual environment, run: source {project_dir / 'venv' / 'bin' / 'activate'}")
                
            except Exception as e:
                logger.warning(f"Failed to create virtual environment: {e}")


class DevToolsRunner:
    """
    Command-line runner for QCC development tools.
    
    Attributes:
        parser: Argument parser for command-line arguments
    """
    
    def __init__(self):
        """Initialize the DevToolsRunner."""
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """
        Create the argument parser.
        
        Returns:
            Configured argument parser
        """
        parser = argparse.ArgumentParser(
            description="QCC Development Tools",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=textwrap.dedent("""
                Examples:
                  dev_tools.py init                   # Initialize development environment
                  dev_tools.py cell create text-editor # Create a new text editor cell
                  dev_tools.py project create my-app   # Create a new QCC project
                  dev_tools.py start                  # Start development server
            """)
        )
        
        # Add main commands
        subparsers = parser.add_subparsers(dest="command", help="Command to execute")
        
        # 'init' command
        init_parser = subparsers.add_parser("init", help="Initialize development environment")
        init_parser.add_argument("--config", help="Path to configuration file")
        
        # 'cell' command
        cell_parser = subparsers.add_parser("cell", help="Cell development commands")
        cell_subparsers = cell_parser.add_subparsers(dest="cell_command", help="Cell command")
        
        # 'cell create' command
        create_cell_parser = cell_subparsers.add_parser("create", help="Create a new cell")
        create_cell_parser.add_argument("name", help="Name of the cell")
        create_cell_parser.add_argument("--capability", "-c", help="Primary capability of the cell", default="custom")
        create_cell_parser.add_argument("--type", "-t", help="Type of cell", choices=["system", "middleware", "application"], default="application")
        create_cell_parser.add_argument("--description", "-d", help="Description of the cell")
        create_cell_parser.add_argument("--author", "-a", help="Author of the cell")
        create_cell_parser.add_argument("--version", "-v", help="Cell version", default="1.0.0")
        
        # 'cell build' command
        build_cell_parser = cell_subparsers.add_parser("build", help="Build a cell package")
        build_cell_parser.add_argument("name", help="Name of the cell")
        build_cell_parser.add_argument("--type", "-t", help="Type of cell", choices=["system", "middleware", "application"], default="application")
        build_cell_parser.add_argument("--output", "-o", help="Output directory")
        
        # 'cell test' command
        test_cell_parser = cell_subparsers.add_parser("test", help="Run cell tests")
        test_cell_parser.add_argument("name", help="Name of the cell")
        test_cell_parser.add_argument("--type", "-t", help="Type of cell", choices=["system", "middleware", "application"], default="application")
        
        # 'project' command
        project_parser = subparsers.add_parser("project", help="Project development commands")
        project_subparsers = project_parser.add_subparsers(dest="project_command", help="Project command")
        
        # 'project create' command
        create_project_parser = project_subparsers.add_parser("create", help="Create a new QCC project")
        create_project_parser.add_argument("name", help="Name of the project")
        create_project_parser.add_argument("--output", "-o", help="Output directory")
        
        # 'start' command
        start_parser = subparsers.add_parser("start", help="Start development server")
        start_parser.add_argument("--dashboard", "-d", action="store_true", help="Open dashboard in browser")
        
        # 'lint' command
        lint_parser = subparsers.add_parser("lint", help="Lint code")
        lint_parser.add_argument("path", nargs="?", help="Path to lint", default=".")
        
        # Global options
        parser.add_argument("--verbose", "-v", action="count", default=0, help="Increase verbosity")
        parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output")
        
        return parser
    
    def run(self) -> int:
        """
        Run the development tools with the specified arguments.
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        args = self.parser.parse_args()
        
        # Configure logging
        self._configure_logging(args.verbose, args.quiet)
        
        try:
            # Handle commands
            if args.command == "init":
                return self._handle_init(args)
            elif args.command == "cell":
                return self._handle_cell(args)
            elif args.command == "project":
                return self._handle_project(args)
            elif args.command == "start":
                return self._handle_start(args)
            elif args.command == "lint":
                return self._handle_lint(args)
            else:
                self.parser.print_help()
                return 0
                
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return 1
    
    def _configure_logging(self, verbosity: int, quiet: bool) -> None:
        """
        Configure logging based on verbosity level.
        
        Args:
            verbosity: Verbosity level (0-3)
            quiet: Whether to suppress output
        """
        if quiet:
            logging.basicConfig(level=logging.ERROR)
            return
        
        log_levels = {
            0: logging.WARNING,
            1: logging.INFO,
            2: logging.DEBUG,
            3: logging.NOTSET
        }
        
        level = log_levels.get(verbosity, logging.INFO)
        
        logging.basicConfig(
            level=level,
            format="%(levelname)s: %(message)s" if level > logging.INFO else "%(message)s"
        )
    
    def _handle_init(self, args) -> int:
        """
        Handle the 'init' command.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code
        """
        config_path = Path(args.config) if args.config else None
        
        dev_env = DevelopmentEnvironment(config_path)
        if dev_env.setup_dev_environment():
            print(f"{Fore.GREEN}Development environment initialized successfully{Style.RESET_ALL}")
            return 0
        else:
            print(f"{Fore.RED}Failed to initialize development environment{Style.RESET_ALL}")
            return 1
    
    def _handle_cell(self, args) -> int:
        """
        Handle the 'cell' command.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code
        """
        dev_env = DevelopmentEnvironment()
        
        if args.cell_command == "create":
            try:
                cell_dir = dev_env.cell_generator.create_cell(
                    name=args.name,
                    capability=args.capability,
                    cell_type=args.type,
                    description=args.description,
                    author=args.author,
                    version=args.version
                )
                
                print(f"{Fore.GREEN}Cell created: {cell_dir}{Style.RESET_ALL}")
                return 0
                
            except Exception as e:
                print(f"{Fore.RED}Failed to create cell: {e}{Style.RESET_ALL}")
                logger.error(f"Failed to create cell: {e}", exc_info=True)
                return 1
                
        elif args.cell_command == "build":
            try:
                cell_dir = dev_env.qcc_root / "src" / "cells" / args.type / args.name
                output_dir = Path(args.output) if args.output else None
                
                package_path = dev_env.cell_generator.create_cell_package(cell_dir, output_dir)
                
                if package_path:
                    print(f"{Fore.GREEN}Cell package created: {package_path}{Style.RESET_ALL}")
                    return 0
                else:
                    print(f"{Fore.RED}Failed to create cell package{Style.RESET_ALL}")
                    return 1
                    
            except Exception as e:
                print(f"{Fore.RED}Failed to build cell: {e}{Style.RESET_ALL}")
                logger.error(f"Failed to build cell: {e}", exc_info=True)
                return 1
                
        elif args.cell_command == "test":
            try:
                cell_dir = dev_env.qcc_root / "src" / "cells" / args.type / args.name
                
                if not cell_dir.exists():
                    print(f"{Fore.RED}Cell not found: {cell_dir}{Style.RESET_ALL}")
                    return 1
                
                test_dir = cell_dir / "tests"
                if not test_dir.exists() or not list(test_dir.glob("test_*.py")):
                    print(f"{Fore.YELLOW}No tests found for cell: {args.name}{Style.RESET_ALL}")
                    return 0
                
                print(f"Running tests for cell: {args.name}")
                
                # Run pytest
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", str(test_dir), "-v"],
                    capture_output=True,
                    text=True
                )
                
                # Print test output
                print(result.stdout)
                
                if result.returncode == 0:
                    print(f"{Fore.GREEN}All tests passed{Style.RESET_ALL}")
                    return 0
                else:
                    print(f"{Fore.RED}Some tests failed{Style.RESET_ALL}")
                    return 1
                    
            except Exception as e:
                print(f"{Fore.RED}Failed to run tests: {e}{Style.RESET_ALL}")
                logger.error(f"Failed to run tests: {e}", exc_info=True)
                return 1
                
        else:
            print("Please specify a cell command (create, build, test)")
            return 1
    
    def _handle_project(self, args) -> int:
        """
        Handle the 'project' command.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code
        """
        dev_env = DevelopmentEnvironment()
        
        if args.project_command == "create":
            try:
                output_dir = Path(args.output) if args.output else None
                
                project_dir = dev_env.create_project(args.name, output_dir)
                
                print(f"{Fore.GREEN}Project created: {project_dir}{Style.RESET_ALL}")
                return 0
                
            except Exception as e:
                print(f"{Fore.RED}Failed to create project: {e}{Style.RESET_ALL}")
                logger.error(f"Failed to create project: {e}", exc_info=True)
                return 1
                
        else:
            print("Please specify a project command (create)")
            return 1
    
    def _handle_start(self, args) -> int:
        """
        Handle the 'start' command.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code
        """
        dev_env = DevelopmentEnvironment()
        
        try:
            process = dev_env.start_dev_server()
            
            if process:
                # Print server information
                dashboard_port = dev_env.config.get("dashboard_port", 8082)
                assembler_port = dev_env.config.get("local_assembler_port", 8080)
                provider_port = dev_env.config.get("local_provider_port", 8081)
                
                print(f"{Fore.GREEN}Development server started (PID: {process.pid}){Style.RESET_ALL}")
                print(f"Dashboard: http://localhost:{dashboard_port}")
                print(f"Assembler API: http://localhost:{assembler_port}")
                print(f"Provider API: http://localhost:{provider_port}")
                
                # Open dashboard in browser if requested
                if args.dashboard:
                    import webbrowser
                    webbrowser.open(f"http://localhost:{dashboard_port}")
                
                print("Press Ctrl+C to stop the server")
                
                # Wait for server process
                try:
                    process.wait()
                except KeyboardInterrupt:
                    print("\nStopping server...")
                    process.terminate()
                    process.wait()
                    print(f"{Fore.GREEN}Server stopped{Style.RESET_ALL}")
                
                return 0
            else:
                print(f"{Fore.RED}Failed to start development server{Style.RESET_ALL}")
                return 1
                
        except Exception as e:
            print(f"{Fore.RED}Failed to start server: {e}{Style.RESET_ALL}")
            logger.error(f"Failed to start server: {e}", exc_info=True)
            return 1
    
    def _handle_lint(self, args) -> int:
        """
        Handle the 'lint' command.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Exit code
        """
        try:
            # Check if flake8 is installed
            try:
                import flake8
            except ImportError:
                print("flake8 is not installed. Installing...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "flake8"],
                    check=True
                )
            
            # Run flake8
            path = args.path
            print(f"Linting code in {path}")
            
            result = subprocess.run(
                [sys.executable, "-m", "flake8", path],
                capture_output=True,
                text=True
            )
            
            # Print lint output
            if result.stdout:
                print(result.stdout)
            
            if result.returncode == 0:
                print(f"{Fore.GREEN}No lint issues found{Style.RESET_ALL}")
                return 0
            else:
                print(f"{Fore.YELLOW}Lint issues found{Style.RESET_ALL}")
                return 1
                
        except Exception as e:
            print(f"{Fore.RED}Failed to lint code: {e}{Style.RESET_ALL}")
            logger.error(f"Failed to lint code: {e}", exc_info=True)
            return 1


class CodeGenerator:
    """
    Generates code for common QCC patterns.
    
    Attributes:
        template_renderer: Template renderer for code generation
    """
    
    def __init__(self, template_renderer: TemplateRenderer = None):
        """
        Initialize the code generator.
        
        Args:
            template_renderer: Template renderer for code generation
        """
        self.template_renderer = template_renderer or TemplateRenderer()
    
    def generate_cell_capability(
        self,
        capability_name: str,
        description: str = None,
        parameters: List[Dict[str, Any]] = None,
        outputs: List[Dict[str, Any]] = None
    ) -> str:
        """
        Generate code for a cell capability.
        
        Args:
            capability_name: Name of the capability
            description: Description of the capability
            parameters: List of parameter definitions
            outputs: List of output definitions
            
        Returns:
            Generated code
        """
        context = {
            "capability_name": capability_name,
            "description": description or f"Provides {capability_name} functionality",
            "parameters": parameters or [],
            "outputs": outputs or [{"name": "result", "type": "any"}]
        }
        
        return self.template_renderer.render_template("capability.py.j2", context)
    
    def generate_model(
        self,
        model_name: str,
        fields: List[Dict[str, Any]],
        description: str = None
    ) -> str:
        """
        Generate code for a data model.
        
        Args:
            model_name: Name of the model
            fields: List of field definitions
            description: Description of the model
            
        Returns:
            Generated code
        """
        context = {
            "model_name": model_name,
            "fields": fields,
            "description": description or f"{model_name} data model"
        }
        
        return self.template_renderer.render_template("model.py.j2", context)
    
    def generate_api_endpoint(
        self,
        endpoint_name: str,
        http_method: str,
        path: str,
        parameters: List[Dict[str, Any]] = None,
        responses: Dict[int, Dict[str, Any]] = None,
        description: str = None
    ) -> str:
        """
        Generate code for an API endpoint.
        
        Args:
            endpoint_name: Name of the endpoint
            http_method: HTTP method (GET, POST, etc.)
            path: Endpoint path
            parameters: List of parameter definitions
            responses: Dictionary of response definitions by status code
            description: Description of the endpoint
            
        Returns:
            Generated code
        """
        context = {
            "endpoint_name": endpoint_name,
            "http_method": http_method.upper(),
            "path": path,
            "parameters": parameters or [],
            "responses": responses or {200: {"description": "Success"}},
            "description": description or f"{endpoint_name} endpoint"
        }
        
        return self.template_renderer.render_template("api_endpoint.py.j2", context)


class DebugUtilities:
    """
    Utilities for debugging QCC applications.
    
    Attributes:
        qcc_root: Root directory of the QCC project
    """
    
    def __init__(self, qcc_root: Path = None):
        """
        Initialize the debug utilities.
        
        Args:
            qcc_root: Root directory of the QCC project
        """
        self.qcc_root = qcc_root or QCC_ROOT
    
    def dump_cell_state(self, cell_id: str, output_path: Path = None) -> Dict[str, Any]:
        """
        Dump the state of a cell for debugging.
        
        Args:
            cell_id: ID of the cell
            output_path: Path to save the state
            
        Returns:
            Cell state dictionary
        """
        # Find active cell
        cells_dir = self.qcc_root / "data" / "cell-cache"
        cell_path = cells_dir / f"{cell_id}.json"
        
        if not cell_path.exists():
            logger.error(f"Cell state not found: {cell_path}")
            return None
        
        try:
            # Load cell state
            with open(cell_path, 'r') as f:
                cell_state = json.load(f)
            
            # Save to output path if specified
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(cell_state, f, indent=2)
                logger.info(f"Cell state saved to {output_path}")
            
            return cell_state
            
        except Exception as e:
            logger.error(f"Failed to dump cell state: {e}")
            return None
    
    def dump_solution_state(self, solution_id: str, output_path: Path = None) -> Dict[str, Any]:
        """
        Dump the state of a solution for debugging.
        
        Args:
            solution_id: ID of the solution
            output_path: Path to save the state
            
        Returns:
            Solution state dictionary
        """
        # Find active solution
        solutions_dir = self.qcc_root / "data" / "solutions"
        solution_path = solutions_dir / f"{solution_id}.json"
        
        if not solution_path.exists():
            logger.error(f"Solution state not found: {solution_path}")
            return None
        
        try:
            # Load solution state
            with open(solution_path, 'r') as f:
                solution_state = json.load(f)
            
            # Save to output path if specified
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(solution_state, f, indent=2)
                logger.info(f"Solution state saved to {output_path}")
            
            return solution_state
            
        except Exception as e:
            logger.error(f"Failed to dump solution state: {e}")
            return None
    
    def analyze_logs(self, log_path: Path = None, output_path: Path = None) -> Dict[str, Any]:
        """
        Analyze logs for debugging.
        
        Args:
            log_path: Path to log file
            output_path: Path to save analysis results
            
        Returns:
            Analysis results
        """
        if log_path is None:
            log_path = self.qcc_root / "logs" / "qcc.log"
        
        if not log_path.exists():
            logger.error(f"Log file not found: {log_path}")
            return None
        
        try:
            # Define patterns to analyze
            patterns = {
                "errors": r"ERROR",
                "warnings": r"WARNING",
                "cell_creation": r"Created cell",
                "cell_activation": r"activated",
                "cell_termination": r"terminated",
                "assembler_requests": r"Assembling solution",
                "providers": r"provider"
            }
            
            results = {key: [] for key in patterns}
            counts = {key: 0 for key in patterns}
            
            # Process log file
            with open(log_path, 'r') as f:
                for line in f:
                    for pattern_name, pattern in patterns.items():
                        if re.search(pattern, line, re.IGNORECASE):
                            counts[pattern_name] += 1
                            # Store a sample of matching lines (max 10)
                            if len(results[pattern_name]) < 10:
                                results[pattern_name].append(line.strip())
            
            # Prepare analysis results
            analysis = {
                "counts": counts,
                "samples": results,
                "analyzed_at": datetime.datetime.now().isoformat(),
                "log_path": str(log_path)
            }
            
            # Save to output path if specified
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(analysis, f, indent=2)
                logger.info(f"Log analysis saved to {output_path}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze logs: {e}")
            return None
    
    def trace_cell_communication(self, solution_id: str, output_path: Path = None) -> List[Dict[str, Any]]:
        """
        Trace communication between cells in a solution.
        
        Args:
            solution_id: ID of the solution
            output_path: Path to save trace results
            
        Returns:
            List of communication events
        """
        # Find solution communication logs
        comm_log_path = self.qcc_root / "logs" / "cell_communication.log"
        
        if not comm_log_path.exists():
            logger.error(f"Communication log not found: {comm_log_path}")
            return None
        
        try:
            # Extract communication events for the solution
            events = []
            
            with open(comm_log_path, 'r') as f:
                for line in f:
                    if solution_id in line:
                        try:
                            # Parse log line for communication data
                            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
                            source_match = re.search(r'source=([a-f0-9-]+)', line)
                            target_match = re.search(r'target=([a-f0-9-]+)', line)
                            type_match = re.search(r'type=(\w+)', line)
                            
                            if timestamp_match and source_match and target_match and type_match:
                                events.append({
                                    "timestamp": timestamp_match.group(1),
                                    "source_cell": source_match.group(1),
                                    "target_cell": target_match.group(1),
                                    "message_type": type_match.group(1),
                                    "raw_log": line.strip()
                                })
                        except Exception as e:
                            logger.warning(f"Failed to parse communication log line: {e}")
            
            # Save to output path if specified
            if output_path and events:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w') as f:
                    json.dump(events, f, indent=2)
                logger.info(f"Communication trace saved to {output_path}")
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to trace cell communication: {e}")
            return None


# Import required for the DevToolsRunner
import textwrap

# Main entry point
if __name__ == "__main__":
    runner = DevToolsRunner()
    sys.exit(runner.run())
