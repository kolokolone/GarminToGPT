# GarminToGPT

**Version 1.1.4**

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

Le tunnel OpenAI **ne crée aucune URL publique**. Dans ChatGPT, on choisit
`Connection: Tunnel` et le `tunnel_id` ; il n’y a pas d’URL `/mcp` à coller.

## Prérequis

- Docker Desktop.
- Une **clé API personnelle Garmin** créée sur
  [Garmin Connect → Personal API](https://connect.garmin.com/app/settings/personalApiToken).
- Un **`tunnel_id` OpenAI** créé sur
  [Platform → Tunnels](https://platform.openai.com/settings/organization/tunnels).
- Une **clé API ChatGPT** (runtime key OpenAI) avec les permissions Tunnels
  **Read + Use**, créée sur
  [Platform → Runtime API keys](https://platform.openai.com/settings/organization/api-keys).
- `tunnel-client` est téléchargé automatiquement (release OpenAI épinglée
  `v0.0.18`, vérifiée SHA-256) dans `runtime/bin`, ou fourni dans le `PATH`.
  L’image Docker l’installe au build.

Le client tunnel a besoin d’un accès sortant HTTPS vers `api.openai.com:443` et
vers le MCP local `127.0.0.1:8080`.

## Utilisation normale (Docker + ChatGPT)

C’est le parcours recommandé pour une utilisation normale.

### 1. Lancer le service dans Docker

```powershell
docker compose up -d --build
```

Ouvre `http://127.0.0.1:8000`.

Le service démarre le backend, l’UI, `mcp-proxy` et le tunnel OpenAI. Le tunnel
est **sortant** : aucun port public n’est ouvert.

### 2. Enregistrer les clés dans l’UI

1. Ouvre `http://127.0.0.1:8000/connexion`.
2. Colle la **clé API personnelle Garmin** et clique sur `Tester et enregistrer`.
3. Ouvre `http://127.0.0.1:8000/tunnel`.
4. Colle le **`tunnel_id`** et la **clé API ChatGPT**, puis clique sur
   `Tester et enregistrer`.
5. Démarre le tunnel depuis `/tunnel` (ou `Activer l'accès ChatGPT` sur
   l’accueil) et vérifie que `/readyz` est prêt. En local :
   `http://127.0.0.1:8091/readyz`. Dans Docker, consulte
   `./garmintogpt/appdata/logs/tunnel.log`.

### 3. Ajouter le serveur MCP dans ChatGPT

1. Dans ChatGPT, va dans **Plugins**, puis **Ajouter**.
2. Choisis **Ajouter un serveur MCP personnalisé**.
3. Renseigne **Nom** (par exemple `GarminToGPT`) et **Description**.
4. Sous **Connexion**, choisis **Tunnel**.
5. Sélectionne le **tunnel créé pour ce service** (le même `tunnel_id`).
6. Pour **Authentification**, choisis **Sans authentification**.
7. Garde le service Docker et le tunnel démarrés : le client reçoit les appels
   MCP et les transfère à Garmin Personal MCP.

Selon la version de ChatGPT, l’entrée peut s’appeler **Plugins** ou
**Connectors** ; le principe reste `Connection: Tunnel` + sélection du tunnel +
`Sans authentification`.

### 4. Persistance des clés

Tout l’état persistant tient dans **un seul dossier hôte**, hors Git :

- `./garmintogpt/appdata/config/garmin` : clé Garmin + cache de jeton ;
- `./garmintogpt/appdata/config/garmintogpt` : tunnel ID + clé API ChatGPT ;
- `./garmintogpt/appdata/logs` : logs ;
- `./garmintogpt/appdata/runtime` : état, PID et binaires runtime.

Ce dossier survit aux mises à jour d’image, à la recréation du conteneur et à
`docker compose down -v`. Sauvegarde `./garmintogpt/appdata` pour conserver les
clés.

L’entrypoint crée les liens nécessaires depuis les chemins par défaut de
l’application (`/app/runtime`, `/app/logs`, `~/.config/garmin`,
`~/.config/garmintogpt`) vers `/appdata`. Aucune migration automatique : si des
clés existent encore dans un ancien conteneur, copie-les une fois avant de le
supprimer :

```powershell
New-Item -ItemType Directory -Force .\garmintogpt\appdata\config\garmin, .\garmintogpt\appdata\config\garmintogpt
docker cp garmintogpt:/home/app/.config/garmin/. .\garmintogpt\appdata\config\garmin\
docker cp garmintogpt:/home/app/.config/garmintogpt/. .\garmintogpt\appdata\config\garmintogpt\
```

Puis `docker compose up -d --build`. Si le conteneur a déjà été supprimé,
ressaisis les clés une fois dans `/connexion` et `/tunnel`.

Aucune variable d’environnement n’est nécessaire. `PYTHONUNBUFFERED=1` est
défini dans l’image pour des logs non bufferisés. Les variables
`GARMIN_PERSONAL_API_KEY`, `CONTROL_PLANE_TUNNEL_ID` et
`CONTROL_PLANE_API_KEY`/`OPENAI_API_KEY` restent prioritaires sur les fichiers
si tu les ajoutes explicitement au conteneur ; dans ce cas l’UI l’indique et le
formulaire tunnel est en lecture seule.

## Clé API personnelle Garmin

GarminToGPT ne demande pas de mot de passe Garmin. La connexion utilise la clé
**Personal API** de Garmin :

1. Crée une clé sur [Garmin Connect → Settings → Personal API](https://connect.garmin.com/app/settings/personalApiToken) (durée 30, 90, 180 ou 365 jours) et copie-la immédiatement : Garmin ne l’affiche qu’une fois.
2. Ouvre `http://127.0.0.1:8000/connexion` et colle la clé.
3. Clique sur `Tester et enregistrer` : GarminToGPT échange la clé contre un jeton de 24 h via le client officiel `garmin-connect-personal-api-python`, vérifie l’accès, puis enregistre la clé.

La clé est stockée dans `~/.config/garmin/connect-personal-api-key` (permissions
restreintes) et le cache de jeton dans
`~/.config/garmin/connect-personal-api-bearer-token.json`.
`GARMIN_PERSONAL_API_KEY` est prioritaire sur le fichier, comme dans le client
Garmin.

Le jeton est renouvelé automatiquement une heure avant expiration. La date
d’expiration de la clé n’est pas lisible via l’API : renseigne-la dans
`/connexion` pour obtenir un compte à rebours exact ; elle est détectée
automatiquement si Garmin renvoie un jeton de moins de 24 h.

## Tunnel OpenAI (Secure MCP Tunnel)

La page `http://127.0.0.1:8000/tunnel` gère le tunnel :

1. Crée ou récupère un `tunnel_id` sur [Platform → Tunnels](https://platform.openai.com/settings/organization/tunnels).
2. Crée une **clé API ChatGPT** sur [Platform → Runtime API keys](https://platform.openai.com/settings/organization/api-keys) avec Tunnels **Read + Use**. N’utilise pas une admin key pour le daemon.
3. Colle le `tunnel_id` et la clé API ChatGPT dans `/tunnel`, puis clique sur `Tester et enregistrer`. La clé est vérifiée via `tunnel-client admin tunnels get` avant d’être enregistrée.
4. Démarre le tunnel depuis `/tunnel` ou via `Activer l'accès ChatGPT` sur l’accueil.

Le tunnel ID et la clé sont stockés hors dépôt dans
`~/.config/garmintogpt/openai-tunnel.json` et
`~/.config/garmintogpt/openai-tunnel-key` (0600). Les variables
`CONTROL_PLANE_TUNNEL_ID` et `CONTROL_PLANE_API_KEY` (ou `OPENAI_API_KEY`)
sont prioritaires sur les fichiers. La clé n’est jamais renvoyée par l’API.

Le client expose un healthcheck local sur `http://127.0.0.1:8091/readyz` et un
tableau de bord sur `http://127.0.0.1:8091/ui`. `mcp-proxy` reste sur
`127.0.0.1:8080/mcp` ; le tunnel l’attend jusqu’à 90 s
(`--mcp.startup-wait-timeout`) avant le premier poll OpenAI.

Aucune URL publique n’est créée ni à copier. Le parcours ChatGPT complet est
décrit dans **Utilisation normale** ci-dessus.

Liens utiles :

- [Guide Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [openai/tunnel-client](https://github.com/openai/tunnel-client)
- [Garmin Personal MCP](https://github.com/Mason-Levyy/garmin-personal-mcp)
- [Client officiel Garmin Personal API](https://github.com/garmin/connect-personal-api-python)

## Tests

L’UI `/tests` permet de lancer les diagnostics locaux : config, dépendances,
clé API Garmin, connexion Garmin, MCP, client tunnel, tunnel ID, readiness
`/readyz` et connecteur ChatGPT.

## Logs

Logs attendus dans `./garmintogpt/appdata/logs/` :

- `backend.log`
- `mcp.log`
- `tunnel.log`
- `auth.log`
- `tests.log`

Les logs affichés par l’API passent par une redaction des emails, clés
`GCDC_…`, clés API ChatGPT/OpenAI, JWT, cookies, headers Authorization/ApiKey
et mots de passe.

## Sécurité

- Le MCP local et le healthcheck du tunnel sont sur `127.0.0.1`.
- Le tunnel OpenAI est **sortant uniquement** : aucun port entrant ni URL publique n’est nécessaire.
- Les requêtes et réponses MCP transitent par OpenAI ; si tes données ne doivent pas passer par OpenAI, n’utilise pas ce tunnel.
- La clé API ChatGPT est stockée en 0600 ou fournie par variable d’environnement.
- La suppression de la configuration du tunnel nécessite une confirmation explicite et arrête le tunnel.
- `docker compose down -v` ne supprime pas `./garmintogpt/appdata` ; les clés survivent. Sauvegarde quand même ce dossier.
- Aucun `.env`, `garmin.env`, clé, jeton, log réel ou fichier runtime ne doit être versionné.

Voir `docs/openai-tunnel.md`, `docs/security.md` et `docs/troubleshooting.md`.
