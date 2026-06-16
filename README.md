# GarminToGPT

GarminToGPT est une application locale qui aide à connecter ChatGPT à Garmin Connect via `garmin-mcp`, un proxy MCP HTTP local et un tunnel HTTPS Cloudflare.

Chaîne cible :

```text
Garmin Connect -> garmin-mcp -> mcp-proxy local -> Cloudflare Tunnel -> ChatGPT MCP Connector
```

L’URL recommandée à copier dans ChatGPT est toujours l’endpoint `/mcp` :

```text
https://xxxx.trycloudflare.com/mcp
```

## Prérequis

- Windows avec PowerShell 5.1 ou 7.
- Python 3.12 pour l’usage cible.
- Node.js 24 pour le frontend.
- `uv` / `uvx`.
- `cloudflared` si tu veux ouvrir le tunnel.
- Docker Desktop si tu veux lancer l’image.

## Lancement développement

```powershell
cd "C:\Users\domin\Desktop\Garmin-MCP"
.\scripts\dev.ps1
```

UI : `http://127.0.0.1:3000`  
API : `http://127.0.0.1:8000`

## Lancement local buildé

Option Windows recommandée pour tester localement comme le conteneur final, avec un seul backend FastAPI qui sert aussi l’UI buildée :

```powershell
cd "C:\Users\domin\Desktop\Garmin-MCP"
.\start.bat
```

Puis ouvre `http://127.0.0.1:8000`.

Option PowerShell équivalente :

```powershell
cd "C:\Users\domin\Desktop\Garmin-MCP"
.\scripts\start.ps1
```

UI + API : `http://127.0.0.1:8000`

## Docker

```powershell
cd "C:\Users\domin\Desktop\Garmin-MCP"
docker compose up -d
```

Le compose expose uniquement `127.0.0.1:8000`. Les tokens Garmin restent hors image dans `./data/garmin`.

## Authentification Garmin

GarminToGPT ne stocke pas le mot de passe Garmin. Le flux `/connexion` détecte les tokens existants et affiche une procédure assistée basée sur la commande officielle :

```powershell
uvx --python 3.12 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp-auth
```

Après l’auth, clique sur `Vérifier puis démarrer` pour lancer le proxy MCP puis Cloudflare.

## Tests

```powershell
.\scripts\test.ps1
```

L’UI `/tests` permet aussi de lancer les diagnostics locaux : config, dépendances, token, MCP, tunnel, URL ChatGPT.

## Logs

Logs attendus :

- `logs/backend.log`
- `logs/mcp.log`
- `logs/cloudflared.log`
- `logs/auth.log`
- `logs/tests.log`

Les logs affichés par l’API passent par une redaction des emails, tokens, cookies, headers Authorization et mots de passe.

## Sécurité

- Le MCP local est configuré sur `127.0.0.1`.
- Le quick tunnel Cloudflare est temporaire, pas une solution de production.
- Tant que le tunnel est actif, l’URL publique peut exposer les outils MCP Garmin.
- La suppression des tokens nécessite une confirmation explicite.
- Aucun `.env`, token, log réel ou fichier runtime ne doit être versionné.

Voir `docs/security.md` et `docs/troubleshooting.md`.
