# Sécurité

Priorité : sécurité, robustesse, diagnostic, simplicité.

## Clé API personnelle Garmin

GarminToGPT ne stocke pas de mot de passe Garmin. La connexion utilise la clé
Personal API officielle, échangée contre un jeton de 24 h par
`garmin-connect-personal-api-python`.

- Clé : `~/.config/garmin/connect-personal-api-key` (0600 best effort) ou
  `GARMIN_PERSONAL_API_KEY`.
- Cache de jeton : `~/.config/garmin/connect-personal-api-bearer-token.json`.
- La clé et le jeton ne sont jamais renvoyés par l’API de statut et les logs
  passent par une redaction `GCDC_…`, JWT, `ApiKey` et `Bearer`.

## Clé API ChatGPT / OpenAI

Le tunnel utilise une **clé API ChatGPT** (runtime key OpenAI) avec Tunnels
Read + Use.

- Clé : `~/.config/garmintogpt/openai-tunnel-key` (0600 best effort) ou
  `CONTROL_PLANE_API_KEY` / `OPENAI_API_KEY`.
- Tunnel ID : `~/.config/garmintogpt/openai-tunnel.json` (non secret) ou
  `CONTROL_PLANE_TUNNEL_ID`.
- La clé est passée au processus `tunnel-client` par son environnement, jamais
  dans la ligne de commande.
- La clé n’est jamais renvoyée par l’API ; seule une empreinte masquée est
  affichée.
- Une admin key (`OPENAI_ADMIN_KEY`) ne doit pas être utilisée pour le daemon.

Références :

- [Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [openai/tunnel-client](https://github.com/openai/tunnel-client)
- [Garmin Personal MCP](https://github.com/Mason-Levyy/garmin-personal-mcp)

## Tunnel OpenAI

- Connexion **sortante uniquement** vers `api.openai.com:443` ; aucun port
  entrant ni URL publique.
- Le client expose `/healthz`, `/readyz`, `/metrics` et `/ui` sur
  `127.0.0.1:8091`.
- Les requêtes et réponses MCP transitent par OpenAI. Le tunnel ne répond pas
  aux exigences « strictement local » : dans ce cas, ne l’active pas.
- Le client doit rester démarré pour les appels MCP de ChatGPT.
- Ferme le tunnel quand tu n’en as plus besoin.

## Persistance Docker

Tout l’état est dans un seul bind mount visible sur l’hôte, hors Git :

- `./garmintogpt/appdata/config/garmin` : clé Garmin + cache de jeton ;
- `./garmintogpt/appdata/config/garmintogpt` : tunnel ID + clé API ChatGPT ;
- `./garmintogpt/appdata/logs` : logs ;
- `./garmintogpt/appdata/runtime` : état, PID et binaires runtime.

Ce dossier survit aux mises à jour d’image, à la recréation du conteneur et à
`docker compose down -v`. Sauvegarde `./garmintogpt/appdata`. Aucune migration
automatique n’est effectuée.

## Fichiers ignorés

`.env`, `garmin.env`, logs, runtime, `garmintogpt/appdata`, clés, jetons,
secrets et mots de passe ne doivent jamais être versionnés. Le binaire
téléchargé est sous `runtime/bin`, donc dans `garmintogpt/appdata`.

## MCP et outils d’écriture

La Personal API est en lecture seule. Les outils d’écriture ne sont pas exposés ;
le proxy MCP ne doit exposer que les lectures.
