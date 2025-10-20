# cli/service.py

import os
import subprocess
import time
import typer
from pathlib import Path
from typing import Optional

from cli.utils import print_result
from config.config_manager import EnvConfigManager
from docker.docker_compose_manager import DockerComposeManager

service_app = typer.Typer(help="Manage Needle services (Virtual Environment + Docker Infrastructure).")


class ServiceManager:
    """Manages both virtual environment services and Docker infrastructure services."""
    
    def __init__(self, needle_home: str):
        self.needle_home = Path(needle_home)
        self.backend_pid_file = self.needle_home / "logs" / "backend.pid"
        self.image_gen_pid_file = self.needle_home / "logs" / "image-generator-hub.pid"
        self.docker_manager = DockerComposeManager()
    
    def _load_environment_vars(self) -> dict:
        """Load environment variables from template or use defaults."""
        env_vars = {
            # Database Configuration
            "POSTGRES__USER": "myuser",
            "POSTGRES__PASSWORD": "mypassword", 
            "POSTGRES__DB": "mydb",
            "POSTGRES__HOST": "localhost",
            "POSTGRES__PORT": "5432",
            
            # Vector Database Configuration
            "MILVUS__HOST": "localhost",
            "MILVUS__PORT": "19530",
            
            # Service Configuration
            "SERVICE__USE_CUDA": "true",  # Will be detected at runtime
            "SERVICE__CONFIG_DIR_PATH": str(self.needle_home / "configs"),
            
            # Image Generator Configuration
            "GENERATOR__HOST": "localhost",
            "GENERATOR__PORT": "8010",
            
            # Directory Indexing Configuration
            "DIRECTORY__NUM_WATCHER_WORKERS": "4",
            "DIRECTORY__BATCH_SIZE": "50",
            "DIRECTORY__RECURSIVE_INDEXING": "true",
            "DIRECTORY__CONSISTENCY_CHECK_INTERVAL": "1800",
            
            # Query Configuration
            "QUERY__NUM_IMAGES_TO_RETRIEVE": "10",
            "QUERY__NUM_IMAGES_TO_GENERATE": "1",
            "QUERY__GENERATED_IMAGE_SIZE": "SMALL",
            "QUERY__NUM_ENGINES_TO_USE": "1",
            "QUERY__USE_FALLBACK": "true",
            "QUERY__INCLUDE_BASE_IMAGES_IN_PREVIEW": "false",
        }
        
        # Try to load from template if it exists
        env_template = self.needle_home / "scripts" / "env.template"
        if env_template.exists():
            try:
                with open(env_template, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            # Replace template variables
                            value = value.replace('{{HAS_GPU}}', 'true')
                            value = value.replace('{{NEEDLE_DIR}}', str(self.needle_home))
                            env_vars[key] = value
            except Exception as e:
                typer.echo(f"Warning: Could not load environment template: {e}")
        
        return env_vars


class UpdateManager:
    """Manages updates for Needle components."""
    
    def __init__(self, needle_home: str):
        self.needle_home = Path(needle_home)
        self.github_repo = "UIC-InDeXLab/Needle"
        
    def get_latest_release_info(self):
        """Get latest release information from GitHub API."""
        import requests
        try:
            response = requests.get(f"https://api.github.com/repos/{self.github_repo}/releases/latest")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            typer.echo(f"Error fetching release info: {e}")
            return None
    
    def get_current_needlectl_version(self):
        """Get current needlectl version."""
        try:
            from cli.version import VERSION
            return VERSION
        except:
            return "unknown"
    
    def get_current_backend_version(self):
        """Get current backend version from git."""
        try:
            import subprocess
            import os
            
            # Change to project root directory
            original_cwd = os.getcwd()
            os.chdir(self.needle_home)
            
            try:
                # Get the latest needlectl tag
                result = subprocess.run(
                    ["git", "tag", "-l", "needlectl/v*", "--sort=-v:refname"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                tags = result.stdout.strip().split('\n')
                
                if not tags or tags == ['']:
                    return "0.1.0"
                else:
                    latest_tag = tags[0]
                    return latest_tag.replace("needlectl/v", "")
            finally:
                os.chdir(original_cwd)
        except:
            return "unknown"
    
    def get_current_ui_version(self):
        """Get current UI version from package.json."""
        try:
            import json
            ui_package_json = self.needle_home / "ui" / "package.json"
            if ui_package_json.exists():
                with open(ui_package_json, 'r') as f:
                    package_data = json.load(f)
                    return package_data.get("version", "unknown")
            return "not found"
        except:
            return "unknown"
    
    def update_needlectl(self, latest_version: str, force: bool = False):
        """Update needlectl binary."""
        typer.echo("🔄 Updating needlectl binary...")
        
        current_version = self.get_current_needlectl_version()
        if not force and current_version == latest_version:
            typer.echo("✅ needlectl is already up to date")
            return True
        
        try:
            import requests
            import platform
            
            # Determine OS and architecture
            os_name = platform.system().lower()
            if os_name == "darwin":
                os_name = "macos"
            
            # Download the appropriate binary
            binary_name = f"needlectl-{os_name}"
            download_url = f"https://github.com/{self.github_repo}/releases/latest/download/{binary_name}"
            
            typer.echo(f"📥 Downloading {binary_name}...")
            response = requests.get(download_url)
            response.raise_for_status()
            
            # Backup current binary
            current_binary = Path("/usr/local/bin/needlectl")
            if current_binary.exists():
                backup_path = current_binary.with_suffix('.backup')
                current_binary.rename(backup_path)
                typer.echo(f"💾 Backed up current binary to {backup_path}")
            
            # Install new binary
            with open(current_binary, 'wb') as f:
                f.write(response.content)
            
            # Make executable
            current_binary.chmod(0o755)
            
            typer.echo(f"✅ needlectl updated to version {latest_version}")
            return True
            
        except Exception as e:
            typer.echo(f"❌ Failed to update needlectl: {e}")
            return False
    
    def update_backend(self, force: bool = False):
        """Update backend by pulling latest changes from git."""
        typer.echo("🔄 Updating backend...")
        
        try:
            import subprocess
            import os
            
            # Change to project root directory
            original_cwd = os.getcwd()
            os.chdir(self.needle_home)
            
            try:
                # Check if we're in a git repository
                subprocess.run(["git", "status"], check=True, capture_output=True)
                
                # Pull latest changes
                typer.echo("📥 Pulling latest changes from git...")
                result = subprocess.run(
                    ["git", "pull", "origin", "main"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    typer.echo("✅ Backend updated successfully")
                    return True
                else:
                    typer.echo(f"❌ Failed to update backend: {result.stderr}")
                    return False
                    
            finally:
                os.chdir(original_cwd)
                
        except Exception as e:
            typer.echo(f"❌ Failed to update backend: {e}")
            return False
    
    def update_ui(self, latest_version: str, force: bool = False):
        """Update UI by downloading latest artifacts."""
        typer.echo("🔄 Updating UI artifacts...")
        
        try:
            import requests
            import platform
            import tarfile
            
            # Determine OS
            os_name = platform.system().lower()
            if os_name == "darwin":
                os_name = "macos"
            
            # Download UI artifacts
            artifact_name = f"ui-build-{os_name}.tar.gz"
            download_url = f"https://github.com/{self.github_repo}/releases/latest/download/{artifact_name}"
            
            typer.echo(f"📥 Downloading {artifact_name}...")
            response = requests.get(download_url)
            response.raise_for_status()
            
            # Extract to UI directory
            ui_dir = self.needle_home / "ui"
            ui_dir.mkdir(exist_ok=True)
            
            # Save and extract
            temp_file = ui_dir / "temp_ui_build.tar.gz"
            with open(temp_file, 'wb') as f:
                f.write(response.content)
            
            # Extract build directory
            with tarfile.open(temp_file, 'r:gz') as tar:
                tar.extractall(ui_dir)
            
            # Clean up temp file
            temp_file.unlink()
            
            typer.echo("✅ UI artifacts updated successfully")
            return True
            
        except Exception as e:
            typer.echo(f"❌ Failed to update UI: {e}")
            return False
    
    def update(self, force: bool = False, component: Optional[str] = None):
        """Update Needle components."""
        typer.echo("🔍 Checking for updates...")
        
        # Get latest release info
        release_info = self.get_latest_release_info()
        if not release_info:
            typer.echo("❌ Failed to fetch release information")
            return
        
        latest_version = release_info["tag_name"].replace("needlectl/v", "")
        typer.echo(f"📋 Latest version available: {latest_version}")
        
        # Show current versions
        typer.echo(f"📊 Current versions:")
        typer.echo(f"  - needlectl: {self.get_current_needlectl_version()}")
        typer.echo(f"  - backend: {self.get_current_backend_version()}")
        typer.echo(f"  - UI: {self.get_current_ui_version()}")
        
        success = True
        
        if component is None or component == "all" or component == "needlectl":
            success &= self.update_needlectl(latest_version, force)
        
        if component is None or component == "all" or component == "backend":
            success &= self.update_backend(force)
        
        if component is None or component == "all" or component == "ui":
            success &= self.update_ui(latest_version, force)
        
        if success:
            typer.echo("🎉 Update completed successfully!")
            typer.echo("💡 You may need to restart services: needlectl service restart")
        else:
            typer.echo("⚠️  Some updates failed. Check the output above for details.")


    def _is_service_running(self, pid_file: Path) -> bool:
        """Check if a service is running based on PID file."""
        if not pid_file.exists():
            return False
        
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process is still running
            os.kill(pid, 0)
            return True
        except (OSError, ValueError, FileNotFoundError):
            return False
    
    def _get_service_pid(self, pid_file: Path) -> Optional[int]:
        """Get the PID of a service if it's running."""
        if not self._is_service_running(pid_file):
            return None
        
        try:
            with open(pid_file, 'r') as f:
                return int(f.read().strip())
        except (OSError, ValueError, FileNotFoundError):
            return None
    
    def _start_virtual_env_service(self, service_name: str, command: list, pid_file: Path, log_file: Path, working_dir: Path = None, env_vars: dict = None):
        """Start a virtual environment service."""
        if self._is_service_running(pid_file):
            typer.echo(f"{service_name} is already running (PID: {self._get_service_pid(pid_file)})")
            return True
        
        # Ensure logs directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Use provided working directory or default to needle_home
        cwd = working_dir if working_dir else self.needle_home
        
        # Prepare environment variables
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        # Start service in background
        with open(log_file, 'w') as log_f:
            process = subprocess.Popen(
                command,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                env=env
            )
        
        # Save PID
        with open(pid_file, 'w') as f:
            f.write(str(process.pid))
        
        typer.echo(f"{service_name} started (PID: {process.pid})")
        return True
    
    def _stop_virtual_env_service(self, service_name: str, pid_file: Path):
        """Stop a virtual environment service."""
        if not self._is_service_running(pid_file):
            typer.echo(f"{service_name} is not running")
            return True
        
        pid = self._get_service_pid(pid_file)
        if pid:
            try:
                os.kill(pid, 15)  # SIGTERM
                time.sleep(2)
                
                # Check if still running
                if self._is_service_running(pid_file):
                    os.kill(pid, 9)  # SIGKILL
                    time.sleep(1)
                
                typer.echo(f"{service_name} stopped")
            except OSError:
                typer.echo(f"Error stopping {service_name}")
                return False
            finally:
                # Remove PID file
                if pid_file.exists():
                    pid_file.unlink()
        
        return True
    
    def start_services(self):
        """Start all Needle services (infrastructure + virtual environment services)."""
        typer.echo("Starting Needle services...")
        
        # Start infrastructure services (Docker)
        typer.echo("Starting infrastructure services (PostgreSQL, Milvus, etc.)...")
        self.docker_manager.start_containers()
        
        # Wait for infrastructure services to be ready
        typer.echo("Waiting for infrastructure services to be ready...")
        time.sleep(15)
        
        # Start image generator hub
        image_gen_dir = self.needle_home / "ImageGeneratorsHub"
        if image_gen_dir.exists() and (image_gen_dir / ".venv").exists():
            typer.echo("Starting image-generator-hub...")
            python_path = image_gen_dir / ".venv" / "bin" / "python"
            command = [
                str(python_path), "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"
            ]
            log_file = self.needle_home / "logs" / "image-generator-hub.log"
            # Load environment variables for image generator
            env_vars = self._load_environment_vars()
            self._start_virtual_env_service("Image-generator-hub", command, self.image_gen_pid_file, log_file, image_gen_dir, env_vars)
        else:
            typer.echo("Warning: ImageGeneratorsHub not found or virtual environment not set up. Image generation will not be available.")
        
        # Start backend
        typer.echo("Starting Needle backend...")
        backend_dir = self.needle_home / "backend"
        python_path = backend_dir / "venv" / "bin" / "python"
        command = [
            str(python_path), "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"
        ]
        log_file = self.needle_home / "logs" / "backend.log"
        # Load environment variables
        env_vars = self._load_environment_vars()
        self._start_virtual_env_service("Backend", command, self.backend_pid_file, log_file, backend_dir, env_vars)
        
        typer.echo("All services started!")
        typer.echo("🌐 Access Points:")
        typer.echo("  - Backend API: http://localhost:8000")
        typer.echo("  - Image Generator: http://localhost:8010")
        typer.echo("  - API Documentation: http://localhost:8000/docs")
    
    def stop_services(self):
        """Stop all Needle services."""
        typer.echo("Stopping Needle services...")
        
        # Stop virtual environment services
        self._stop_virtual_env_service("Backend", self.backend_pid_file)
        self._stop_virtual_env_service("Image-generator-hub", self.image_gen_pid_file)
        
        # Stop infrastructure services
        typer.echo("Stopping infrastructure services...")
        self.docker_manager.stop_containers()
        
        typer.echo("All services stopped!")
    
    def restart_services(self):
        """Restart all Needle services."""
        typer.echo("Restarting Needle services...")
        self.stop_services()
        time.sleep(2)
        self.start_services()
    
    def get_status(self):
        """Get status of all services."""
        status = {
            "infrastructure": {},
            "virtual_env_services": {}
        }
        
        # Check infrastructure services
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    import json
                    container = json.loads(line)
                    containers.append({
                        "name": container.get("Names", ""),
                        "status": container.get("Status", ""),
                        "ports": container.get("Ports", "")
                    })
            
            status["infrastructure"]["containers"] = containers
        except subprocess.CalledProcessError:
            status["infrastructure"]["error"] = "Failed to get Docker container status"
        
        # Check virtual environment services
        backend_running = self._is_service_running(self.backend_pid_file)
        image_gen_running = self._is_service_running(self.image_gen_pid_file)
        
        status["virtual_env_services"] = {
            "backend": {
                "running": backend_running,
                "pid": self._get_service_pid(self.backend_pid_file) if backend_running else None
            },
            "image_generator_hub": {
                "running": image_gen_running,
                "pid": self._get_service_pid(self.image_gen_pid_file) if image_gen_running else None
            }
        }
        
        return status


@service_app.command("start")
def service_start(ctx: typer.Context):
    """Start all Needle services (infrastructure + virtual environment services)."""
    needle_home = ctx.obj.get("needle_home", ".")
    manager = ServiceManager(needle_home)
    manager.start_services()


@service_app.command("stop")
def service_stop(ctx: typer.Context):
    """Stop all Needle services."""
    needle_home = ctx.obj.get("needle_home", ".")
    manager = ServiceManager(needle_home)
    manager.stop_services()


@service_app.command("restart")
def service_restart(ctx: typer.Context):
    """Restart all Needle services."""
    needle_home = ctx.obj.get("needle_home", ".")
    manager = ServiceManager(needle_home)
    manager.restart_services()


@service_app.command("status")
def service_status_cmd(ctx: typer.Context):
    """Show status of all services."""
    needle_home = ctx.obj.get("needle_home", ".")
    manager = ServiceManager(needle_home)
    status = manager.get_status()
    print_result(status, ctx.obj["output"])


@service_app.command("log")
def service_log_cmd(ctx: typer.Context, service: str = typer.Argument("backend", help="Service to show logs for (backend, image-generator-hub, or infrastructure)")):
    """Show logs for a specific service."""
    needle_home = ctx.obj.get("needle_home", ".")
    manager = ServiceManager(needle_home)
    
    if service == "infrastructure":
        # Show Docker logs
        from docker.docker_compose_manager import DockerComposeManager
        docker_manager = DockerComposeManager()
        docker_manager.log_services("postgres")
        docker_manager.log_services("milvus-standalone")
    else:
        # Show virtual environment service logs
        from pathlib import Path
        log_file = Path(needle_home) / "logs" / f"{service}.log"
        
        if log_file.exists():
            typer.echo(f"Showing logs for {service}:")
            with open(log_file, 'r') as f:
                typer.echo(f.read())
        else:
            typer.echo(f"Log file not found: {log_file}")


@service_app.command("update")
def service_update(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", "-f", help="Force update even if already up to date"),
    component: Optional[str] = typer.Option(None, "--component", "-c", help="Update specific component: needlectl, backend, ui, or all")
):
    """Update Needle components to latest versions."""
    needle_home = ctx.obj.get("needle_home", ".")
    manager = ServiceManager(needle_home)
    
    updater = UpdateManager(needle_home)
    updater.update(force=force, component=component)


@service_app.command("config")
def service_config(ctx: typer.Context):
    """Manage service configuration."""
    manager = EnvConfigManager(service_name="service")
    manager.handle()
