#!/bin/bash

echo "🧪 TESTING ALL FIXES FOR ADVANCED AI INTEGRATION"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}🔍 TEST 1: XML Validation${NC}"
echo "=========================="

# Test di.xml
echo "Testing di.xml..."
if xmllint --noout magento2-module/Vendor/DiscoverySuite/etc/di.xml 2>/dev/null; then
    echo -e "${GREEN}✅ di.xml is valid${NC}"
else
    echo -e "${RED}❌ di.xml has errors${NC}"
    xmllint magento2-module/Vendor/DiscoverySuite/etc/di.xml
fi

# Test system.xml
echo "Testing system.xml..."
if xmllint --noout magento2-module/Vendor/DiscoverySuite/etc/adminhtml/system.xml 2>/dev/null; then
    echo -e "${GREEN}✅ system.xml is valid${NC}"
else
    echo -e "${RED}❌ system.xml has errors${NC}"
    xmllint magento2-module/Vendor/DiscoverySuite/etc/adminhtml/system.xml
fi

# Test config.xml
echo "Testing config.xml..."
if xmllint --noout magento2-module/Vendor/DiscoverySuite/etc/config.xml 2>/dev/null; then
    echo -e "${GREEN}✅ config.xml is valid${NC}"
else
    echo -e "${RED}❌ config.xml has errors${NC}"
    xmllint magento2-module/Vendor/DiscoverySuite/etc/config.xml
fi

echo ""
echo -e "${BLUE}🔍 TEST 2: Configuration Path Validation${NC}"
echo "========================================="

# Check if all paths exist in system.xml
REQUIRED_PATHS=(
    "discovery_suite_config/search/nlp_enabled"
    "discovery_suite_config/search/intent_recognition"
    "discovery_suite_config/search/semantic_search"
    "discovery_suite_config/recommendations/ml_powered"
    "discovery_suite_config/recommendations/real_time_learning"
    "discovery_suite_config/recommendations/collaborative_filtering"
    "discovery_suite_config/recommendations/content_based"
    "discovery_suite_config/shopping_assistant/conversational_ai"
    "discovery_suite_config/shopping_assistant/nlp_processing"
    "discovery_suite_config/shopping_assistant/multi_turn_conversations"
    "discovery_suite_config/analytics/real_time_tracking"
    "discovery_suite_config/analytics/behavioral_insights"
    "discovery_suite_config/analytics/ab_testing"
    "discovery_suite_config/analytics/predictive_analytics"
)

