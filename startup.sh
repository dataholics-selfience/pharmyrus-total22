#!/bin/bash
# PHARMYRUS V16.1 - STARTUP VERIFICATION
# Verifica se aplicação está funcionando antes de aceitar requests

echo "🔧 Pharmyrus V16.1 - Starting..."

# 1. Verificar porta
PORT=${PORT:-8000}
echo "📡 Port: $PORT"

# 2. Verificar Python
python3 --version || { echo "❌ Python not found"; exit 1; }

# 3. Verificar dependências
echo "📦 Checking dependencies..."
pip list | grep -E "(fastapi|uvicorn|httpx)" || { echo "❌ Missing dependencies"; exit 1; }

# 4. Testar importação
echo "🔧 Testing imports..."
python3 -c "
from key_pool_manager import KeyPoolManager
from lightweight_crawler import LightweightCrawler
from main import app
print('✅ All imports OK')
" || { echo "❌ Import failed"; exit 1; }

# 5. Iniciar servidor
echo "🚀 Starting server on 0.0.0.0:$PORT..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT --log-level info
