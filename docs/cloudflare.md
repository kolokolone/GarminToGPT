# Cloudflare Tunnel

## Quick tunnel

Commande utilisée :

```powershell
cloudflared tunnel --url http://127.0.0.1:8080
```

Le backend lit les logs `cloudflared` et extrait l’URL `https://xxxx.trycloudflare.com`, puis construit `https://xxxx.trycloudflare.com/mcp`.

Le quick tunnel est temporaire et ne doit pas être présenté comme production.

## Tunnel nommé

Le mode `named` est prévu dans `config/app.yaml` avec `cloudflare.mode`, `tunnel_name` et `hostname`. Il est recommandé pour un usage durable.
