# cli/ui.py

import os
import subprocess
import typer
from pathlib import Path
from typing import Optional

from cli.utils import print_result

ui_app = typer.Typer(help="Manage Needle UI (Web Interface).")


class UIManager:
    """Manages the Needle web UI."""
    
    def __init__(self, needle_home: str):
        self.needle_home = Path(needle_home)
        self.ui_dir = self.needle_home / "ui"
        self.build_dir = self.ui_dir / "build"
        self.ui_pid_file = self.needle_home / "logs" / "ui.pid"
        
    def _is_ui_running(self) -> bool:
        """Check if the UI server is running."""
        if not self.ui_pid_file.exists():
            return False
        
        try:
            with open(self.ui_pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process is still running
            os.kill(pid, 0)
            return True
        except (OSError, ValueError, FileNotFoundError):
            return False
    
    def _get_ui_pid(self) -> Optional[int]:
        """Get the PID of the UI server if it's running."""
        if not self._is_ui_running():
            return None
        
        try:
            with open(self.ui_pid_file, 'r') as f:
                return int(f.read().strip())
        except (OSError, ValueError, FileNotFoundError):
            return None
    
    def start_ui(self, port: int = 3000):
        """Start the UI server."""
        if self._is_ui_running():
            pid = self._get_ui_pid()
            typer.echo(f"UI is already running (PID: {pid})")
            typer.echo(f"🌐 Access the UI at: http://localhost:{port}")
            return True
        
        # Check if build directory exists
        if not self.build_dir.exists():
            typer.echo("❌ UI build directory not found. Please build the UI first:")
            typer.echo("   cd ui && npm install && npm run build")
            return False
        
        # Ensure logs directory exists
        self.ui_pid_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Start UI server using Python's built-in HTTP server
        log_file = self.needle_home / "logs" / "ui.log"
        
        # Use Python's built-in HTTP server to serve the static files
        command = [
            "python3", "-m", "http.server", str(port), "--directory", str(self.build_dir)
        ]
        
        # Start server in background
        with open(log_file, 'w') as log_f:
            process = subprocess.Popen(
                command,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                cwd=self.build_dir
            )
        
        # Save PID
        with open(self.ui_pid_file, 'w') as f:
            f.write(str(process.pid))
        
        typer.echo(f"✅ UI started (PID: {process.pid})")
        typer.echo(f"🌐 Access the UI at: http://localhost:{port}")
        typer.echo(f"📝 Logs: {log_file}")
        return True
    
    def stop_ui(self):
        """Stop the UI server."""
        if not self._is_ui_running():
            typer.echo("UI is not running")
            return True
        
        pid = self._get_ui_pid()
        if pid:
            try:
                os.kill(pid, 15)  # SIGTERM
                import time
                time.sleep(2)
                
                # Check if still running
                if self._is_ui_running():
                    os.kill(pid, 9)  # SIGKILL
                    time.sleep(1)
                
                typer.echo("✅ UI stopped")
            except OSError:
                typer.echo("❌ Error stopping UI")
                return False
            finally:
                # Remove PID file
                if self.ui_pid_file.exists():
                    self.ui_pid_file.unlink()
        
        return True
    
    def get_status(self):
        """Get UI status."""
        is_running = self._is_ui_running()
        pid = self._get_ui_pid() if is_running else None
        
        return {
            "running": is_running,
            "pid": pid,
            "build_exists": self.build_dir.exists(),
            "ui_directory": str(self.ui_dir),
            "build_directory": str(self.build_dir)
        }


@ui_app.command("start")
def ui_start(ctx: typer.Context, port: int = typer.Option(3000, "--port", "-p", help="Port to run the UI on")):
    """Start the Needle web UI."""
    needle_home = ctx.obj.get("needle_home", ".")
    manager = UIManager(needle_home)
    manager.start_ui(port)


@ui_app.command("stop")
def ui_stop(ctx: typer.Context):
    """Stop the Needle web UI."""
    needle_home = ctx.obj.get("needle_home", ".")
    manager = UIManager(needle_home)
    manager.stop_ui()


@ui_app.command("status")
def ui_status_cmd(ctx: typer.Context):
    """Show UI status."""
    needle_home = ctx.obj.get("needle_home", ".")
    manager = UIManager(needle_home)
    status = manager.get_status()
    print_result(status, ctx.obj["output"])


@ui_app.command("build")
def ui_build(ctx: typer.Context):
    """Build the UI for production."""
    needle_home = ctx.obj.get("needle_home", ".")
    ui_dir = Path(needle_home) / "ui"
    
    if not ui_dir.exists():
        typer.echo("❌ UI directory not found. Please run this from the Needle project root.")
        return
    
    typer.echo("🔨 Building UI for production...")
    
    # Check if node_modules exists
    node_modules = ui_dir / "node_modules"
    if not node_modules.exists():
        typer.echo("📦 Installing dependencies...")
        result = subprocess.run(["npm", "install"], cwd=ui_dir, capture_output=True, text=True)
        if result.returncode != 0:
            typer.echo(f"❌ Failed to install dependencies: {result.stderr}")
            return
    
    # Build the UI
    typer.echo("🏗️  Building React app...")
    result = subprocess.run(["npm", "run", "build"], cwd=ui_dir, capture_output=True, text=True)
    if result.returncode != 0:
        typer.echo(f"❌ Build failed: {result.stderr}")
        return
    
    typer.echo("✅ UI built successfully!")
    typer.echo(f"📁 Build directory: {ui_dir / 'build'}")
    typer.echo("🚀 You can now start the UI with: needlectl ui start")


@ui_app.command("log")
def ui_log_cmd(ctx: typer.Context):
    """Show UI logs."""
    needle_home = ctx.obj.get("needle_home", ".")
    log_file = Path(needle_home) / "logs" / "ui.log"
    
    if log_file.exists():
        typer.echo("📝 UI Logs:")
        with open(log_file, 'r') as f:
            typer.echo(f.read())
    else:
        typer.echo("📝 No UI logs found")
