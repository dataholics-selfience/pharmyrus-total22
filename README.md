# Pharmyrus V14 - WO Discovery Robusto

## 🎯 FOCO: ACHAR WOs IGUAL CORTELLIS

### Objetivo Step 1:
- ✅ Descobrir WO numbers (igual Cortellis)
- ⏳ BR patents (próximo step)
- ⏳ INPI validation (step final)

### Target Darolutamide:
- **Expected:** 7 WOs
- **Sources:** Google Patents (SerpAPI)
- **Match target:** ≥ 70% (5+ WOs)

---

## 🚀 Técnicas de Grande Escala

### 1. Multi-Source Queries (20+)
```python
queries = [
    "Darolutamide",
    "Darolutamide patent",
    "ODM-201",
    "ODM-201 patent",
    "BAY-1841788",
    "Darolutamide WO2016",
    "Darolutamide WO2018",
    ...
]
```

### 2. Concurrent Requests (Semaphore)
```python
semaphore = asyncio.Semaphore(5)  # Max 5 simultâneos

async def search_with_limit(query):
    async with semaphore:
        return await search_google_patents_direct(query)

# Execute all with concurrency control
tasks = [search_with_limit(q) for q in queries]
results = await asyncio.gather(*tasks)
```

### 3. Retry Logic (Exponential Backoff)
```python
try:
    resp = await client.get(url)
except HTTPStatusError as e:
    if retry < 2:
        wait_time = 2 ** retry  # 1s, 2s, 4s
        await asyncio.sleep(wait_time)
        return await search(..., retry + 1)
```

### 4. Connection Pooling
```python
async with httpx.AsyncClient(
    timeout=60.0,
    limits=httpx.Limits(
        max_keepalive_connections=10,
        max_connections=20
    )
) as client:
    # Reusa conexões HTTP
```

### 5. Rate Limiting
```python
await asyncio.sleep(0.5)  # 500ms entre requests
```

### 6. API Key Pool
```python
SERPAPI_KEYS = [
    "key1",  # 250 queries/month
    "key2",  # 250 queries/month
]

def get_serpapi_key():
    # Round-robin
    return SERPAPI_KEYS[current_idx % len(SERPAPI_KEYS)]
```

---

## 📊 Resultado Esperado

```json
{
  "wo_discovery": {
    "total_wo": 7-10,
    "wo_numbers": [
      "WO2016162604",  ✅ Match
      "WO2011051540",  ✅ Match
      "WO2018162793",  ✅ Match
      "WO2021229145",  ✅ Match
      "WO2023194528",  ✅ Match
      ...
    ]
  },
  "cortellis_comparison": {
    "match_rate": "71-100%",
    "status": "✅ EXCELLENT"
  }
}
```

---

## 🚀 Deploy

```bash
# Railway
git init
git add .
git commit -m "V14 WO Discovery"
# Deploy automático

# Test
curl https://YOUR-APP/api/v14/test/darolutamide
```

---

## ✅ Validação

Se aparecer:

```
[2/3] WO DISCOVERY
    ✓ 'Darolutamide': 3 WOs
    ✓ 'ODM-201': 2 WOs
  → Total WOs discovered: 7

RESULTADO WO DISCOVERY:
  Match rate: 71%
  Status: ✅ EXCELLENT
```

**= SUCESSO!**

---

## 📝 Next Steps

1. ✅ **Step 1:** WO Discovery (current)
2. ⏳ **Step 2:** BR Patent mapping
3. ⏳ **Step 3:** INPI validation
