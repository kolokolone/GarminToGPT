# Tunnel OpenAI (Secure MCP Tunnel)

GarminToGPT relie [Garmin Personal MCP](https://github.com/Mason-Levyy/garmin-personal-mcp)
à ChatGPT avec le client officiel
[`openai/tunnel-client`](https://github.com/openai/tunnel-client), derrière le
[Secure MCP Tunnel d’OpenAI](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).
Le client se connecte **en sortie** au control plane OpenAI : aucun port entrant
ni URL publique n’est créé.

## Valeurs nécessaires

| Valeur | Où la trouver | Secret |
|---|---|---|
| Clé API personnelle Garmin | Garmin Connect → Personal API | oui |
| `tunnel_id` | Platform → Tunnels | non |
| Clé API ChatGPT (runtime key OpenAI) | Platform → Runtime API keys, Tunnels Read + Use | oui |
| URL MCP locale | `http://127.0.0.1:8080/mcp` | non |

Une **admin key** (`OPENAI_ADMIN_KEY`) ne doit pas être utilisée pour le daemon :
elle sert uniquement à créer, lister, modifier ou supprimer des tunnels.

## Utilisation normale (Docker)

```powershell
docker compose up -d --build
```

Ouvre `http://127.0.0.1:8000/tunnel` et enregistre le `tunnel_id` et la clé API
ChatGPT. Les volumes `garmintogpt_openai`, `garmintogpt_garmin` et
`garmintogpt_runtime` conservent les clés et l’état entre les redémarrages.
`docker compose down` conserve les volumes ; `docker compose down -v` les
supprime (et efface donc les clés).

## Configuration dans l’application

Ouvre `http://127.0.0.1:8000/tunnel`.

- Colle le `tunnel_id` et la clé API ChatGPT.
- `Tester et enregistrer` exécute
  `tunnel-client admin --json tunnels get <tunnel_id>` avec la clé avant de
  sauvegarder. Un 401/403 signifie que la clé est invalide ou n’a pas les
  permissions Tunnels Read + Use ; un 404 signifie que le tunnel est introuvable
  ou hors du workspace.
- Le tunnel ID est stocké dans
  `~/.config/garmintogpt/openai-tunnel.json`.
- La clé est stockée dans
  `~/.config/garmintogpt/openai-tunnel-key` avec des permissions 0600 (best
  effort sur Windows).
- `CONTROL_PLANE_TUNNEL_ID` et `CONTROL_PLANE_API_KEY` (ou `OPENAI_API_KEY`)
  sont prioritaires sur les fichiers ; la page affiche alors la configuration
  comme non éditable.

La dernière valeur enregistrée dans `/tunnel` est celle utilisée au redémarrage
suivant. L’écriture est atomique et l’ancien cache de jeton est invalidé par
l’empreinte de la clé. Il n’y a pas de SQLite : deux fichiers locaux suffisent,
et ils restent compatibles avec les outils OpenAI.

## Démarrage et diagnostic

Le client est lancé avec :

```text
tunnel-client run
  --control-plane.tunnel-id <tunnel_id>
  --control-plane.api-key env:CONTROL_PLANE_API_KEY
  --mcp.server-url url=http://127.0.0.1:8080/mcp,channel=main
  --mcp.startup-wait-timeout 90s
  --health.listen-addr 127.0.0.1:8091
```

La clé est passée au processus par son environnement, jamais dans la ligne de
commande. `--mcp.startup-wait-timeout` attend que `mcp-proxy` écoute avant le
premier poll OpenAI (utile au premier lancement `uvx`). Le healthcheck est lu
sur :

- `http://127.0.0.1:8091/readyz` — état prêt ;
- `http://127.0.0.1:8091/ui` — tableau de bord local ;
- `http://127.0.0.1:8091/metrics` — métriques Prometheus.

`mcp-proxy` continue d’écouter sur `127.0.0.1:8080/mcp` ; le tunnel s’y connecte
en local, puis Garmin Personal MCP fournit les outils.

## Côté ChatGPT

1. Le client doit être démarré et `/readyz` doit répondre 200.
2. ChatGPT → Settings → Connectors.
3. Choisir `Connection: Tunnel`.
4. Sélectionner le tunnel ou coller le `tunnel_id`.
5. Pour l’authentification du connecteur, choisir **Sans authentification**.
6. Garder le client démarré : il reçoit les appels MCP et les transfère au proxy
   local.

Il n’y a **pas d’URL publique** à copier. Le tunnel est identifié par son
`tunnel_id` côté ChatGPT.

## Binaire

La release épinglée est `v0.0.18`. Le backend télécharge l’archive officielle
Windows/Linux (amd64/arm64) dans `runtime/bin` au premier démarrage, vérifie son
SHA-256, puis extrait uniquement `tunnel-client` (le compagnon `cloudflared`
présent dans l’archive n’est pas utilisé).

L’image Docker télécharge et vérifie le binaire Linux amd64 au build ; il est
donc déjà dans le `PATH` et l’application ne le retélécharge pas.

Pour un binaire géré manuellement, place `tunnel-client` dans le `PATH` ou
renseigne `tunnel.command` dans `config/app.yaml`.

## Réseau et sécurité

- Sortie HTTPS vers `api.openai.com:443` (`/v1/tunnels/*`) obligatoire.
- Aucun port entrant requis pour le tunnel.
- Le healthcheck et le tableau de bord du client restent sur `127.0.0.1`.
- Les requêtes/réponses MCP transitent par OpenAI ; le tunnel ne rend pas les
  données strictement locales.
- La clé API ChatGPT est un secret : ne la mets ni dans Git, ni dans un log, ni
  dans la ligne de commande.

## Dépannage

- `No usable tunnel` / 401 : clé invalide, expirée, ou permissions Tunnels
  Read + Use absentes.
- 404 : `tunnel_id` erroné ou hors du workspace OpenAI.
- `/readyz` reste en 503 : vérifie les logs `logs/tunnel.log`, l’accès sortant
  vers `api.openai.com`, et que `mcp-proxy` répond sur `127.0.0.1:8080/mcp`.
- `connection refused` sur 8080 au démarrage : le tunnel attend désormais MCP
  jusqu’à 90 s ; si le premier démarrage est plus long, augmente
  `tunnel.mcp_startup_timeout_seconds`.
- Le tunnel n’apparaît pas dans ChatGPT : vérifie le workspace/les permissions
  du connecteur, puis attends la propagation côté OpenAI.
- Port 8091 occupé : arrête l’ancien client ou change `tunnel.health_port`.

## Références

- [Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [openai/tunnel-client](https://github.com/openai/tunnel-client)
- [Garmin Personal MCP](https://github.com/Mason-Levyy/garmin-personal-mcp)
- [Client officiel Garmin Personal API](https://github.com/garmin/connect-personal-api-python)
