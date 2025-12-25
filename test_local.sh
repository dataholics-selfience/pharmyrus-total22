#!/bin/bash
# Test V17 locally before Railway deploy

echo "🔧 TESTING V17 LOCALLY"
echo "====================="

# Check Python
python3 --version || { echo "❌ Python not found"; exit 1; }

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -q -r requirements.txt || { echo "❌ Install failed"; exit 1; }

# Test imports
echo "🔧 Testing imports..."
python3 -c "
from key_pool_manager import KeyPoolManager
from advanced_proxy_manager import AdvancedProxyManager
from high_volume_crawler import HighVolumeCrawler
from main import app
print('✅ All imports OK')
" || { echo "❌ Import failed"; exit 1; }

# Test proxy manager
echo "🔧 Testing proxy manager..."
python3 advanced_proxy_manager.py || { echo "❌ Proxy manager test failed"; exit 1; }

echo ""
echo "✅ ALL TESTS PASSED!"
echo "Ready to deploy to Railway!"
echo ""
echo "Next steps:"
echo "  1. git add ."
echo "  2. git commit -m 'V17 with PORT fix'"
echo "  3. git push"
