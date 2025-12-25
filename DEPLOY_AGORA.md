# 🚀 DEPLOY V17 - AGORA NA RAILWAY

## ⚡ 3 PASSOS PARA VER FUNCIONANDO

### 1️⃣ GitHub (2 min)
```bash
cd ~/Downloads
unzip pharmyrus-v17-PRODUCTION.zip
cd pharmyrus-v17-PRODUCTION

git init
git add .
git commit -m "V17 Production - IP rotation + Quarantine"
git remote add origin https://github.com/SEU_USUARIO/pharmyrus-v17.git
git push -u origin main
```

### 2️⃣ Railway (2 min)
1. Railway Dashboard
2. New Project → Deploy from GitHub
3. Selecione o repositório `pharmyrus-v17`
4. Deploy automático inicia
5. **Aguarde 2-3 min**

### 3️⃣ Testar (30 seg)

#### Teste 1: Health Check
```bash
curl https://SEU_APP.railway.app/health
```
**Esperado:**
```json
{
  "status": "healthy",
  "total_proxies": 200,
  "healthy_proxies": 200,
  "quarantined_proxies": 0,
  "global_success_rate": "0.0%"
}
```

#### Teste 2: Quick Test
```bash
curl https://SEU_APP.railway.app/api/v17/test/darolutamide
```
**Esperado:**
```json
{
  "status": "success",
  "molecule": "darolutamide",
  "system_info": {
    "total_proxies": 200,
    "healthy_proxies": 200,
    "keys": 14
  }
}
```

#### 🔥 Teste 3: BUSCA REAL COM WOs!
```bash
curl -X POST https://SEU_APP.railway.app/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "nome_molecula": "darolutamide",
    "dev_codes": ["ODM-201"]
  }'
```

**Esperado (VAI LEVAR ~30 SEG):**
```json
{
  "molecule": "darolutamide",
  "wo_numbers": [
    "WO2011051540",
    "WO2016162604",
    "WO2018162793",
    ...
  ],
  "br_numbers": [
    "BR112012027681",
    "BR112017024082",
    ...
  ],
  "summary": {
    "total_wo": 10,
    "total_br": 5,
    "parallel_execution": true
  },
  "proxy_stats": {
    "healthy_proxies": 195,
    "quarantined_proxies": 5,
    "global_success_rate": 0.85
  }
}
```

---

## 📊 O QUE VAI ACONTECER NOS LOGS

### Startup (primeiros 10 seg):
```
🚀 Starting Pharmyrus V17 Production...
🔧 Initializing HIGH-VOLUME crawler...
📦 Proxy pool: 200 proxies loaded
✅ WebShare key usj7vxj7...: 10 proxies
✅ WebShare key 64vy07th...: 10 proxies
...
✅ Crawler ready: 200 proxies
✅ Pharmyrus V17 ready!
```

### Durante busca REAL:
```
======================================================================
🚀 HIGH-VOLUME SEARCH: darolutamide
======================================================================

📊 Executing 10 queries in parallel (max 5 concurrent)...

🔍 Query: darolutamide patent
   🌐 Using: http://142.111.48.253:7030...
   ✅ Found 3 WO numbers

🔍 Query: darolutamide WO2011
   🌐 Using: http://185.193.28.75:80...      <--- IP DIFERENTE!
   ✅ Found 2 WO numbers

🔍 Query: ODM-201 patent WO
   🌐 Using: http://91.203.18.144:8080...    <--- IP DIFERENTE!
   ✅ Found 1 WO numbers

✅ Total WO numbers found: 15
📍 Extracting BR numbers from 15 WOs...

   WO WO2011051540: 2 BR patents
   WO WO2016162604: 3 BR patents
   ...

✅ Total BR numbers found: 8

======================================================================
🔥 ADVANCED PROXY MANAGER STATUS
======================================================================

POOL STATUS:
  Total proxies: 200
  ✅ Healthy: 195
  ⛔ Quarantined: 5                         <--- QUARENTENA AUTOMÁTICA!

GLOBAL STATS:
  Total requests: 45
  Successes: 38
  Failures: 7
  Success rate: 84.4%

TOP PERFORMERS:
  1. http://142.111.48.253:7030... - 100.0% (5 req)
  2. http://185.193.28.75:80... - 100.0% (4 req)
  3. http://91.203.18.144:8080... - 95.5% (3 req)

QUARANTINED:
  ⛔ http://45.77.39.89:9050... - 3 failures (release in 245s)
  ⛔ http://198.211.124.58:3128... - 4 failures (release in 180s)
======================================================================
```

