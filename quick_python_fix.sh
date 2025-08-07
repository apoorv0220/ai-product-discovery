#!/bin/bash

# 🚀 Quick Python Environment Fix
# One-liner to fix PEP 668 externally-managed-environment issue

echo "🐍 Quick fix for Python externally-managed-environment..."

# Install required system packages
echo "📦 Installing Python system requirements..."
sudo apt update && sudo apt install -y python3-full python3-venv python3-pip python3-dev python3-distutils python3-setuptools build-essential

# Test virtual environment creation
echo "🧪 Testing virtual environment creation..."
rm -rf test_venv 2>/dev/null || true
python3 -m venv test_venv && source test_venv/bin/activate && python -m pip install --upgrade pip && pip install requests && deactivate && rm -rf test_venv

echo "✅ Python environment fixed!"
echo ""
echo "You can now run: ./deploy_docker_shared_server.sh"