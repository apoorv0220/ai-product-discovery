# Magento Server Commands

## Installation & Setup
```bash
# 1. Install dependencies
chmod +x install_dependencies.sh
./install_dependencies.sh

# 2. Setup module
chmod +x setup_complete_magento_module.sh
./setup_complete_magento_module.sh

# 3. Enable module (if not auto-enabled)
php bin/magento module:enable Vendor_DiscoverySuite
php bin/magento setup:upgrade
php bin/magento setup:di:compile
php bin/magento cache:flush
```

## Configuration
```bash
# Set API base URL
php bin/magento config:set discovery_suite_config/general/enabled 1
php bin/magento config:set discovery_suite_config/general/api_base_url "http://ai-product-discovery.softdemonew.info"

# Enable search features
php bin/magento config:set discovery_suite_config/search/enabled 1
php bin/magento config:set discovery_suite_config/search/nlp_enabled 1
php bin/magento config:set discovery_suite_config/search/typo_tolerance 1

# Enable recommendations
php bin/magento config:set discovery_suite_config/recommendations/enabled 1
php bin/magento config:set discovery_suite_config/recommendations/ml_powered 1

# Enable analytics
php bin/magento config:set discovery_suite_config/analytics/enabled 1
php bin/magento config:set discovery_suite_config/analytics/real_time_tracking 1
```

## Testing
```bash
# Test all features
chmod +x comprehensive_test.sh
./comprehensive_test.sh

# Test advanced AI features
php bin/magento discovery:test:advanced-ai

# Test connectivity
php bin/magento discovery:test:connection

# Sync catalog (when services are running)
php bin/magento discovery:sync:catalog
```

## Troubleshooting
```bash
# Clear all caches
php bin/magento cache:flush

# Regenerate DI
rm -rf generated/*
php bin/magento setup:di:compile

# Check module status
php bin/magento module:status Vendor_DiscoverySuite

# Check configuration
php bin/magento config:show discovery_suite_config

# View logs
tail -f var/log/system.log
tail -f var/log/exception.log
```

## Service Management (AI Server)
```bash
# Start AI services
chmod +x start_ai_services.sh
./start_ai_services.sh

# Check service status
curl http://ai-product-discovery.softdemonew.info:7001/health
curl http://ai-product-discovery.softdemonew.info:7002/health
```

## Autocomplete Endpoint
```
GET /discoverysuite/search/autocompleteadvanced?q=hero&limit=10
```

## Production Deployment
```bash
# Full deployment
./deploy_advanced_ai_sync.sh

# Set production mode
php bin/magento deploy:mode:set production
php bin/magento setup:static-content:deploy
```
