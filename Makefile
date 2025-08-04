# AI Product Discovery Suite - Makefile
# 
# @category    Infrastructure
# @author      AI Product Discovery Team
# @copyright   Copyright (c) 2024 DiscoverySuite (https://discoverysuite.ai)
# @license     https://opensource.org/licenses/MIT MIT License

.PHONY: help build up down restart logs clean test install-magento setup-env

# Default target
help:
	@echo "AI Product Discovery Suite - Available Commands:"
	@echo ""
	@echo "🚀 Main Commands:"
	@echo "  make setup        - Initial setup (copy env, build, run)"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make restart      - Restart all services"
	@echo "  make build        - Build all Docker images"
	@echo ""
	@echo "📊 Monitoring:"
	@echo "  make logs         - Show all service logs"
	@echo "  make logs-search  - Show search service logs"
	@echo "  make logs-db      - Show database logs"
	@echo "  make status       - Show service status"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-search  - Test search service"
	@echo "  make test-api     - Test all API endpoints"
	@echo ""
	@echo "🔧 Development:"
	@echo "  make shell-search - Access search service shell"
	@echo "  make shell-db     - Access database shell"
	@echo "  make clean        - Clean up containers and volumes"
	@echo "  make setup-env    - Setup environment files"
	@echo ""
	@echo "📦 Magento:"
	@echo "  make install-magento - Install Magento 2 module"
	@echo "  make sync-catalog    - Sync product catalog"
	@echo ""

# Setup and Configuration
setup-env:
	@echo "🔧 Setting up environment files..."
	@cp .env.example .env
	@echo "✅ Environment file created. Please edit .env with your settings."

setup: setup-env build up
	@echo "🚀 Running initial setup..."
	@sleep 10
	@make test-health
	@echo ""
	@echo "✅ Setup complete! Services available at:"
	@echo "   - Search Service: http://localhost:8001"
	@echo "   - Recommendation Service: http://localhost:8002"
	@echo "   - Analytics Service: http://localhost:8004"
	@echo "   - Database Admin: http://localhost:8090"
	@echo "   - Redis Commander: http://localhost:8091"
	@echo "   - RabbitMQ Management: http://localhost:15672"
	@echo ""

# Docker Operations
build:
	@echo "🔨 Building Docker images..."
	docker-compose build

up:
	@echo "🚀 Starting all services..."
	docker-compose up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 15

down:
	@echo "🛑 Stopping all services..."
	docker-compose down

restart: down up

# Logging and Monitoring
logs:
	@echo "📋 Showing logs for all services..."
	docker-compose logs -f

logs-search:
	@echo "📋 Showing search service logs..."
	docker-compose logs -f search-service

logs-recommendation:
	@echo "📋 Showing recommendation service logs..."
	docker-compose logs -f recommendation-service

logs-analytics:
	@echo "📋 Showing analytics service logs..."
	docker-compose logs -f analytics-service

logs-db:
	@echo "📋 Showing database logs..."
	docker-compose logs -f postgres

status:
	@echo "📊 Service Status:"
	@docker-compose ps

# Testing
test-health:
	@echo "🏥 Testing service health..."
	@curl -f http://localhost:8001/health || echo "❌ Search service not healthy"
	@curl -f http://localhost:8002/health || echo "❌ Recommendation service not healthy"
	@curl -f http://localhost:8004/health || echo "❌ Analytics service not healthy"
	@echo "✅ Health check complete"

test-search:
	@echo "🔍 Testing search functionality..."
	@curl -X GET "http://localhost:8001/search?q=test&store_id=1" \
		-H "Content-Type: application/json" || echo "❌ Search test failed"
	@echo "✅ Search test complete"

test-autocomplete:
	@echo "🔍 Testing autocomplete functionality..."
	@curl -X GET "http://localhost:8001/autocomplete?q=te&store_id=1" \
		-H "Content-Type: application/json" || echo "❌ Autocomplete test failed"
	@echo "✅ Autocomplete test complete"

test-api: test-health test-search test-autocomplete
	@echo "✅ All API tests complete"

test:
	@echo "🧪 Running comprehensive tests..."
	@make test-api
	@echo "🧪 Running Python tests..."
	@docker-compose exec search-service python -m pytest tests/ -v || echo "⚠️ Python tests failed"
	@echo "✅ All tests complete"

# Development Tools
shell-search:
	@echo "🐚 Accessing search service shell..."
	docker-compose exec search-service /bin/bash

shell-recommendation:
	@echo "🐚 Accessing recommendation service shell..."
	docker-compose exec recommendation-service /bin/bash

shell-db:
	@echo "🐚 Accessing database shell..."
	docker-compose exec postgres psql -U discovery -d discovery_suite

shell-redis:
	@echo "🐚 Accessing Redis shell..."
	docker-compose exec redis redis-cli

# Magento Integration
install-magento:
	@echo "📦 Installing Magento 2 module..."
	@if [ -d "/path/to/magento" ]; then \
		cp -r magento2-module/Vendor /path/to/magento/app/code/; \
		echo "✅ Module files copied"; \
	else \
		echo "❌ Magento directory not found. Please update the path in Makefile"; \
	fi

sync-catalog:
	@echo "🔄 Syncing product catalog..."
	@curl -X POST "http://localhost:8001/index/rebuild" \
		-H "Content-Type: application/json" \
		-d '{"store_id": 1}' || echo "❌ Catalog sync failed"
	@echo "✅ Catalog sync initiated"

# Data Management
import-sample-data:
	@echo "📥 Importing sample product data..."
	@docker-compose exec postgres psql -U discovery -d discovery_suite -f /docker-entrypoint-initdb.d/sample-data.sql
	@echo "✅ Sample data imported"

backup-db:
	@echo "💾 Creating database backup..."
	@docker-compose exec postgres pg_dump -U discovery discovery_suite > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backed up"

# Cleanup
clean:
	@echo "🧹 Cleaning up containers and volumes..."
	@docker-compose down -v
	@docker-compose rm -f
	@docker system prune -f
	@echo "✅ Cleanup complete"

clean-all: clean
	@echo "🧹 Deep cleaning (removing images)..."
	@docker-compose down --rmi all -v --remove-orphans
	@echo "✅ Deep cleanup complete"

# Monitoring and Metrics
metrics:
	@echo "📈 Service Metrics:"
	@echo "Database connections:"
	@docker-compose exec postgres psql -U discovery -d discovery_suite -c "SELECT count(*) FROM pg_stat_activity;"
	@echo "Redis memory usage:"
	@docker-compose exec redis redis-cli info memory | grep used_memory_human

# Development Utilities
format:
	@echo "🎨 Formatting Python code..."
	@docker-compose exec search-service black backend/ --line-length=100
	@docker-compose exec search-service isort backend/
	@echo "✅ Code formatted"

lint:
	@echo "🔍 Linting Python code..."
	@docker-compose exec search-service flake8 backend/ --max-line-length=100
	@echo "✅ Linting complete"

# Quick start for development
dev: setup-env
	@echo "🚀 Starting development environment..."
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
	@echo "✅ Development environment running"