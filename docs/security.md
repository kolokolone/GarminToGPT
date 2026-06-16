# Sécurité

Priorité : sécurité, robustesse, diagnostic, simplicité.

## Secrets

GarminToGPT ne doit jamais stocker de mot de passe Garmin. Les commandes officielles `garmin-mcp-auth` et `garmin-mcp-auth --verify` sont utilisées comme source de vérité.

Les fichiers suivants sont ignorés : `.env`, logs, runtime, data, `.garminconnect`, tokens, secrets et mots de passe.

## Tunnel Cloudflare

Un quick tunnel Cloudflare donne une URL publique. Même si l’URL est longue, elle ne doit pas être considérée comme un contrôle d’accès. Ferme le tunnel dès que ChatGPT n’en a plus besoin.

Pour un usage durable, configure un tunnel nommé et étudie Cloudflare Access si ChatGPT le supporte dans ton flux.

## MCP et outils d’écriture

Le backend classe conservativement les outils connus : `get_*` en lecture, `add_*`, `set_*`, `delete_*`, `remove_*`, `upload_*`, `schedule_*` et `unschedule_*` en écriture. Un filtrage read-only strict doit être ajouté dès que le proxy MCP choisi expose un mécanisme stable de filtrage.
