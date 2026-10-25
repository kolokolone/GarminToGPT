# Tunnel OpenAI (Secure MCP Tunnel)

GarminToGPT utilise le client officiel
[`openai/tunnel-client`](https://github.com/openai/tunnel-client) pour relier le
MCP local à ChatGPT. Le client se connecte **en sortie** au control plane
OpenAI : aucun port entrant ni URL publique n’est créé.

## Valeurs nécessaires

| Valeur | Où la trouver | Secret |
|---|---|---|
| `tunnel_id` | Platform → Tunnels | non |
| Runtime API key | Platform → Runtime API keys, permissions Tunnels **Read + Use** | oui |
| URL MCP locale | `http://127.0.0.1:8080/mcp` | non |

Une **admin key** (`OPENAI_ADMIN_KEY`) ne doit pas être utilisée pour le daemon :
elle sert uniquement à créer/lister/modifier/supprimer des tunnels.

## Configuration dans l’application

Ouvre `http://127.0.0.1:8000/tunnel`.

- Colle le `tunnel_id` et la runtime key.
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
commande. Le healthcheck est lu sur :

- `http://127.0.0.1:8091/readyz` — état prêt ;
- `http://127.0.0.1:8091/ui` — tableau de bord local ;
- `http://127.0.0.1:8091/metrics` — métriques Prometheus.

`mcp-proxy` continue d’écouter sur `127.0.0.1:8080/mcp` ; le tunnel s’y connecte
en local. `--mcp.startup-wait-timeout 90s` laisse au proxy le temps de démarrer
(et de s’installer au premier lancement) avant le premier poll OpenAI.

## Côté ChatGPT

1. Le client doit être démarré et `/readyz` doit répondre 200.
2. ChatGPT → Settings → Connectors.
3. Choisir `Connection: Tunnel`.
4. Sélectionner le tunnel ou coller le `tunnel_id`.
5. Garder le client démarré : il reçoit les appels MCP et les transfère au proxy
   local.

Il n’y a **pas d’URL `https://…/mcp` à copier**. Le tunnel est identifié par son
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
- La runtime key est un secret : ne la mets ni dans Git, ni dans un log, ni dans
  la ligne de commande.

## Dépannage

- `No usable tunnel` / 401 : clé invalide, expirée, ou permissions Tunnels
  Read + Use absentes.
- 404 : `tunnel_id` erroné ou hors du workspace OpenAI.
- `/readyz` reste en 503 : vérifie les logs `logs/tunnel.log`, l’accès sortant
  vers `api.openai.com`, et que `mcp-proxy` répond sur `127.0.0.1:8080/mcp`.
- Le tunnel n’apparaît pas dans ChatGPT : vérifie le workspace/les permissions
  du connecteur, puis attends la propagation côté OpenAI.
- Port 8091 occupé : arrête l’ancien client ou change `tunnel.health_port`.
