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
            self._start_virtual_env_service("Image-generator-hub", command, self.image_gen_pid_file, log_file, image_gen_dir)
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
        # Set the config directory path to the correct location
        env_vars = {
            "SERVICE__CONFIG_DIR_PATH": str(self.needle_home / "configs" / "fast")
        }
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


@service_app.command("config")
def service_config(ctx: typer.Context):
    """Manage service configuration."""
    manager = EnvConfigManager(service_name="service")
    manager.handle()
