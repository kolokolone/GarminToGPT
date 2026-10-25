# Dépannage

## Clé API Garmin absente

Ouvre `/connexion`, crée une clé sur
[Garmin Connect → Personal API](https://connect.garmin.com/app/settings/personalApiToken),
puis colle-la. Le pont MCP et le tunnel refusent de démarrer sans clé vérifiée.

## Clé API refusée (HTTP 400, 401 ou 403)

La clé est invalide, révoquée ou expirée. Garmin ne permet pas de la renouveler
par API : crée une nouvelle clé (30/90/180/365 jours) et mets-la à jour dans
`/connexion`. L'ancienne clé reste active tant que la nouvelle n'a pas été
vérifiée.

## Rotation / date d'expiration inconnue

Garmin ne publie pas la date d'expiration de la clé. Renseigne dans
`/connexion` la date affichée sur la page Personal API. Si Garmin renvoie un
jeton valable moins de 24 h, la date est détectée automatiquement.

## Variable d'environnement prioritaire

Si `GARMIN_PERSONAL_API_KEY` est définie, elle est prioritaire sur le fichier.
L'interface ne peut pas la remplacer : retire la variable (ou mets-la à jour)
puis recharge `/connexion`.

## Token expiré

Le jeton dure 24 h et est renouvelé automatiquement une heure avant expiration.
Clique sur `Vérifier maintenant` dans `/connexion` pour forcer un nouvel échange.

## Port 8080 occupé

Le proxy MCP utilise `127.0.0.1:8080`. Arrête l’autre service ou modifie `config/app.yaml`.

## `ImportError: request_ctx` au démarrage MCP

Cette erreur indique que `mcp-proxy` a été lancé avec le SDK MCP 2.x alors que sa version
actuelle utilise encore l'API v1 `request_ctx`. La commande fournie par GarminToGPT fige
`mcp-proxy==0.12.0` et contraint son environnement à `mcp>=1.28.1,<2`. Conserve la contrainte
sur le proxy lui-même, avant l'argument exécutable `mcp-proxy`, jusqu'à la migration MCP 2.0.

## Cloudflare 1033 ou 530

Ces erreurs signalent généralement que Cloudflare ne rejoint plus le service local. Vérifie que MCP répond localement sur `/mcp`, puis régénère le tunnel.

## Tunnel expiré

Clique sur `Allumer le tunnel` ou `Regénérer le lien`. Un quick tunnel est temporaire.

## `/sse` vs `/mcp`

L’endpoint recommandé pour ChatGPT est `/mcp`. `/sse` peut exister selon les proxys, mais n’est pas recommandé par défaut.

## Docker volumes

Les volumes `config`, `logs` et `runtime` doivent être montés pour conserver la
configuration, les logs et les PID. Le volume `garmintogpt_garmin` est monté sur
`/home/app/.config/garmin` et contient la clé API ainsi que le cache de jeton.

## ChatGPT ne voit pas le connecteur

Vérifie que l’URL est HTTPS, se termine par `/mcp`, et que le tunnel Cloudflare ainsi que le proxy MCP sont actifs.
