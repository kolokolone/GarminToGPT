# Architecture GarminToGPT

GarminToGPT sépare strictement l’UI, l’API et les effets de bord système.

```text
Next.js UI
  -> FastAPI backend
    -> GarminAuthService
    -> McpService
    -> TunnelService
    -> LogService
    -> TestService
    -> ProcessManager
      -> garmin-mcp / mcp-proxy / cloudflared
```

Le frontend appelle uniquement `/api/*`. Il ne lance jamais de processus.

Le backend est responsable des PID, logs, redaction, healthchecks, endpoints stables et URL finale ChatGPT.

En mode buildé, Next.js exporte des fichiers statiques dans `frontend/out`, servis par FastAPI. Le conteneur final expose un seul port applicatif `8000`, tandis que le proxy MCP reste sur `127.0.0.1:8080` à l’intérieur de l’environnement d’exécution.
