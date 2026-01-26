COMPOSE_INFRA := docker compose -f docker/docker-compose.infrastructure.yaml

.PHONY: dev install uninstall start stop status

# Development mode - starts infrastructure services and backend in dev mode
dev:
	$(COMPOSE_INFRA) up -d
	@echo "Waiting for infrastructure services to be ready..."
	@sleep 15
	@echo "Starting backend in development mode..."
	@cd backend && source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Install Needle (for development - use one-liner for production)
install:
	@chmod +x scripts/install.sh
	@./scripts/install.sh

# Install with specific configuration
install-fast:
	@chmod +x scripts/install.sh
	@./scripts/install.sh fast

install-balanced:
	@chmod +x scripts/install.sh
	@./scripts/install.sh balanced

install-accurate:
	@chmod +x scripts/install.sh
	@./scripts/install.sh accurate

# Uninstall Needle (only removes ~/.needle installation)
uninstall:
	@chmod +x scripts/uninstall.sh
	@./scripts/uninstall.sh

# Start all services using needlectl
start:
	@needlectl service start

# Stop all services using needlectl
stop:
	@needlectl service stop

# Check service status using needlectl
status:
	@needlectl service status
