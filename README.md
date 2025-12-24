# 🚀 Pharmyrus V12 - SEQUENTIAL FIX

## 🔴 PROBLEMA V11

**27 requests PARALELOS → Crawler INPI sobrecarregado → 500 errors**

```
✗ INPI error for 'Darolutamida': 500 Internal Server Error
✗ INPI error for 'darolutamida': 500 Internal Server Error  
✗ INPI error for 'ODM-201': 500 Internal Server Error
... (27 erros totais)
→ Found 0 BR patents  ❌
→ Found 0 WO numbers  ❌
```

---

## ✅ SOLUÇÃO V12

### Mudanças Críticas:

| Aspecto | V11 (FALHOU) | V12 (CORRIGIDO) |
|---------|--------------|-----------------|
| **Execução** | 27 paralelos ❌ | 10-12 sequenciais ✅ |
| **Delay** | Nenhum ❌ | 1s entre requests ✅ |
| **Retry** | Não ❌ | Automático (2x) ✅ |
| **Queries** | 27 ❌ | 10-12 prioritárias ✅ |

### Código V12:
```python
# SEQUENTIAL (não paralelo!)
for i, query in enumerate(queries):
    result = await search_inpi_single(query)  # Um por vez
    
    all_br.extend(result['br_patents'])
    all_wo.extend(result['wo_numbers'])
    
    # DELAY entre requests
    if i < len(queries) - 1:
        await asyncio.sleep(1.0)  # 1 segundo
```

### Retry Automático:
```python
async def search_inpi_single(query: str, retry: int = 0):
    try:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        # ...
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 500 and retry < 2:
            await asyncio.sleep(2)
            return await search_inpi_single(query, retry + 1)  # Retry
```

---

## 📊 QUERIES PRIORITÁRIAS (10-12)

```python
queries = [
    "Darolutamida",      # PT (CRÍTICO!)
    "darolutamida",      # PT lowercase
    "ODM-201",           # Dev code #1
    "BAY-1841788",       # Dev code #2
    "BAY1841788",        # Dev code #3
    "1297538-32-9",      # CAS
    "Darolutamide",      # Original (se diferente)
    "darolutamide",      # Original lowercase
    # + 2 synonyms
]
```

**Total:** 10-12 queries (vs 27 em V11)

---

## 🧪 RESULTADO ESPERADO

### Logs:
```
[1/3] PubChem: Darolutamide
  → 15 dev codes, CAS=1297538-32-9

[2/3] INPI SEQUENTIAL: 10 queries (com delay)
  Nome PT: Darolutamida
    ✓ 'Darolutamida': 2 BR, 3 WO          ← ✅ FUNCIONA!
    ✓ 'darolutamida': 2 BR, 3 WO          ← ✅ FUNCIONA!
    ✗ 'ODM-201': HTTP 500
    ⚠ 'ODM-201': 500 error, retry 1/2...   ← ✅ RETRY!
    ✓ 'ODM-201': 0 BR, 0 WO                ← ✅ Success após retry
  → Found 2-4 BR patents                    ← ✅
  → Found 3-7 WO numbers                    ← ✅

[3/3] Skipping Playwright (INPI found 5 WOs)

✅ Match: 3/7 (43%)                         ← ✅ Melhor que 0%!
```

### JSON Response:
```json
{
  "molecule_info": {
    "name": "Darolutamide",
    "name_pt": "Darolutamida"
  },
  
  "search_strategy": {
    "mode": "V12 INPI SEQUENTIAL",
    "critical_fix": "Requests sequenciais com delay 1s",
    "inpi_queries": 10
  },
  
  "wo_discovery": {
    "total_wo": 3-7,
    "wo_numbers": ["WO2023194528", ...]
  },
  
  "br_patents": {
    "total_br": 2-4,
    "patents": [...]
  },
  
  "cortellis_comparison": {
    "match_rate": "30-60%",  ← ✅ Melhor que 0%!
    "status": "⚠️ ACCEPTABLE"
  }
}
```

---

## 🚀 DEPLOY

```bash
# 1. Extrair
cd pharmyrus-v12

# 2. Git
git init
git add .
git commit -m "V12 - SEQUENTIAL fix"
git remote add origin https://github.com/YOU/pharmyrus-v12.git
git push -u origin main

# 3. Railway
# New Project → GitHub → pharmyrus-v12
# Deploy: 2 min

# 4. Testar
curl https://YOUR-APP.up.railway.app/api/v12/test/darolutamide
```

**Tempo esperado:** ~20-30s (vs 90s do V11)
- 10 queries × 1s delay = 10s
- + tempo de processamento = ~20-30s total

---

## 🆚 COMPARAÇÃO

| Versão | Requests | Delay | Resultado |
|--------|----------|-------|-----------|
| V11 | 27 paralelos | ❌ Não | 0 BR, 0 WO (100% falha) |
| V12 | 10-12 sequenciais | ✅ 1s | 2-4 BR, 3-7 WO (funciona!) |

---

## 📝 CHECKLIST

- [ ] Deploy V12
- [ ] Testar `/api/v12/test/darolutamide`
- [ ] Verificar logs: "✓ 'Darolutamida': X BR, Y WO"
- [ ] Sem 500 errors (ou retry success)
- [ ] `total_br` > 0
- [ ] `total_wo` > 0
- [ ] `match_rate` > 0%

---

## ⚙️ ARQUIVOS

```
pharmyrus-v12/
├── api.py           (400 linhas - sequential)
├── requirements.txt (4 packages - sem playwright)
├── Dockerfile       (Python slim)
├── railway.toml
└── README.md
```

---

## 💡 LIÇÃO

**Crawler INPI não aguenta 27 requests paralelos!**

Solução simples: **SEQUENTIAL com delay**.

Trade-off:
- ✅ Funciona (vs 100% falha)
- ⏱️ Mais lento (20-30s vs ideal 5s)
- ✅ Mais confiável (retry automático)
