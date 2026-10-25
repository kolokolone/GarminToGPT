# Sécurité

Priorité : sécurité, robustesse, diagnostic, simplicité.

## Secrets

GarminToGPT ne stocke aucun mot de passe Garmin. La connexion utilise la clé
Personal API officielle, échangée contre un jeton de 24 h par
`garmin-connect-personal-api-python`.

- La clé est stockée dans `~/.config/garmin/connect-personal-api-key` avec des
  permissions restreintes, ou fournie par `GARMIN_PERSONAL_API_KEY`.
- Le cache de jeton officiel est dans
  `~/.config/garmin/connect-personal-api-bearer-token.json`.
- La clé et le jeton ne sont jamais renvoyés par l'API de statut, jamais
  journalisés, et les logs passent par une redaction qui couvre `GCDC_...`,
  les JWT et les en-têtes `ApiKey`/`Bearer`.
- `garmin.env` est ignoré par Git. Ne versionne jamais une clé réelle.

Les fichiers suivants sont ignorés : `.env`, `garmin.env`, logs, runtime, data,
tokens, secrets et mots de passe.

## Tunnel Cloudflare

Un quick tunnel Cloudflare donne une URL publique. Même si l’URL est longue, elle ne doit pas être considérée comme un contrôle d’accès. Ferme le tunnel dès que ChatGPT n’en a plus besoin.

Pour un usage durable, configure un tunnel nommé et étudie Cloudflare Access si ChatGPT le supporte dans ton flux.

## MCP et outils d’écriture

Le backend classe conservativement les outils connus : `get_*` en lecture, `add_*`, `set_*`, `delete_*`, `remove_*`, `upload_*`, `schedule_*` et `unschedule_*` en écriture. Un filtrage read-only strict doit être ajouté dès que le proxy MCP choisi expose un mécanisme stable de filtrage.
