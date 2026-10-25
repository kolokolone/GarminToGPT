# Sécurité

Priorité : sécurité, robustesse, diagnostic, simplicité.

## Secrets Garmin

GarminToGPT ne stocke aucun mot de passe Garmin. La connexion utilise la clé
Personal API officielle, échangée contre un jeton de 24 h par
`garmin-connect-personal-api-python`.

- Clé : `~/.config/garmin/connect-personal-api-key` (0600 best effort) ou
  `GARMIN_PERSONAL_API_KEY`.
- Cache de jeton : `~/.config/garmin/connect-personal-api-bearer-token.json`.
- La clé et le jeton ne sont jamais renvoyés par l’API de statut et les logs
  passent par une redaction `GCDC_…`, JWT, `ApiKey` et `Bearer`.

## Secrets OpenAI

Le tunnel utilise une **runtime API key** OpenAI avec Tunnels Read + Use.

- Clé : `~/.config/garmintogpt/openai-tunnel-key` (0600 best effort) ou
  `CONTROL_PLANE_API_KEY` / `OPENAI_API_KEY`.
- Tunnel ID : `~/.config/garmintogpt/openai-tunnel.json` (non secret) ou
  `CONTROL_PLANE_TUNNEL_ID`.
- La clé est passée au processus `tunnel-client` par son environnement, jamais
  dans la ligne de commande.
- La clé n’est jamais renvoyée par l’API ; seule une empreinte masquée est
  affichée.
- Une admin key (`OPENAI_ADMIN_KEY`) ne doit pas être utilisée pour le daemon.

## Tunnel OpenAI

- Connexion **sortante uniquement** vers `api.openai.com:443` ; aucun port
  entrant ni URL publique.
- Le client expose `/healthz`, `/readyz`, `/metrics` et `/ui` sur
  `127.0.0.1:8091`.
- Les requêtes et réponses MCP transitent par OpenAI. Le tunnel ne répond pas
  aux exigences « strictement local » : dans ce cas, ne l’active pas.
- Le client doit rester démarré pour les appels MCP de ChatGPT.
- Ferme le tunnel quand tu n’en as plus besoin.

## Fichiers ignorés

`.env`, `garmin.env`, logs, runtime, data, clés, jetons, secrets et mots de
passe ne doivent jamais être versionnés. `runtime/bin` (binaire téléchargé) est
sous `runtime/`.

## MCP et outils d’écriture

La Personal API est en lecture seule. Les outils d’écriture de l’ancien serveur
SSO ne sont plus exposés ; le proxy MCP ne doit exposer que les lectures.
