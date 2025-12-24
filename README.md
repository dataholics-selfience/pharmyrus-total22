# Pharmyrus V9 SIMPLE

## 🎯 Por que V9?

**Problema V8**: Tentei reimplementar com EPO OPS, WIPO, Playwright → Complexidade alta, erros de deploy

**Solução V9**: **Usar o que JÁ FUNCIONA no n8n**
- ✅ PubChem → dev codes + CAS
- ✅ Google Patents → WO numbers (HTTP simples, sem SerpAPI)
- ✅ INPI Crawler → BR patents (seu crawler existente!)

**Total**: 250 linhas Python, ZERO dependências complexas

---

## 🚀 Deploy (2 minutos)

```bash
# 1. Git
cd pharmyrus-simple
git init
git add .
git commit -m "V9 Simple - Based on working n8n"
git remote add origin https://github.com/YOU/pharmyrus-v9.git
git push -u origin main

# 2. Railway
# New Project → GitHub → pharmyrus-v9
# Auto-deploy em 30-60s ✅

# 3. Test
curl https://pharmyrus-v9-xxx.up.railway.app/api/v9/test/darolutamide
```

---

## 📊 O que Esperar

**Darolutamide**:
- WO: 10-20 encontrados (meta: 5-7 match com Cortellis)
- BR: 8-15 encontrados (meta: 6-8 match com Cortellis)
- Tempo: 10-30 segundos

Se match rate < 70%:
- Ajustar queries em `api.py` linha ~120
- Adicionar mais dev codes
- Refinar regex de extração WO

---

## 🔧 Como Funciona

```python
# 1. PubChem
dev_codes = ['BAY-1841788', 'ODM-201']
cas = '1297538-32-9'

# 2. Build queries (como n8n)
queries = [
    "darolutamide Bayer patent WO",
    "darolutamide Orion Corporation patent",
    "BAY-1841788 patent WO",
    ...
]

# 3. Google Patents (simples)
for query in queries:
    html = requests.get(f"https://patents.google.com/?q={query}")
    wos = extract_wo_numbers(html)

# 4. INPI Crawler (seu existente)
br_patents = requests.get(
    "https://crawler3-production.up.railway.app/api/data/inpi/patents",
    params={'medicine': 'darolutamide'}
)

# 5. Consolidate
return {
    'wo_numbers': [...],
    'br_patents': [...],
    'cortellis_comparison': {...}
}
```

---

## ✅ Vantagens

**vs V8**:
- ❌ Sem EPO OPS OAuth
- ❌ Sem WIPO crawler
- ❌ Sem Playwright
- ❌ Sem dependências complexas
- ✅ Deploy funciona em 30s
- ✅ 250 linhas vs 1800
- ✅ Baseado no que JÁ FUNCIONA

**vs n8n atual**:
- ✅ API HTTP (fácil integrar)
- ✅ JSON estruturado
- ✅ Comparação Cortellis automática
- ✅ Mais rápido (Python async)

---

## 🔄 Próximo Passo: Integrar SerpAPI

**Quando estiver pronto** (não agora):

```python
# Em api.py, substituir search_google_patents_simple por:

async def search_google_patents_serpapi(query: str) -> List[str]:
    url = "https://serpapi.com/search.json"
    params = {
        'engine': 'google_patents',
        'q': query,
        'api_key': os.getenv('SERPAPI_KEY')
    }
    resp = await client.get(url, params=params)
    data = resp.json()
    
    wos = []
    for result in data.get('organic_results', []):
        pub_num = result.get('publication_number', '')
        if pub_num.startswith('WO'):
            wos.append(pub_num)
    
    return wos
```

Depois redeploy e será **idêntico ao n8n** mas em API Python!

---

**COMECE SIMPLES. FUNCIONE PRIMEIRO. OTIMIZE DEPOIS.**
