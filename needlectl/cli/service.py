# cli/service.py

import os
import shutil
import subprocess
import time
import typer
from pathlib import Path
from typing import Optional

import requests

from backend.api_client import BackendClient
from cli.utils import print_result


service_app = typer.Typer(help="Manage the local Needle backend (embedded, no Docker).")


class ServiceManager:
    """Manages the local Needle backend (embedded SQLite + LanceDB, no Docker).

    In the desktop build the app auto-starts the backend; these commands let CLI
    users launch/attach to it and check health.
    """

    API_URL = "http://127.0.0.1:8000"
    BACKEND_PROC_NAME = "needle-backend"

    def __init__(self, needle_home: str):
        self.needle_home = Path(needle_home)

    def _is_backend_healthy(self) -> bool:
        try:
            r = requests.get(f"{self.API_URL}/health", timeout=3)
            return r.ok and r.json().get("status") == "running"
        except requests.RequestException:
            return False

    def _find_app_launcher(self):
        candidates = [
            Path.home() / ".local" / "bin" / "Needle.AppImage",
            Path("/Applications/Needle.app/Contents/MacOS/Needle"),
        ]
        for c in candidates:
            if c.exists():
                return [str(c)]
        exe = shutil.which("needle") or shutil.which("Needle")
        return [exe] if exe else None

    def _backend_pids(self):
        try:
            out = subprocess.run(
                ["pgrep", "-f", self.BACKEND_PROC_NAME],
                capture_output=True, text=True
            )
            return [int(p) for p in out.stdout.split() if p.strip()]
        except Exception:
            return []

    def start_services(self):
        if self._is_backend_healthy():
            typer.echo(f"Needle backend is already running at {self.API_URL}")
            return
        launcher = self._find_app_launcher()
        if not launcher:
            typer.echo("Could not find the Needle desktop app.")
            typer.echo("Launch Needle from your applications menu, or install it first.")
            return
        typer.echo("Launching the Needle app...")
        subprocess.Popen(
            launcher, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        typer.echo("Waiting for the backend to become ready...")
        for _ in range(60):
            if self._is_backend_healthy():
                typer.echo(f"Backend is running at {self.API_URL}")
                return
            time.sleep(1)
        typer.echo("Backend did not become ready in time. Check the app window.")

    def stop_services(self):
        pids = self._backend_pids()
        if not pids:
            typer.echo("No running Needle backend found. If the app is open, quit it from its window.")
            return
        for pid in pids:
            try:
                os.kill(pid, 15)
            except OSError:
                pass
        time.sleep(2)
        for pid in self._backend_pids():
            try:
                os.kill(pid, 9)
            except OSError:
                pass
        typer.echo("Stopped the Needle backend.")

    def restart_services(self):
        self.stop_services()
        time.sleep(2)
        self.start_services()

    def get_status(self):
        healthy = self._is_backend_healthy()
        info = {"backend": {"running": healthy, "url": self.API_URL}}
        if healthy:
            try:
                version = requests.get(f"{self.API_URL}/version", timeout=3).json().get("version")
                info["backend"]["version"] = version
            except requests.RequestException:
                pass
        return info


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
def service_log_cmd(ctx: typer.Context, service: str = typer.Argument("backend", help="(kept for compatibility)")):
    """Show where backend logs can be found."""
    from utils import get_data_dir

    typer.echo("The Needle backend runs inside the desktop app; its logs stream to the app process.")
    typer.echo("If you started the backend from source (make backend), logs appear in that terminal.")
    typer.echo(f"Application data and logs: {get_data_dir()}")


@service_app.command("setup")
def service_setup(
    ctx: typer.Context,
    profile: Optional[str] = typer.Option(None, help="fast | balanced | accurate"),
    gpu: Optional[bool] = typer.Option(None, "--gpu/--no-gpu", help="Use the GPU when available."),
    wait: bool = typer.Option(True, help="Wait for the models to finish downloading."),
):
    """Run first-time setup.

    Until this completes the backend rejects indexing and search, which is why a
    fresh install would otherwise answer every command with "not ready yet".
    Running it here does the same thing as the app's welcome screen.
    """
    import time

    client = BackendClient(ctx.obj["api_url"])
    status = client.get_setup_status()

    if status.get("configured") and profile is None and gpu is None:
        typer.echo(f"Already set up (profile: {status.get('profile')}).")
        typer.echo("Pass --profile to change it; this re-indexes your library.")
        return

    options = client.get_setup_options()
    if profile is None:
        profile = options.get("default_profile", "fast")
    valid = [p["id"] for p in options.get("profiles", [])] or ["fast", "balanced", "accurate"]
    if profile not in valid:
        typer.echo(f"Unknown profile '{profile}'. Choose from: {', '.join(valid)}")
        raise typer.Exit(code=1)

    if gpu is None:
        gpu = bool(options.get("gpu_available"))

    client.configure_setup(profile, gpu)
    typer.echo(f"Setting up with the '{profile}' profile (GPU: {'on' if gpu else 'off'}).")
    if not wait:
        return

    last = None
    while True:
        state = client.get_setup_status()
        if state.get("ready") or state.get("state") == "error":
            break
        message = state.get("message")
        if message and message != last:
            typer.echo(message)
            last = message
        time.sleep(1)

    if state.get("state") == "error":
        typer.echo(f"Setup failed: {state.get('message')}")
        raise typer.Exit(code=1)
    typer.echo("Needle is ready.")


@service_app.command("info")
def service_info(ctx: typer.Context):
    """Show version, platform, library and storage details."""
    client = BackendClient(ctx.obj["api_url"])
    print_result(client.get_system_info(), ctx.obj["output"])


@service_app.command("gpu")
def service_gpu(ctx: typer.Context, state: str = typer.Argument(..., help="on | off")):
    """Turn hardware acceleration on or off."""
    if state not in ("on", "off"):
        typer.echo("Expected 'on' or 'off'.")
        raise typer.Exit(code=1)
    client = BackendClient(ctx.obj["api_url"])
    result = client.set_gpu(state == "on")
    typer.echo(f"GPU {'enabled' if result.get('use_gpu') else 'disabled'}; reloading models.")


@service_app.command("update")
def service_update(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", "-f", help="Force update even if already up to date"),
    component: Optional[str] = typer.Option(None, "--component", "-c", help="Update specific component: needlectl, backend, ui, or all")
):
    """Update Needle components to latest versions."""
    needle_home = ctx.obj.get("needle_home", ".")
    
    updater = UpdateManager(needle_home)
    updater.update(force=force, component=component)


@service_app.command("config")
def service_config(ctx: typer.Context):
    """Show where Needle's settings live."""
    from utils import get_data_dir

    typer.echo("Settings are managed by the app and stored alongside your data:")
    typer.echo(f"  {get_data_dir()}")
    typer.echo("")
    typer.echo("Generator settings:   needlectl generator list")
    typer.echo("Accuracy profile:     needlectl service setup --profile <name>")
    typer.echo("Hardware accel:       needlectl service gpu on|off")