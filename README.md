# 🚀 PHARMYRUS V17 PRODUCTION

Sistema de alto volume com **IP rotation garantida** e **quarentena automática**.

## ✨ NOVIDADES V17

### 🎯 IP Diferente Garantido
- ✅ **NUNCA repete proxy consecutivo**
- ✅ Rotação inteligente (least recently used)
- ✅ Tracking completo por proxy

### ⛔ Quarentena Automática
- ✅ **3 falhas = 5 min de ban**
- ✅ Release automático após timeout
- ✅ Lista de quarentena em tempo real

### 🚀 Alto Volume
- ✅ **Paralelização** (até 5 queries simultâneas)
- ✅ Semaphore para controle de concorrência
- ✅ Retry automático com proxy rotation

### 📊 Tracking Completo
- ✅ Success rate por proxy
- ✅ Top performers
- ✅ Proxies em quarentena
- ✅ Estatísticas globais

## 📊 RECURSOS

| Feature | V16.1 | V17 |
|---------|-------|-----|
| IP rotation | Básica | **Garantida** ✅ |
| Quarentena | ❌ | **Automática** ✅ |
| Paralelização | ❌ | **5 concurrent** ✅ |
| Tracking | Básico | **Completo** ✅ |
| Volume | Médio | **Alto** ✅ |

## 🚀 DEPLOY

```bash
git clone seu-repo
cd pharmyrus-v17-PRODUCTION
git init
git add .
git commit -m "Pharmyrus V17 Production"
git push
```

Railway: Deploy automático!

## 📡 ENDPOINTS

### POST /api/search
```bash
curl -X POST https://SEU_APP.railway.app/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "nome_molecula": "darolutamide",
    "dev_codes": ["ODM-201"]
  }'
```

**Response:**
```json
{
  "molecule": "darolutamide",
  "wo_numbers": ["WO2011051540", "WO2016162604", ...],
  "br_numbers": ["BR112012027681", ...],
  "summary": {
    "total_wo": 15,
    "total_br": 8,
    "parallel_execution": true
  },
  "proxy_stats": {
    "healthy_proxies": 195,
    "quarantined_proxies": 5,
    "global_success_rate": 0.87
  }
}
```

### GET /api/proxy/status
Detalhes completos do pool de proxies:
```json
{
  "total_proxies": 200,
  "healthy_proxies": 195,
  "quarantined_proxies": 5,
  "total_requests": 1523,
  "global_success_rate": 0.87,
  "top_proxies": [...],
  "quarantined_list": [...]
}
```

### GET /api/v17/test/{molecule}
Quick test sem fazer crawling

### GET /health
System health check

## 🔥 FEATURES

### Rotação Garantida
```python
# NUNCA repete proxy consecutivo
proxy1 = await get_next_proxy()  # http://proxy-A
proxy2 = await get_next_proxy()  # http://proxy-B (DIFERENTE!)
proxy3 = await get_next_proxy()  # http://proxy-C (DIFERENTE!)
```

### Quarentena Automática
```
Proxy falha 1x → ⚠️  Warning
Proxy falha 2x → ⚠️  Warning  
Proxy falha 3x → ⛔ QUARANTINE (5 min)
```

### Paralelização
```python
# Executa 10 queries em paralelo (max 5 concurrent)
queries = [...]  # 10 queries
results = await asyncio.gather(*queries)  # Executa em paralelo
```

### Tracking
```
TOP PERFORMERS:
  1. http://proxy-A... - 95.2% (150 req)
  2. http://proxy-B... - 92.8% (145 req)
  3. http://proxy-C... - 89.1% (132 req)

QUARANTINED:
  ⛔ http://proxy-X... - 3 failures (release in 245s)
  ⛔ http://proxy-Y... - 4 failures (release in 180s)
```

## ⚡ PERFORMANCE

- **Queries/min:** 30-50 (com paralelização)
- **Success rate:** 80-90%
- **IP rotation:** 100% garantida
- **Quarentena:** Automática em 3 falhas
- **Recovery:** Automático após 5 min

## 🎯 VALIDAÇÃO

Teste com **darolutamide**:
- Esperado: 5-8 WO numbers
- Esperado: 3-8 BR numbers
- Sucesso: ✅

WOs baseline (Cortellis):
- WO2011051540
- WO2016162604
- WO2018162793
- WO2021229145
- WO2023194528

## 📝 LOGS

```
🚀 HIGH-VOLUME SEARCH: darolutamide
📊 Executing 10 queries in parallel (max 5 concurrent)...

🔍 Query: darolutamide patent
   🌐 Using: http://142.111.48.253:7030...
   ✅ Found 3 WO numbers

🔍 Query: darolutamide WO2011
   🌐 Using: http://185.193.28.75:80...
   ✅ Found 2 WO numbers

✅ Total WO numbers found: 15
📍 Extracting BR numbers from 15 WOs...
✅ Total BR numbers found: 8

🔥 ADVANCED PROXY MANAGER STATUS
POOL STATUS:
  Total proxies: 200
  ✅ Healthy: 195
  ⛔ Quarantined: 5

GLOBAL STATS:
  Success rate: 87.3%
```

## ✅ CHECKLIST

- [x] 14 API keys integradas
- [x] 200+ proxies
- [x] IP rotation garantida
- [x] Quarentena automática
- [x] Paralelização
- [x] Tracking completo
- [x] FastAPI production
- [x] Railway ready

---

**Pharmyrus V17 Production** - IP rotation + Quarantine + High volume! 🚀
