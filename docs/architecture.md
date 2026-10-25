# Architecture GarminToGPT

GarminToGPT sépare strictement l’UI, l’API et les effets de bord système.

```text
Clé Personal API Garmin
  -> garmin-connect-personal-api-python (client officiel)
  -> garmin-personal-mcp (MCP stdio, lecture seule)
  -> mcp-proxy 127.0.0.1:8080/mcp
  -> tunnel-client OpenAI (sortant)
  -> OpenAI tunnel service
  -> ChatGPT (Connection: Tunnel)
```

```text
Next.js UI
  -> FastAPI backend
    -> GarminAuthService (clé API Garmin, rotation, jeton)
    -> TunnelService (config OpenAI, binaire, /readyz)
    -> McpService
    -> LogService
    -> TestService
    -> ProcessManager
```

Le frontend appelle uniquement `/api/*`. Il ne lance jamais de processus.

Le backend est responsable des PID, logs, redaction, healthchecks, endpoints
stables et de l’état du tunnel.

## Garmin

La clé Personal API et le cache de jeton sont partagés avec le client officiel :

- `~/.config/garmin/connect-personal-api-key`
- `~/.config/garmin/connect-personal-api-bearer-token.json`

`GARMIN_PERSONAL_API_KEY` reste prioritaire sur le fichier. La Personal API est
en lecture seule.

## Tunnel OpenAI

Le tunnel ID et la runtime key sont gérés par la page `/tunnel` :

- `~/.config/garmintogpt/openai-tunnel.json`
- `~/.config/garmintogpt/openai-tunnel-key` (0600)

`CONTROL_PLANE_TUNNEL_ID` et `CONTROL_PLANE_API_KEY` (ou `OPENAI_API_KEY`) sont
prioritaires.

Le client `tunnel-client` est un daemon sortant : il interroge le control plane
OpenAI et transfère les appels MCP au proxy local. Il n’y a **aucune URL
publique** ni port entrant. Le healthcheck local est exposé sur
`127.0.0.1:8091` (`/readyz`, `/ui`, `/metrics`).

Le binaire est épinglé `v0.0.18`, téléchargé avec vérification SHA-256 dans
`runtime/bin` (Windows/Linux) ou installé dans l’image Docker.

En mode buildé, Next.js exporte des fichiers statiques dans `frontend/out`,
servis par FastAPI. Le conteneur final expose un seul port applicatif `8000`.