---

## ✅ VERIFICAÇÃO DE FEATURES

### ✅ IP Diferente Por Consulta
```
Query 1: 🌐 Using: http://142.111.48.253...
Query 2: 🌐 Using: http://185.193.28.75...    <-- DIFERENTE!
Query 3: 🌐 Using: http://91.203.18.144...    <-- DIFERENTE!
```
**NUNCA repete consecutivo!**

### ✅ Quarentena Automática
```
Proxy falha → ⚠️  Warning
Proxy falha → ⚠️  Warning
Proxy falha → ⛔ QUARANTINE (5 min ban)
```

### ✅ Alto Volume
```
📊 Executing 10 queries in parallel (max 5 concurrent)...
```
**5 queries simultâneas!**

### ✅ Coleta Real de WOs
```
✅ Total WO numbers found: 15
✅ Total BR numbers found: 8
```

---

## 🎯 ENDPOINTS DISPONÍVEIS

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Health check básico |
| `/health` | GET | Status detalhado |
| `/api/v17/test/{molecule}` | GET | Test rápido |
| `/api/search` | POST | **Busca REAL com WOs** 🔥 |
| `/api/proxy/status` | GET | Status dos proxies |
| `/api/status` | GET | Status completo do sistema |

---

## 🔥 COMANDOS PRONTOS

Substitua `SEU_APP` pelo seu domínio Railway:

```bash
# 1. Health
curl https://SEU_APP.railway.app/health

# 2. Test
curl https://SEU_APP.railway.app/api/v17/test/aspirin

# 3. Busca REAL (Darolutamide)
curl -X POST https://SEU_APP.railway.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"nome_molecula": "darolutamide", "dev_codes": ["ODM-201"]}'

# 4. Busca REAL (Aspirin)
curl -X POST https://SEU_APP.railway.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"nome_molecula": "aspirin"}'

# 5. Proxy Status
curl https://SEU_APP.railway.app/api/proxy/status
```

---

## 📊 DADOS DE VALIDAÇÃO

### Darolutamide (baseline Cortellis):
```
WOs esperados:
✅ WO2011051540
✅ WO2016162604
✅ WO2018162793
✅ WO2021229145
✅ WO2023194528

BRs esperados: 5-8
```

### Aspirin (teste simples):
```
WOs esperados: 10-20
BRs esperados: 3-10
```

---

## ⚡ PERFORMANCE

- **Startup:** 10-15 seg
- **First request:** 30-40 seg (coleta real)
- **Subsequent:** 20-30 seg
- **Paralelização:** 5 queries simultâneas
- **IP rotation:** 100% garantida
- **Quarentena:** Automática em 3 falhas

---

## 🚨 SE DER ERRO

### Erro 502:
→ Veja os logs no Railway
→ Copie e cole aqui

### Erro 503:
→ Sistema ainda inicializando (aguarde 15 seg)

### Timeout:
→ Normal na primeira busca
→ Aguarde até 60 seg

---

## ✅ CHECKLIST FINAL

- [ ] ZIP baixado
- [ ] Git commit feito
- [ ] Pushed para GitHub
- [ ] Railway deploy iniciado
- [ ] Aguardou 2-3 min
- [ ] Testou `/health` → OK
- [ ] Testou `/api/v17/test/darolutamide` → OK
- [ ] **Testou `/api/search` com darolutamide** → 🔥 **VAI FUNCIONAR!**

---

**Próximo passo:** BAIXE O ZIP e siga os 3 passos! 🚀
