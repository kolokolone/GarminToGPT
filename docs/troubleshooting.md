# Dépannage

## Auth Garmin impossible

Lance la commande affichée sur `/connexion` dans un terminal local. GarminToGPT ne stocke pas le mot de passe et ne simule pas d’API si la CLI officielle est interactive.

## Token expiré

Va sur `/connexion`, relance la procédure assistée, puis clique sur `Vérifier puis démarrer`.

## Port 8080 occupé

Le proxy MCP utilise `127.0.0.1:8080`. Arrête l’autre service ou modifie `config/app.yaml`.

## Cloudflare 1033 ou 530

Ces erreurs signalent généralement que Cloudflare ne rejoint plus le service local. Vérifie que MCP répond localement sur `/mcp`, puis régénère le tunnel.

## Tunnel expiré

Clique sur `Allumer le tunnel` ou `Regénérer le lien`. Un quick tunnel est temporaire.

## `/sse` vs `/mcp`

L’endpoint recommandé pour ChatGPT est `/mcp`. `/sse` peut exister selon les proxys, mais n’est pas recommandé par défaut.

## Docker volumes

Les volumes `config`, `logs`, `runtime` et `data/garmin` doivent être montés pour conserver configuration, logs, PID et tokens Garmin hors image.

## ChatGPT ne voit pas le connecteur

Vérifie que l’URL est HTTPS, se termine par `/mcp`, et que le tunnel Cloudflare ainsi que le proxy MCP sont actifs.
