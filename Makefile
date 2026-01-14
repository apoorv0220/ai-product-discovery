# AI Product Discovery Suite - Development and Deployment Makefile
.PHONY: help dev-infra prod-up stop clean logs status build-base dev-setup

# Default target
help:
	@echo "AI Product Discovery Suite - Development and Deployment"
	@echo ""
	@echo "Available targets:"
	@echo "  build-base   Build the base Docker image"
	@echo "  dev-infra    Start development infrastructure only"
	@echo "  dev-setup    Set up local development environment"
	@echo "  prod-up      Start production environment (infra + apps)"
	@echo "  stop         Stop all running containers"
	@echo "  clean        Remove all containers, volumes, and networks"
	@echo "  logs         Show logs from all running containers"
	@echo "  status       Show status of all containers"
	@echo "  help         Show this help message"

# Build base Docker image
build-base:
	@echo "🔨 Building base image..."
	@docker build -f backend/Dockerfile.base -t discovery-base:latest backend/
	@echo "✅ Base image built"

# Development Infrastructure Only
dev-infra:
	@echo "🚀 Starting development infrastructure..."
	@cp .env.dev .env
	@./scripts/validate-env.sh
	@docker-compose up -d postgres redis elasticsearch qdrant celery-worker celery-beat flower
	@echo "✅ Development infrastructure started"
	@echo "🌐 Services available at:"
	@echo "  - PostgreSQL: localhost:7010"
	@echo "  - Redis: localhost:7011"
	@echo "  - Elasticsearch: localhost:7020"
	@echo "  - Qdrant: localhost:7021"
	@echo "  - Flower: localhost:5555"
	@echo ""
	@echo "💡 Next steps:"
	@echo "  1. Run application services locally:"
	@echo "     cd backend/search-service && python main.py"
	@echo "     cd backend/recommendation-service && python main.py"
	@echo "     cd backend/analytics-service && python main.py"
	@echo "     cd backend/shopping-assistant && python main.py"
	@echo "  2. Or run 'make prod-up' for full containerized environment"

# Production Full Environment
prod-up: build-base
	@echo "🏭 Starting production environment..."
	@cp .env.prod .env
	@docker-compose up -d
	@sleep 10
	@docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Production environment started"
	@echo "🌐 Services available at:"
	@echo "  - Search Service: localhost:7001"
	@echo "  - Recommendation Service: localhost:7002"
	@echo "  - Analytics Service: localhost:7004"
	@echo "  - Shopping Assistant: localhost:7005"
	@echo "  - Flower: localhost:5555"
	@echo "  - Nginx: localhost:7008"

# Development Setup (Local Environment)
dev-setup:
	@echo "🔧 Setting up local development environment..."
	@if [ ! -d "venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@echo "Installing dependencies..."
	@. venv/bin/activate && pip install --upgrade pip && \
		pip install -r backend/requirements.txt && \
		pip install -e backend/shared
	@echo "✅ Development environment setup complete"
	@echo "💡 Activate virtual environment: source venv/bin/activate"

# Stop all containers
stop:
	@echo "🛑 Stopping all containers..."
	@docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
	@docker-compose down
	@echo "✅ All containers stopped"

# Clean everything
clean: stop
	@echo "🧹 Cleaning up containers, volumes, and networks..."
	@docker-compose -f docker-compose.prod.yml down -v --remove-orphans 2>/dev/null || true
	@docker-compose down -v --remove-orphans
	@docker network rm ai_discovery_network 2>/dev/null || true
	@echo "✅ Cleanup complete"

# Show logs
logs:
	@docker-compose logs -f --tail=100

# Show status
status:
	@echo "📊 Container Status:"
	@docker-compose ps
	@echo ""
	@echo "📊 Production Services:"
	@docker-compose -f docker-compose.prod.yml ps 2>/dev/null || echo "No production services running"

# Development shortcuts
dev-logs:
	@docker-compose logs -f --tail=50

dev-shell-postgres:
	@docker-compose exec postgres psql -U ai_user -d ai_discovery

dev-shell-redis:
	@docker-compose exec redis redis-cli -a "${REDIS_PASSWORD}"

dev-restart:
	@docker-compose restart

# Production shortcuts
prod-logs:
	@docker-compose -f docker-compose.prod.yml logs -f --tail=50

prod-restart:
	@docker-compose -f docker-compose.prod.yml restart

# Health checks
health-check:
	@echo "🔍 Checking infrastructure health..."
	@docker-compose ps
	@echo ""
	@echo "🔍 Checking service health..."
	@-curl -s http://localhost:7010/ > /dev/null && echo "✅ PostgreSQL: OK" || echo "❌ PostgreSQL: FAIL"
	@-docker-compose exec -T redis redis-cli -a "${REDIS_PASSWORD}" ping > /dev/null && echo "✅ Redis: OK" || echo "❌ Redis: FAIL"
	@-curl -s http://localhost:7020/_cluster/health > /dev/null && echo "✅ Elasticsearch: OK" || echo "❌ Elasticsearch: FAIL"
	@-curl -s http://localhost:7021/health > /dev/null && echo "✅ Qdrant: OK" || echo "❌ Qdrant: FAIL"