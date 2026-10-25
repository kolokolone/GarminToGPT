# GarminToGPT

GarminToGPT est une application locale qui connecte ChatGPT à Garmin Connect via la **Personal API officielle de Garmin**, un serveur MCP local et un tunnel HTTPS Cloudflare.

Chaîne cible :

```text
Clé Personal API Garmin (GCDC_…)
  -> garmin-connect-personal-api-python (client officiel, jeton 24 h)
  -> garmin-personal-mcp
  -> mcp-proxy local
  -> Cloudflare Tunnel
  -> ChatGPT MCP Connector
```

La Personal API est **en lecture seule** : activités, sommeil, HRV, Body Battery, pas, stress, poids, nutrition, profil. Les écritures (workouts, courses, gear) de l'ancien flux SSO ne sont plus disponibles.

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
cd "C:\Users\domin\Desktop\GarminToGPT"
.\scripts\dev.ps1
```

UI : `http://127.0.0.1:3000`  
API : `http://127.0.0.1:8000`

## Lancement local buildé

Option Windows recommandée pour tester localement comme le conteneur final, avec un seul backend FastAPI qui sert aussi l’UI buildée :

```powershell
cd "C:\Users\domin\Desktop\GarminToGPT"
.\start.bat
```

Puis ouvre `http://127.0.0.1:8000`.

Option PowerShell équivalente :

```powershell
cd "C:\Users\domin\Desktop\GarminToGPT"
.\scripts\start.ps1
```

UI + API : `http://127.0.0.1:8000`

## Docker

```powershell
cd "C:\Users\domin\Desktop\GarminToGPT"
docker compose up -d
```

Le compose expose uniquement `127.0.0.1:8000`. La clé API et le cache de jeton restent hors image dans le volume `garmintogpt_garmin` monté sur `/home/app/.config/garmin`.

## Authentification Garmin (Personal API)

GarminToGPT ne demande plus de mot de passe Garmin. La connexion utilise une clé **Personal API** créée sur
[Garmin Connect → Settings → Personal API](https://connect.garmin.com/app/settings/personalApiToken).

1. Crée une clé (durée 30, 90, 180 ou 365 jours) et copie-la immédiatement : Garmin ne l'affiche qu'une fois.
2. Ouvre `http://127.0.0.1:8000/connexion` et colle la clé.
3. Clique sur `Tester et enregistrer` : GarminToGPT échange la clé contre un jeton de 24 h via le client officiel `garmin-connect-personal-api-python`, vérifie l'accès, puis enregistre la clé.
4. Clique sur `Activer l'accès ChatGPT` sur l'accueil pour lancer le proxy MCP puis Cloudflare.

La clé est stockée dans `~/.config/garmin/connect-personal-api-key` (permissions restreintes) et le cache de jeton dans `~/.config/garmin/connect-personal-api-bearer-token.json`. `GARMIN_PERSONAL_API_KEY` est prioritaire sur le fichier, comme dans le client Garmin.

Le jeton est renouvelé automatiquement une heure avant expiration. La date d'expiration de la clé n'est pas lisible via l'API : renseigne-la dans `/connexion` pour obtenir un compte à rebours exact ; elle est détectée automatiquement si Garmin renvoie un jeton de moins de 24 h.

## Tests

```powershell
.\scripts\test.ps1
```

L’UI `/tests` permet aussi de lancer les diagnostics locaux : config, dépendances, clé API, connexion Garmin, MCP, tunnel, URL ChatGPT.

## Logs

Logs attendus :

- `logs/backend.log`
- `logs/mcp.log`
- `logs/cloudflared.log`
- `logs/auth.log`
- `logs/tests.log`

Les logs affichés par l’API passent par une redaction des emails, clés `GCDC_…`, JWT, cookies, headers Authorization/ApiKey et mots de passe.

## Sécurité

- Le MCP local est configuré sur `127.0.0.1`.
- Le quick tunnel Cloudflare est temporaire, pas une solution de production.
- Tant que le tunnel est actif, l’URL publique peut exposer les outils MCP Garmin.
- La suppression de la clé API nécessite une confirmation explicite et arrête le pont MCP.
- Aucun `.env`, `garmin.env`, clé, jeton, log réel ou fichier runtime ne doit être versionné.

Voir `docs/security.md` et `docs/troubleshooting.md`.
