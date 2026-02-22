# Makefile for CEDR Practice Environment
# Run from repo root (same directory as docker-compose.yml).

DOCKER_COMPOSE := docker-compose

.PHONY: help up down shell logs status restart clean colima-fix pull

# Default target when you just run 'make'
help:
	@echo "🚀 CEDR Tutorial - Available Commands:"
	@echo "  make up          - Start the CEDR container in the background"
	@echo "  make down        - Stop and remove the CEDR container"
	@echo "  make shell       - Open an interactive bash shell inside the container"
	@echo "  make logs        - Tail the container logs (useful for troubleshooting)"
	@echo "  make status      - Check if the container is running"
	@echo "  make restart     - Restart the container"
	@echo "  make clean       - Stop the container and wipe isolated volumes/networks"
	@echo "  make pull        - Pull the latest CEDR tutorial image"
	@echo "  make colima-fix  - Restart Colima to fix Mac volume/permission sync issues (optional, Colima/Mac only)"

up:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

shell:
	docker exec -it cedr_tutorial /bin/bash

logs:
	$(DOCKER_COMPOSE) logs -f

status:
	$(DOCKER_COMPOSE) ps

restart:
	$(DOCKER_COMPOSE) down && $(DOCKER_COMPOSE) up -d

clean:
	$(DOCKER_COMPOSE) down -v --remove-orphans

pull:
	$(DOCKER_COMPOSE) pull

# Optional: use if volume sync or permissions are wrong with Colima on Mac
colima-fix:
	colima stop
	colima start --edit
