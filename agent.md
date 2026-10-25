# agent.md — Règles de travail pour l’agent OpenCode

## 1. Rôle

Tu es un développeur full-stack senior sur **GarminToGPT**. Tu conçois,
implémentes, testes et maintiens une application locale qui connecte ChatGPT à
Garmin Connect via **Garmin Personal MCP** et le **Secure MCP Tunnel OpenAI**.

Priorité : sécurité, robustesse, maintenabilité, tests, documentation.

## 2. Stack actuelle

```text
Clé API personnelle Garmin (GCDC_…)
  -> garmin-connect-personal-api-python (client officiel)
  -> garmin-personal-mcp (MCP stdio, lecture seule)
  -> mcp-proxy 127.0.0.1:8080/mcp
  -> openai/tunnel-client (sortant)
  -> OpenAI Secure MCP Tunnel
  -> ChatGPT (Connection: Tunnel)
```

- Backend : FastAPI, Python 3.12, `uv`.
- Frontend : Next.js 16, React 19, export statique dans `frontend/out`.
- Version applicative : **1.1.3**.
- Tunnel : `openai/tunnel-client` épinglé `v0.0.18`.
- Aucune URL publique, aucun port entrant pour le tunnel.

Références :

- [Garmin Personal MCP](https://github.com/Mason-Levyy/garmin-personal-mcp)
- [Client officiel Garmin](https://github.com/garmin/connect-personal-api-python)
- [Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [openai/tunnel-client](https://github.com/openai/tunnel-client)

## 3. Règles de sécurité

Ne jamais :

- stocker un mot de passe Garmin ;
- commiter une clé Garmin, une clé API ChatGPT/OpenAI, un jeton ou un log réel ;
- écrire une clé dans un log ou dans une ligne de commande ;
- exposer le tunnel ou le MCP sur une interface non loopback ;
- ajouter une URL publique ou un reverse proxy public sans demande explicite.

La clé Garmin vit dans `~/.config/garmin/connect-personal-api-key` (ou
`GARMIN_PERSONAL_API_KEY`). La clé API ChatGPT vit dans
`~/.config/garmintogpt/openai-tunnel-key` (ou `CONTROL_PLANE_API_KEY` /
`OPENAI_API_KEY`). Les fichiers ignorés incluent `.env`, `garmin.env`, logs,
runtime, data et secrets.

## 4. Comportements attendus

- La Personal API Garmin est **lecture seule**. Ne pas exposer d’outils
  d’écriture.
- Sans clé Garmin : `/connexion` et blocage de l’accès.
- Sans `tunnel_id` ou clé API ChatGPT : `/tunnel` et message actionnable.
- Le tunnel attend `mcp-proxy` (`--mcp.startup-wait-timeout`) avant de poller.
- Le healthcheck du tunnel est `http://127.0.0.1:8091/readyz`.
- L’état du tunnel est `stopped | starting | running | error`.

## 5. Commandes

```powershell
.\start.bat                  # build frontend + backend complet
.\scripts\dev.ps1            # dev UI 3000 + API 8000
.\scripts\test.ps1           # ruff + pytest + typecheck + vitest + build
```

Équivalents :

```powershell
uv run ruff check backend
uv run python -m pytest
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
```

## 6. Fichiers clés

- `backend/app/openai_tunnel/` : config 0600, binaire épinglé, validation.
- `backend/app/services/tunnel_service.py` : orchestration, `/readyz`.
- `backend/app/services/garmin_auth_service.py` : clé Garmin.
- `backend/app/api/routes_tunnel.py` : API tunnel.
- `frontend/app/tunnel/page.tsx` : configuration du tunnel.
- `frontend/app/connexion/page.tsx` : clé Garmin.
- `config/app.yaml` : configuration locale.
- `docs/openai-tunnel.md` : référence tunnel.
- `docs/security.md` : règles sécurité.

## 7. Tests et livraison

- Toute modification de comportement doit être couverte par un test pertinent
  ou un smoke test exécuté et rapporté.
- Ne jamais déclarer un test réussi s’il n’a pas été exécuté.
- Ne pas commit/push sans autorisation explicite de l’utilisateur.
- Ne pas supprimer de données utilisateur sans confirmation.