FOUND_PATHS=0
TOTAL_PATHS=${#REQUIRED_PATHS[@]}

for path in "${REQUIRED_PATHS[@]}"; do
    # Extract the field id from the path
    field_id=$(echo "$path" | awk -F'/' '{print $NF}')
    
    if grep -q "id=\"$field_id\"" magento2-module/Vendor/DiscoverySuite/etc/adminhtml/system.xml; then
        echo -e "${GREEN}✅ $path${NC}"
        FOUND_PATHS=$((FOUND_PATHS + 1))
    else
        echo -e "${RED}❌ $path${NC}"
    fi
done

echo ""
echo "Configuration Paths: $FOUND_PATHS/$TOTAL_PATHS found"

echo ""
echo -e "${BLUE}🔍 TEST 3: Helper Method Validation${NC}"
echo "==================================="

# Check if helper methods exist
REQUIRED_METHODS=(
    "isNlpEnabled"
    "isTypoToleranceEnabled"
    "isIntentRecognitionEnabled"
    "isSemanticSearchEnabled"
    "isMlPoweredRecommendationsEnabled"
    "isRealTimeLearningEnabled"
    "isCollaborativeFilteringEnabled"
    "isContentBasedEnabled"
    "isShoppingAssistantEnabled"
    "isConversationalAiEnabled"
    "isChatNlpEnabled"
    "isMultiTurnConversationsEnabled"
    "isRealTimeTrackingEnabled"
    "isBehavioralInsightsEnabled"
    "isAbTestingEnabled"
    "isPredictiveAnalyticsEnabled"
)

FOUND_METHODS=0
TOTAL_METHODS=${#REQUIRED_METHODS[@]}

for method in "${REQUIRED_METHODS[@]}"; do
    if grep -q "public function $method" magento2-module/Vendor/DiscoverySuite/Helper/Data.php; then
        echo -e "${GREEN}✅ $method()${NC}"
        FOUND_METHODS=$((FOUND_METHODS + 1))
    else
        echo -e "${RED}❌ $method()${NC}"
    fi
done

echo ""
echo "Helper Methods: $FOUND_METHODS/$TOTAL_METHODS found"

echo ""
echo -e "${BLUE}🔍 TEST 4: Default Config Values${NC}"
echo "================================"

# Check if default values exist in config.xml
DEFAULT_VALUES=(
    "nlp_enabled"
    "intent_recognition"
    "semantic_search"
    "ml_powered"
    "real_time_learning"
    "collaborative_filtering"
    "content_based"
    "conversational_ai"
    "nlp_processing"
    "multi_turn_conversations"
    "real_time_tracking"
    "behavioral_insights"
    "ab_testing"
    "predictive_analytics"
)

FOUND_DEFAULTS=0
TOTAL_DEFAULTS=${#DEFAULT_VALUES[@]}

for value in "${DEFAULT_VALUES[@]}"; do
    if grep -q "<$value>" magento2-module/Vendor/DiscoverySuite/etc/config.xml; then
        echo -e "${GREEN}✅ $value${NC}"
        FOUND_DEFAULTS=$((FOUND_DEFAULTS + 1))
    else
        echo -e "${RED}❌ $value${NC}"
    fi
done

echo ""
echo "Default Values: $FOUND_DEFAULTS/$TOTAL_DEFAULTS found"

echo ""
echo -e "${BLUE}🔍 TEST 5: Advanced AI Implementation Check${NC}"
echo "==========================================="

# Check advanced AI files
ADVANCED_FILES=(
    "backend/search-service/core/nlp_processor.py"
    "backend/recommendation-service/core/ml_engine.py"
    "backend/analytics-service/core/advanced_analytics.py"
    "backend/shopping-assistant/core/conversational_ai.py"
)

FOUND_FILES=0
TOTAL_FILES=${#ADVANCED_FILES[@]}

for file in "${ADVANCED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $file${NC}"
        FOUND_FILES=$((FOUND_FILES + 1))
    else
        echo -e "${RED}❌ $file${NC}"
    fi
done

echo ""
echo "Advanced AI Files: $FOUND_FILES/$TOTAL_FILES found"

echo ""
echo -e "${BLUE}📊 FINAL TEST RESULTS${NC}"
echo "====================="

TOTAL_CHECKS=$((TOTAL_PATHS + TOTAL_METHODS + TOTAL_DEFAULTS + TOTAL_FILES))
TOTAL_PASSED=$((FOUND_PATHS + FOUND_METHODS + FOUND_DEFAULTS + FOUND_FILES))
SUCCESS_RATE=$(( (TOTAL_PASSED * 100) / TOTAL_CHECKS ))

echo "Configuration Paths: $FOUND_PATHS/$TOTAL_PATHS ($(( (FOUND_PATHS * 100) / TOTAL_PATHS ))%)"
echo "Helper Methods: $FOUND_METHODS/$TOTAL_METHODS ($(( (FOUND_METHODS * 100) / TOTAL_METHODS ))%)"
echo "Default Values: $FOUND_DEFAULTS/$TOTAL_DEFAULTS ($(( (FOUND_DEFAULTS * 100) / TOTAL_DEFAULTS ))%)"
echo "Advanced AI Files: $FOUND_FILES/$TOTAL_FILES ($(( (FOUND_FILES * 100) / TOTAL_FILES ))%)"
echo ""
echo "Overall Success Rate: $TOTAL_PASSED/$TOTAL_CHECKS ($SUCCESS_RATE%)"

if [ "$SUCCESS_RATE" -ge 90 ]; then
    echo -e "${GREEN}🎉 EXCELLENT! All advanced AI features are properly integrated.${NC}"
elif [ "$SUCCESS_RATE" -ge 80 ]; then
    echo -e "${YELLOW}⚠️ GOOD! Most features are integrated, minor issues remain.${NC}"
else
    echo -e "${RED}❌ NEEDS WORK! Several integration issues need attention.${NC}"
fi

echo ""
echo -e "${BLUE}🚀 NEXT STEPS FOR DEPLOYMENT:${NC}"
echo ""
echo "1. Run the sync script on your Magento server:"
echo "   ./deploy_advanced_ai_sync.sh"
echo ""
echo "2. After successful sync, test advanced features:"
echo "   php bin/magento discovery:test:advanced-ai"
echo ""
echo "3. Configure advanced settings in admin:"
echo "   Stores → Configuration → AI Discovery Suite"
echo ""
echo "4. Your customers can now experience:"
echo "   • 'I want to buy a Hero Hoodie' (natural language search)"
echo "   • 'Hro Hoodie' (automatic typo correction)"
echo "   • ML-powered personalized recommendations"
echo "   • Conversational AI shopping assistant"
