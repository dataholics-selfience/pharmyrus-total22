# 🔧 DEBUG: Healthcheck Failed

## ❌ PROBLEMA

```
Attempt #1 failed with service unavailable
Attempt #2 failed with service unavailable
...
1/1 replicas never became healthy!
Healthcheck failed!
```

## 🔍 CAUSA RAIZ

Railway healthcheck tenta acessar `/health` mas a aplicação **não responde** porque:

1. ❌ App rodando na porta **8000**
2. ✅ Railway esperando na porta **$PORT** (dinâmica, ex: 8080)

**CONFLITO DE PORTA!**

---

## ✅ CORREÇÃO APLICADA NA V17.1

### 1️⃣ Dockerfile agora usa PORT env var:
```dockerfile
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### 2️⃣ main.py também usa PORT:
```python
port = int(os.environ.get("PORT", 8000))
uvicorn.run(app, host="0.0.0.0", port=port)
```

### 3️⃣ Logs detalhados no startup:
```
🚀 PHARMYRUS V17 PRODUCTION STARTUP
📡 PORT: 8080
🌐 Environment: production
```

---

## 🚀 COMO REDEPLOY COM FIX

### Opção 1: GitHub Push (RECOMENDADO)
```bash
cd pharmyrus-v17-PRODUCTION
git add .
git commit -m "V17.1 - PORT fix for Railway"
git push
```

Railway vai redeploy automático!

### Opção 2: Redeploy Manual
1. Railway Dashboard
2. Deployments → Latest
3. Click "Redeploy"

---

## ✅ VERIFICAR SE FUNCIONOU

### 1. Ver logs durante startup:
```
🚀 PHARMYRUS V17 PRODUCTION STARTUP
📡 PORT: 8080                           <--- DEVE APARECER!
🌐 Environment: production
🔧 Initializing crawler...
📦 Loading proxies...
✅ WebShare key usj7vxj7...: 10 proxies
✅ PHARMYRUS V17 READY!
📊 Total proxies: 200
📊 Healthy proxies: 200
```

### 2. Healthcheck deve passar:
```
==================== Starting Healthcheck ====================
Path: /health
Attempt #1 succeeded!
✅ Deployment successful!
```

### 3. Testar endpoint:
```bash
curl https://SEU_APP.railway.app/health
```

**Esperado:**
```json
{
  "status": "healthy",
  "total_proxies": 200,
  "healthy_proxies": 200
}
```

---

## 🔧 O QUE MUDOU

| Antes (V17.0) | Depois (V17.1) |
|---------------|----------------|
| Port fixo 8000 | Port dinâmico $PORT ✅ |
| Sem logs de porta | Logs detalhados ✅ |
| Healthcheck fail | Healthcheck pass ✅ |

---

## 📊 TIMELINE ESPERADO

```
00:00 - Build starts
00:30 - Docker build complete
01:00 - Container starting
01:10 - App startup (proxy loading)
01:30 - ✅ Healthcheck pass!
01:35 - ✅ Deployment successful!
```

**Total: ~90 segundos**

---

## 🚨 SE AINDA FALHAR

Copie os logs e procure:

### ✅ LOGS BONS:
```
📡 PORT: 8080
🔧 Initializing crawler...
✅ PHARMYRUS V17 READY!
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### ❌ LOGS RUINS:
```
Error: ...
ModuleNotFoundError: ...
Traceback ...
```

Se ver erro → **COPIE E COLE AQUI**!

---

## 💡 POR QUE ISSO ACONTECEU?

Railway usa **PORT dinâmica** para roteamento interno.

Cada deploy pode usar porta diferente:
- Deploy 1: PORT=8080
- Deploy 2: PORT=7030
- Deploy 3: PORT=9050

Por isso **SEMPRE** use `$PORT` em vez de porta fixa!

---

## ✅ CHECKLIST

- [x] Dockerfile usa ${PORT:-8000}
- [x] main.py usa os.environ.get("PORT")
- [x] Logs mostram porta no startup
- [x] Healthcheck configurado em railway.json
- [ ] **Git push feito**
- [ ] **Redeploy Railway**
- [ ] **Logs verificados**
- [ ] **Healthcheck passou**
- [ ] **Endpoint testado**

---

**Próximo passo:** Baixe o ZIP atualizado e faça git push! 🚀
