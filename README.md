# GarminToGPT

**Version 1.1.1**

GarminToGPT est une application locale qui connecte ChatGPT à Garmin Connect avec :

- **[Garmin Personal MCP](https://github.com/Mason-Levyy/garmin-personal-mcp)**, un serveur MCP construit sur la **Personal API officielle de Garmin** ([client officiel](https://github.com/garmin/connect-personal-api-python)) ;
- une **clé API personnelle Garmin** (`GCDC_…`) ;
- le **[Secure MCP Tunnel d’OpenAI](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)** via [`openai/tunnel-client`](https://github.com/openai/tunnel-client), avec un `tunnel_id` et une **clé API ChatGPT** (runtime key OpenAI).

Chaîne cible :

```text
Clé API personnelle Garmin (GCDC_…)
  -> garmin-connect-personal-api-python (client officiel, jeton 24 h)
  -> Garmin Personal MCP (garmin-personal-mcp, lecture seule)
  -> mcp-proxy local 127.0.0.1:8080/mcp
  -> openai/tunnel-client (connexion sortante)
  -> OpenAI Secure MCP Tunnel
  -> ChatGPT (Connection: Tunnel)
```

La Personal API est **en lecture seule** : activités, sommeil, HRV, Body Battery, pas, stress, poids, nutrition, profil. Les écritures (workouts, courses, gear) ne sont pas disponibles.

Le tunnel OpenAI **ne crée aucune URL publique**. Dans ChatGPT, ouvre
`Settings → Connectors`, choisis `Connection: Tunnel`, puis sélectionne le tunnel ou colle son `tunnel_id`.

## Prérequis

- Windows avec PowerShell 5.1 ou 7, ou Linux.
- Python 3.12 pour l’usage cible.
- Node.js 24 pour le frontend.
- `uv` / `uvx`.
- Une **clé API personnelle Garmin** créée sur
  [Garmin Connect → Personal API](https://connect.garmin.com/app/settings/personalApiToken).
- Un **`tunnel_id` OpenAI** créé sur
  [Platform → Tunnels](https://platform.openai.com/settings/organization/tunnels).
- Une **clé API ChatGPT** (runtime key OpenAI) avec les permissions Tunnels
  **Read + Use**, créée sur
  [Platform → Runtime API keys](https://platform.openai.com/settings/organization/api-keys).
- `tunnel-client` : téléchargé automatiquement (release OpenAI épinglée `v0.0.18`, vérifiée SHA-256) dans `runtime/bin`, ou binaire fourni dans le `PATH`.
- Docker Desktop si tu veux lancer l’image.

Le client tunnel a besoin d’un accès sortant HTTPS vers `api.openai.com:443` et vers le MCP local `127.0.0.1:8080`.

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

Le compose expose uniquement `127.0.0.1:8000`. La configuration Garmin est conservée dans le volume `garmintogpt_garmin` (`/home/app/.config/garmin`) et la configuration du tunnel OpenAI dans `garmintogpt_openai` (`/home/app/.config/garmintogpt`). Aucun port public n’est ouvert pour le tunnel : le client se connecte en sortie vers OpenAI.

## Clé API personnelle Garmin

GarminToGPT ne demande pas de mot de passe Garmin. La connexion utilise la clé **Personal API** de Garmin :

1. Crée une clé sur [Garmin Connect → Settings → Personal API](https://connect.garmin.com/app/settings/personalApiToken) (durée 30, 90, 180 ou 365 jours) et copie-la immédiatement : Garmin ne l’affiche qu’une fois.
2. Ouvre `http://127.0.0.1:8000/connexion` et colle la clé.
3. Clique sur `Tester et enregistrer` : GarminToGPT échange la clé contre un jeton de 24 h via le client officiel `garmin-connect-personal-api-python`, vérifie l’accès, puis enregistre la clé.
4. Clique sur `Activer l'accès ChatGPT` sur l’accueil pour lancer le proxy MCP puis le tunnel OpenAI.

La clé est stockée dans `~/.config/garmin/connect-personal-api-key` (permissions restreintes) et le cache de jeton dans `~/.config/garmin/connect-personal-api-bearer-token.json`. `GARMIN_PERSONAL_API_KEY` est prioritaire sur le fichier, comme dans le client Garmin.

Le jeton est renouvelé automatiquement une heure avant expiration. La date d’expiration de la clé n’est pas lisible via l’API : renseigne-la dans `/connexion` pour obtenir un compte à rebours exact ; elle est détectée automatiquement si Garmin renvoie un jeton de moins de 24 h.

## Tunnel OpenAI (Secure MCP Tunnel)

La page `http://127.0.0.1:8000/tunnel` gère le tunnel :

1. Crée ou récupère un `tunnel_id` sur [Platform → Tunnels](https://platform.openai.com/settings/organization/tunnels).
2. Crée une **clé API ChatGPT** sur [Platform → Runtime API keys](https://platform.openai.com/settings/organization/api-keys) avec Tunnels **Read + Use**. N’utilise pas une admin key pour le daemon.
3. Colle le `tunnel_id` et la clé API ChatGPT dans `/tunnel`, puis clique sur `Tester et enregistrer`. La clé est vérifiée via `tunnel-client admin tunnels get` avant d’être enregistrée.
4. Démarre le tunnel depuis `/tunnel` ou via `Activer l'accès ChatGPT` sur l’accueil.
5. Dans ChatGPT → Settings → Connectors → `Connection: Tunnel`, sélectionne le tunnel ou colle son ID. Garde le client démarré.

Le tunnel ID et la clé sont stockés hors dépôt dans
`~/.config/garmintogpt/openai-tunnel.json` et
`~/.config/garmintogpt/openai-tunnel-key` (0600). Les variables
`CONTROL_PLANE_TUNNEL_ID` et `CONTROL_PLANE_API_KEY` (ou `OPENAI_API_KEY`)
sont prioritaires sur les fichiers. La clé n’est jamais renvoyée par l’API.

Le client expose un healthcheck local sur `http://127.0.0.1:8091/readyz` et un tableau de bord sur `http://127.0.0.1:8091/ui`. `mcp-proxy` reste sur `127.0.0.1:8080/mcp` ; le tunnel l’attend jusqu’à 90 s (`--mcp.startup-wait-timeout`) avant le premier poll OpenAI.

Aucune URL publique n’est créée ni à copier.

Liens utiles :

- [Guide Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [openai/tunnel-client](https://github.com/openai/tunnel-client)
- [Garmin Personal MCP](https://github.com/Mason-Levyy/garmin-personal-mcp)
- [Client officiel Garmin Personal API](https://github.com/garmin/connect-personal-api-python)

## Tests

```powershell
.\scripts\test.ps1
```

L’UI `/tests` permet aussi de lancer les diagnostics locaux : config, dépendances, clé API Garmin, connexion Garmin, MCP, client tunnel, tunnel ID, readiness `/readyz` et connecteur ChatGPT.

## Logs

Logs attendus :

- `logs/backend.log`
- `logs/mcp.log`
- `logs/tunnel.log`
- `logs/auth.log`
- `logs/tests.log`

Les logs affichés par l’API passent par une redaction des emails, clés `GCDC_…`, clés API ChatGPT/OpenAI, JWT, cookies, headers Authorization/ApiKey et mots de passe.

## Sécurité

- Le MCP local et le healthcheck du tunnel sont sur `127.0.0.1`.
- Le tunnel OpenAI est **sortant uniquement** : aucun port entrant ni URL publique n’est nécessaire.
- Les requêtes et réponses MCP transitent par OpenAI ; si tes données ne doivent pas passer par OpenAI, n’utilise pas ce tunnel.
- La clé API ChatGPT est stockée en 0600 ou fournie par variable d’environnement.
- La suppression de la configuration du tunnel nécessite une confirmation explicite et arrête le tunnel.
- Aucun `.env`, `garmin.env`, clé, jeton, log réel ou fichier runtime ne doit être versionné.

Voir `docs/openai-tunnel.md`, `docs/security.md` et `docs/troubleshooting.md`.
