# Architecture GarminToGPT 1.1.5

GarminToGPT sépare strictement l’UI, l’API et les effets de bord système.

```text
Clé API personnelle Garmin (GCDC_…)
  -> garmin-connect-personal-api-python (client officiel)
  -> Garmin Personal MCP (garmin-personal-mcp, MCP stdio lecture seule)
  -> mcp-proxy 127.0.0.1:8080/mcp
  -> openai/tunnel-client (connexion sortante)
  -> OpenAI Secure MCP Tunnel
  -> ChatGPT (Connection: Tunnel)
```

```text
Next.js UI
  -> FastAPI backend
    -> GarminAuthService (clé Garmin, rotation, jeton)
    -> TunnelService (config OpenAI, binaire, /readyz)
    -> McpService
    -> LogService
    -> TestService
    -> ProcessManager
```

Le frontend appelle uniquement `/api/*`. Il ne lance jamais de processus.

Le backend est responsable des PID, logs, redaction, healthchecks, endpoints
stables et de l’état du tunnel.

En Docker, tout l’état persistant est monté dans `/appdata` depuis
`./garmintogpt/appdata` ; l’entrypoint relie `runtime/`, `logs/` et
`~/.config/garmin*` vers ce dossier.

## Garmin Personal MCP

[Garmin Personal MCP](https://github.com/Mason-Levyy/garmin-personal-mcp) est un
serveur MCP construit sur la
[Personal API officielle de Garmin](https://github.com/garmin/connect-personal-api-python).
Il est lancé via `uvx` et communique en stdio avec `mcp-proxy`.

La clé API personnelle Garmin et le cache de jeton sont partagés avec le client
officiel :

- `~/.config/garmin/connect-personal-api-key`
- `~/.config/garmin/connect-personal-api-bearer-token.json`

`GARMIN_PERSONAL_API_KEY` reste prioritaire sur le fichier. La Personal API est
en lecture seule.

## Tunnel OpenAI

Le tunnel ID et la clé API ChatGPT sont gérés par la page `/tunnel` :

- `~/.config/garmintogpt/openai-tunnel.json`
- `~/.config/garmintogpt/openai-tunnel-key` (0600)

`CONTROL_PLANE_TUNNEL_ID` et `CONTROL_PLANE_API_KEY` (ou `OPENAI_API_KEY`) sont
prioritaires.

Le client [`openai/tunnel-client`](https://github.com/openai/tunnel-client) est
un daemon sortant : il interroge le control plane OpenAI et transfère les appels
MCP au proxy local. Il n’y a **aucune URL publique** ni port entrant. Le
healthcheck local est exposé sur `127.0.0.1:8091` (`/readyz`, `/ui`,
`/metrics`).

Le binaire est épinglé `v0.0.18`, téléchargé avec vérification SHA-256 dans
`runtime/bin`, ou installé dans l’image Docker. Le client attend
le listener MCP local jusqu’à 90 s (`--mcp.startup-wait-timeout`) avant le
premier poll OpenAI.

En mode buildé, Next.js exporte des fichiers statiques dans `frontend/out`,
servis par FastAPI. Le conteneur final expose un seul port applicatif `8000`.

## Références

- [Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [openai/tunnel-client](https://github.com/openai/tunnel-client)
- [Garmin Personal MCP](https://github.com/Mason-Levyy/garmin-personal-mcp)
- [Garmin Personal API client](https://github.com/garmin/connect-personal-api-python)
