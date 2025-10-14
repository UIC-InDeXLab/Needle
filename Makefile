COMPOSE_INFRA := docker compose -f docker/docker-compose.infrastructure.yaml

.PHONY: dev install uninstall start stop status

# Development mode - starts infrastructure services and backend in dev mode
dev:
	$(COMPOSE_INFRA) up -d
	@echo "Waiting for infrastructure services to be ready..."
	@sleep 15
	@echo "Starting backend in development mode..."
	@cd backend && source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Install Needle (unified setup)
install:
	@chmod +x install.sh
	@./install.sh

# Install with specific configuration
install-fast:
	@chmod +x install.sh
	@./install.sh fast

install-balanced:
	@chmod +x install.sh
	@./install.sh balanced

install-accurate:
	@chmod +x install.sh
	@./install.sh accurate

# Uninstall Needle
uninstall:
	@chmod +x uninstall.sh
	@./uninstall.sh

# Start all services
start:
	@chmod +x start-needle.sh
	@./start-needle.sh

# Stop all services
stop:
	@chmod +x stop-needle.sh
	@./stop-needle.sh

# Check service status
status:
	@chmod +x status-needle.sh
	@./status-needle.sh