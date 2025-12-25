# 🔧 DEBUG RAILWAY - PHARMYRUS V16.1

## ❌ ERRO 502 - Application failed to respond

### CAUSAS POSSÍVEIS:

1. ❌ App não iniciou (crash no startup)
2. ❌ App não responde na porta correta
3. ❌ Timeout no healthcheck
4. ❌ Erro na inicialização do crawler

---

## 🔍 COMO DEBUGAR NO RAILWAY

### 1️⃣ VER LOGS

```
Railway Dashboard → Deployments → View Logs
```

**O que procurar:**
```
✅ Logs bons:
🚀 Starting Pharmyrus V16.1 Lightweight...
🔧 Initializing proxy pool...
✅ Proxy pool ready: 200 proxies
✅ Pharmyrus ready!
INFO:     Uvicorn running on http://0.0.0.0:8000

❌ Logs ruins:
Error: ...
Traceback ...
ModuleNotFoundError ...
Connection refused ...
```

### 2️⃣ VERIFICAR VARIÁVEIS DE AMBIENTE

Railway deve ter:
- `PORT` (automático)
- `RAILWAY_ENVIRONMENT` (automático)

**Não precisa configurar nada!**

### 3️⃣ TESTAR ENDPOINTS

```bash
# 1. Root (mais simples)
curl https://SEU_APP.railway.app/

# 2. Health
curl https://SEU_APP.railway.app/health

# 3. Test endpoint (novo!)
curl https://SEU_APP.railway.app/api/v16/test/aspirin

# 4. Status
curl https://SEU_APP.railway.app/api/status
```

---

## 🚀 SOLUÇÃO RÁPIDA

### Se o erro persistir:

#### OPÇÃO A: Redeploy

1. Railway Dashboard
2. Deployments → Latest
3. Click "Redeploy"
4. Aguarde 2-3 min

#### OPÇÃO B: Verificar startup

Logs devem mostrar:
```
🔧 Pharmyrus V16.1 - Starting...
📡 Port: 8000
📦 Checking dependencies...
✅ All imports OK
🚀 Starting server on 0.0.0.0:8000...
```

Se não aparecer → **Erro no código**

#### OPÇÃO C: Testar localmente

```bash
# Descompactar ZIP
cd pharmyrus-v16.1-FIX

# Instalar
pip install -r requirements.txt

# Rodar
python3 main.py

# Testar
curl http://localhost:8000/health
```

Se funcionar local mas não no Railway → **Problema de build**

---

## 📊 CHECKLIST DE VERIFICAÇÃO

- [ ] Logs mostram "Uvicorn running"?
- [ ] Porta correta ($PORT do Railway)?
- [ ] Dependências instaladas?
- [ ] Imports funcionando?
- [ ] Proxies inicializados?
- [ ] Healthcheck responde?

---

## 🎯 ENDPOINTS DE TESTE (EM ORDEM)

### 1. Mais simples (sem crawler)
```bash
curl https://SEU_APP.railway.app/
```
**Esperado:**
```json
{
  "service": "Pharmyrus V16.1 Lightweight",
  "status": "online",
  "version": "16.1.0"
}
```

### 2. Health (com crawler)
```bash
curl https://SEU_APP.railway.app/health
```
**Esperado:**
```json
{
  "status": "healthy",
  "proxies_available": 200,
  "engine": "httpx (lightweight)"
}
```

### 3. Test endpoint (novo!)
```bash
curl https://SEU_APP.railway.app/api/v16/test/darolutamide
```
**Esperado:**
```json
{
  "status": "success",
  "molecule": "darolutamide",
  "test": true,
  "system_info": {
    "proxies": 200,
    "keys": 14
  }
}
```

### 4. Search real
```bash
curl -X POST https://SEU_APP.railway.app/api/search \
  -H "Content-Type: application/json" \
  -d '{"nome_molecula": "aspirin"}'
```

---

## 🔧 PROBLEMAS COMUNS

### 502 Bad Gateway
→ App não iniciou
→ **Ver logs no Railway**

### 503 Service Unavailable
→ App iniciando (aguarde 30 seg)
→ **Normal no primeiro deploy**

### 504 Gateway Timeout
→ Crawler demorando muito
→ **Aumentar timeout no railway.json**

### Connection refused
→ Porta errada
→ **Railway usa variável $PORT**

---

## ✅ SOLUÇÃO APLICADA NESTA VERSÃO

1. ✅ **startup.sh** - Verifica tudo antes de iniciar
2. ✅ **Healthcheck** - Railway monitora /health
3. ✅ **Test endpoint** - /api/v16/test/{molecule}
4. ✅ **Logs detalhados** - Mostra cada etapa
5. ✅ **Error handling** - Não quebra no startup

---

## 🎓 COMANDOS ÚTEIS

### Ver logs em tempo real
```
Railway CLI: railway logs
```

### Redeploy forçado
```
Railway CLI: railway up --detach
```

### Testar local
```bash
export PORT=8000
./startup.sh
```

---

## 📞 PRÓXIMO PASSO

1. ⬇️ Baixe o ZIP atualizado (`pharmyrus-v16.1-FIX.zip`)
2. 📤 Faça commit no GitHub
3. 🔄 Redeploy no Railway
4. 📋 **COPIE E COLE OS LOGS AQUI** se ainda der erro

---

**Com esta versão, você vai ver exatamente onde está o problema nos logs!** 🎯
