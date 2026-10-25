# Architecture GarminToGPT

GarminToGPT sépare strictement l’UI, l’API et les effets de bord système.

```text
Garmin Connect Personal API (clé GCDC_)
  -> garmin-connect-personal-api-python (client officiel, jeton 24 h)
  -> garmin-personal-mcp (outils MCP lecture seule)
  -> mcp-proxy 127.0.0.1:8080/mcp
  -> cloudflared
  -> ChatGPT MCP Connector
```

```text
Next.js UI
  -> FastAPI backend
    -> GarminAuthService (clé API, rotation, jeton)
    -> McpService
    -> TunnelService
    -> LogService
    -> TestService
    -> ProcessManager
```

Le frontend appelle uniquement `/api/*`. Il ne lance jamais de processus.

Le backend est responsable des PID, logs, redaction, healthchecks, endpoints stables et URL finale ChatGPT.

La clé Personal API et le cache de jeton sont partagés avec le client officiel :

- `~/.config/garmin/connect-personal-api-key`
- `~/.config/garmin/connect-personal-api-bearer-token.json`

`GARMIN_PERSONAL_API_KEY` reste prioritaire sur le fichier, comme dans le client Garmin.
La Personal API est en lecture seule : les outils d'écriture de l'ancien serveur SSO ne sont plus exposés.

En mode buildé, Next.js exporte des fichiers statiques dans `frontend/out`, servis par FastAPI. Le conteneur final expose un seul port applicatif `8000`, tandis que le proxy MCP reste sur `127.0.0.1:8080` à l’intérieur de l’environnement d’exécution.
