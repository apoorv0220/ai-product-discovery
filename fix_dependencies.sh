#!/bin/bash

# 🔧 Quick Dependency Fix for AI Product Discovery Suite
# Resolves weaviate-client and httpx version conflicts

echo "🔧 Fixing dependency conflicts..."

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

echo "Installing compatible versions..."

# Fix the conflicting dependencies first
pip install "httpx==0.27.0"
pip install "weaviate-client==4.8.1"

echo "Installing remaining dependencies..."

# Now install the rest
pip install -r backend/requirements-base.txt
pip install -r backend/requirements.txt

echo "Installing production dependencies..."
pip install gunicorn supervisor

echo "✅ Dependencies fixed!"
echo ""
echo "The issue was:"
echo "- weaviate-client 4.9.5 requires httpx<=0.27.0"
echo "- But requirements.txt had httpx==0.28.1"
echo ""
echo "Fixed by using:"
echo "- httpx==0.27.0 (compatible with weaviate-client)"
echo "- weaviate-client==4.8.1 (stable version)"
echo ""
echo "You can now continue with deployment!"