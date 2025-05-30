COMPOSE_CPU := docker compose -f docker/docker-compose.cpu.yaml
COMPOSE_GPU := docker compose -f docker/docker-compose.gpu.yaml
COMPOSE_DEV := -f docker/docker-compose.dev.yaml

.PHONY: dev dev-cpu dev-gpu

dev-cpu:
	$(COMPOSE_CPU) up -d etcd minio standalone postgres image-generator-hub
	$(COMPOSE_CPU) $(COMPOSE_DEV) up

dev-gpu:
	$(COMPOSE_GPU) up -d etcd minio standalone postgres image-generator-hub
	$(COMPOSE_GPU) $(COMPOSE_DEV) up

dev: dev-cpu