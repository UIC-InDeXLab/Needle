.PHONY: dev backend app install install-fast install-balanced install-accurate uninstall sidecar icons

# Development: run the backend from source (embedded SQLite + LanceDB, no Docker)
backend:
	@cd backend && . venv/bin/activate && uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Development: run the Tauri desktop app against the dev backend + Vite/CRA dev server
dev:
	@cd ui && npm run tauri:dev

# Build the backend sidecar binary (PyInstaller)
sidecar:
	@bash ui/src-tauri/scripts/build-sidecar.sh

# Generate desktop app icons from the logo
icons:
	@cd ui && npx tauri icon src/assets/images/logo.png

# Build the desktop app + native installers
app:
	@chmod +x scripts/build-app.sh
	@./scripts/build-app.sh

# Install Needle desktop app + CLI (Docker-free)
install:
	@chmod +x scripts/install.sh
	@./scripts/install.sh

install-fast:
	@chmod +x scripts/install.sh
	@./scripts/install.sh fast

install-balanced:
	@chmod +x scripts/install.sh
	@./scripts/install.sh balanced

install-accurate:
	@chmod +x scripts/install.sh
	@./scripts/install.sh accurate

# Uninstall Needle (add PURGE=1 to also remove ~/.needle data)
uninstall:
	@chmod +x scripts/uninstall.sh
	@./scripts/uninstall.sh $(if $(PURGE),--purge,)

