# Spécification fonctionnelle et technique — GarminToGPT

## 1. Objectif général

Créer une application locale complète nommée **GarminToGPT** permettant de connecter proprement ChatGPT à un serveur `garmin-mcp` exécuté sur le PC de l’utilisateur.

L’application doit fournir une interface web locale simple, lisible et robuste pour gérer l’authentification Garmin, vérifier l’état des tokens Garmin, démarrer et arrêter le serveur MCP local, démarrer et arrêter le tunnel Cloudflare, afficher l’URL publique HTTPS à copier dans ChatGPT, visualiser les logs, lancer des tests de santé locaux et distants, et diagnostiquer rapidement les erreurs courantes.

L’objectif n’est pas de produire un simple script de démarrage. L’objectif est de construire une vraie application locale, maintenable, conteneurisée, testée, documentée et prête à être versionnée.

Le projet doit être pensé pour un développeur full-stack expérimenté, avec une architecture claire, une séparation stricte entre frontend, backend, services système, orchestration, configuration, tests et documentation.

---

## 2. Nom du projet

Nom applicatif : **GarminToGPT**

Nom recommandé du dépôt : `garmintogpt`

Dossier de travail local obligatoire :

```text
C:\Users\domin\Desktop\Garmin-MCP
```

---

## 3. Problème à résoudre

ChatGPT peut utiliser un connecteur MCP personnalisé, mais il lui faut une URL HTTPS accessible publiquement.

Or `garmin-mcp` fonctionne localement, typiquement en MCP stdio. Il faut donc lancer `garmin-mcp` localement, exposer ce serveur via un proxy MCP HTTP, rendre le service accessible en HTTPS via Cloudflare Tunnel, puis fournir à ChatGPT une URL de type :

```text
https://xxxx.trycloudflare.com/mcp
```

ou, en mode tunnel nommé :

```text
https://garmin.example.com/mcp
```

L’application doit automatiser et superviser cette chaîne.

---

## 4. Contraintes principales

### 4.1 Sécurité

L’application manipule indirectement des données Garmin personnelles. Elle doit appliquer des règles strictes.

Elle ne doit jamais stocker le mot de passe Garmin en clair, ne jamais stocker l’email et le mot de passe Garmin dans un fichier versionné, ne jamais logger les credentials, ne jamais logger les tokens Garmin, et ne jamais commiter les tokens, logs, fichiers runtime, fichiers `.env` ou secrets.

Le serveur local ne doit jamais écouter sur `0.0.0.0`. Il doit écouter uniquement sur `127.0.0.1`.

L’interface doit afficher clairement que l’URL publique Cloudflare donne accès aux outils MCP exposés tant que le tunnel est ouvert. Elle doit recommander de ne pas laisser le tunnel actif inutilement.

Si techniquement possible, l’application doit proposer un mode lecture seule ou, au minimum, documenter les outils MCP capables d’écrire ou modifier des données Garmin.

Toute suppression de token Garmin doit nécessiter une confirmation explicite.

### 4.2 Robustesse

L’application doit éviter les mécanismes fragiles. Elle ne doit pas utiliser de `Start-Sleep` arbitraire comme mécanisme principal d’attente. Elle doit utiliser des healthchecks réels, des timeouts explicites, une gestion propre des PID, des logs structurés, des erreurs utilisateur compréhensibles, un redémarrage idempotent, une détection du port occupé, une détection des processus orphelins et une récupération propre après crash.

### 4.3 Performance

L’application doit démarrer rapidement. Elle ne doit pas réinstaller les dépendances à chaque lancement, ne doit pas relancer l’auth Garmin si les tokens sont valides, doit limiter les polling inutiles, garder une UI fluide, et utiliser des endpoints backend rapides.

---

## 5. Stack technique attendue

### 5.1 Frontend

Stack recommandée :

- Next.js ;
- React ;
- TypeScript ;
- Tailwind CSS ou CSS modules ;
- composants UI simples, sans dépendance lourde inutile ;
- design sobre, clair, centré sur l’état opérationnel.

Pages requises :

- `/connexion` ;
- `/` ;
- `/tests`.

### 5.2 Backend

Stack recommandée :

- FastAPI ;
- Python 3.12 ;
- Pydantic ;
- Uvicorn ;
- orchestration propre des processus via `asyncio` ou `subprocess`.

Le backend doit piloter l’authentification Garmin, la vérification des tokens, le serveur `garmin-mcp`, le proxy MCP HTTP, le tunnel Cloudflare, les logs, les tests et les statuts.

### 5.3 MCP et Garmin

Commande cible pour lancer Garmin MCP :

```bash
uvx --python 3.12 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp
```

Commande cible pour auth Garmin :

```bash
uvx --python 3.12 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp-auth
```

Commande cible pour vérification auth :

```bash
uvx --python 3.12 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp-auth --verify
```

Le backend doit permettre de lancer ces commandes sans exposer les credentials dans les logs.

### 5.4 Proxy MCP

L’application doit utiliser un proxy MCP capable d’exposer `garmin-mcp` en HTTP MCP / Streamable HTTP.

Option recommandée : `mcp-proxy`.

Le service local doit exposer :

```text
http://127.0.0.1:8080/mcp
```

L’endpoint `/mcp` doit être considéré comme l’endpoint recommandé pour ChatGPT. L’endpoint `/sse` peut exister mais ne doit pas être prioritaire.

### 5.5 Cloudflare Tunnel

Le backend doit pouvoir gérer `cloudflared`.

Deux modes doivent être prévus.

Mode quick tunnel :

```bash
cloudflared tunnel --url http://127.0.0.1:8080
```

Ce mode retourne une URL du type :

```text
https://xxxx.trycloudflare.com
```

L’application doit automatiquement afficher l’URL finale :

```text
https://xxxx.trycloudflare.com/mcp
```

Mode named tunnel :

- tunnel Cloudflare nommé ;
- domaine personnel ;
- configuration persistante ;
- meilleure stabilité ;
- meilleure traçabilité.

Ce mode doit être prévu dans la configuration même s’il n’est pas activé au premier lancement.

---

## 6. Architecture applicative cible

Architecture logique :

```text
Utilisateur
  ↓
Page locale Next.js
  ↓
API FastAPI locale
  ↓
Service Manager
  ├── Garmin Auth Manager
  ├── MCP Proxy Manager
  ├── Cloudflare Tunnel Manager
  ├── Log Manager
  ├── Healthcheck Manager
  └── Test Runner
        ↓
  garmin-mcp + mcp-proxy + cloudflared
        ↓
URL HTTPS publique
        ↓
ChatGPT MCP Connector
```

Le frontend ne doit pas piloter directement les processus système. Il doit uniquement appeler le backend. Le backend est responsable des processus, des PID, des logs, des tests, des fichiers runtime, de la configuration et de la sécurité locale.

---

## 7. Arborescence recommandée

```text
Garmin-MCP/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── package.json
├── pnpm-lock.yaml
├── uv.lock
├── Makefile
├── config/
│   ├── app.example.yaml
│   └── app.yaml
├── docs/
│   ├── architecture.md
│   ├── security.md
│   ├── troubleshooting.md
│   ├── mcp-chatgpt.md
│   └── cloudflare.md
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── connexion/
│   │   │   └── page.tsx
│   │   └── tests/
│   │       └── page.tsx
│   ├── components/
│   │   ├── AppHeader.tsx
│   │   ├── StatusBadge.tsx
│   │   ├── TunnelCard.tsx
│   │   ├── ServiceStatusCard.tsx
│   │   ├── LogsModal.tsx
│   │   ├── ConfirmDialog.tsx
│   │   ├── LoadingButton.tsx
│   │   └── TestCard.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   ├── types.ts
│   │   └── format.ts
│   └── styles/
│       └── globals.css
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── paths.py
│   │   │   ├── logging.py
│   │   │   └── security.py
│   │   ├── api/
│   │   │   ├── routes_auth.py
│   │   │   ├── routes_status.py
│   │   │   ├── routes_tunnel.py
│   │   │   ├── routes_mcp.py
│   │   │   ├── routes_logs.py
│   │   │   └── routes_tests.py
│   │   ├── models/
│   │   │   ├── auth.py
│   │   │   ├── status.py
│   │   │   ├── tunnel.py
│   │   │   ├── logs.py
│   │   │   └── tests.py
│   │   ├── services/
│   │   │   ├── process_manager.py
│   │   │   ├── garmin_auth_service.py
│   │   │   ├── mcp_service.py
│   │   │   ├── tunnel_service.py
│   │   │   ├── log_service.py
│   │   │   ├── healthcheck_service.py
│   │   │   └── test_service.py
│   │   └── utils/
│   │       ├── command.py
│   │       ├── ports.py
│   │       ├── redact.py
│   │       └── time.py
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── smoke/
├── scripts/
│   ├── dev.ps1
│   ├── start.ps1
│   ├── stop.ps1
│   ├── status.ps1
│   ├── test.ps1
│   └── publish-image.ps1
├── runtime/
│   └── .gitkeep
├── logs/
│   └── .gitkeep
└── .github/
    └── workflows/
        ├── ci.yml
        ├── docker-build.yml
        ├── docker-publish-ghcr.yml
        └── release.yml
```

---

## 8. Configuration

Créer `config/app.yaml` :

```yaml
app:
  name: GarminToGPT
  version: 0.1.0
  environment: local

server:
  host: 127.0.0.1
  backend_port: 8000
  frontend_port: 3000

mcp:
  host: 127.0.0.1
  port: 8080
  endpoint: /mcp
  sse_endpoint: /sse
  command:
    - uvx
    - --python
    - "3.12"
    - --from
    - git+https://github.com/Taxuspt/garmin_mcp
    - garmin-mcp

garmin:
  auth_command:
    - uvx
    - --python
    - "3.12"
    - --from
    - git+https://github.com/Taxuspt/garmin_mcp
    - garmin-mcp-auth
  verify_command:
    - uvx
    - --python
    - "3.12"
    - --from
    - git+https://github.com/Taxuspt/garmin_mcp
    - garmin-mcp-auth
    - --verify
  token_dir: "%USERPROFILE%\.garminconnect"

cloudflare:
  mode: quick
  local_url: http://127.0.0.1:8080
  tunnel_name: ""
  hostname: ""
  command: cloudflared

runtime:
  dir: runtime
  pid_dir: runtime/pids
  state_file: runtime/state.json

logs:
  dir: logs
  max_size_mb: 10
  retain_files: 5

security:
  bind_local_only: true
  redact_sensitive_logs: true
  allow_write_tools: false

timeouts:
  process_start_seconds: 45
  process_stop_seconds: 15
  healthcheck_seconds: 10
```

Créer `.env.example` :

```env
GARMINTOGPT_ENV=local
GARMINTOGPT_CONFIG=config/app.yaml
GARMINTOGPT_LOG_LEVEL=INFO
```

Aucun secret Garmin ne doit être mis dans `.env`.

---

## 9. Services backend attendus

### 9.1 Garmin Auth Service

Responsabilités :

- détecter si un token Garmin existe ;
- vérifier si le token est valide ;
- lancer l’auth Garmin ;
- gérer le code de confirmation si la CLI le permet ;
- lancer une réauthentification ;
- supprimer les tokens Garmin sur demande explicite ;
- retourner la date de dernière connexion valide.

Fonctions attendues :

```python
has_garmin_token() -> bool
verify_garmin_auth() -> GarminAuthStatus
start_garmin_auth(email: str | None, password: str | None, otp: str | None) -> GarminAuthResult
reauthenticate() -> GarminAuthResult
disconnect_garmin(confirm: bool) -> DisconnectResult
get_last_successful_auth_date() -> datetime | None
```

Si `garmin-mcp-auth` ne permet pas proprement l’authentification non interactive par API, il faut le documenter. Dans ce cas, l’interface doit afficher une procédure assistée, sans stocker le mot de passe.

### 9.2 MCP Service

Responsabilités :

- lancer le proxy MCP ;
- arrêter le proxy MCP ;
- vérifier l’état local ;
- vérifier l’endpoint `/mcp` ;
- lister les outils MCP disponibles ;
- détecter les outils de lecture et d’écriture ;
- remonter les erreurs.

Fonctions attendues :

```python
start_mcp_service() -> ServiceActionResult
stop_mcp_service() -> ServiceActionResult
restart_mcp_service() -> ServiceActionResult
get_mcp_status() -> McpStatus
healthcheck_mcp() -> HealthcheckResult
list_mcp_tools() -> McpToolsResult
classify_mcp_tools() -> McpToolClassification
```

### 9.3 Cloudflare Tunnel Service

Responsabilités :

- lancer le tunnel ;
- arrêter le tunnel ;
- mettre en pause le tunnel ;
- reprendre le tunnel ;
- récupérer l’URL publique ;
- générer l’URL finale `/mcp` ;
- détecter les erreurs Cloudflare ;
- supporter quick tunnel et named tunnel.

Fonctions attendues :

```python
start_tunnel() -> TunnelActionResult
stop_tunnel() -> TunnelActionResult
pause_tunnel() -> TunnelActionResult
resume_tunnel() -> TunnelActionResult
get_tunnel_status() -> TunnelStatus
get_public_url() -> str | None
get_chatgpt_mcp_url() -> str | None
parse_cloudflared_logs_for_url() -> str | None
```

États possibles :

```text
running
stopped
starting
paused
error
unknown
```

### 9.4 Log Service

Responsabilités :

- retourner les logs MCP ;
- retourner les logs Cloudflare ;
- retourner les logs backend ;
- masquer les secrets ;
- limiter la taille des réponses ;
- supporter pagination ou tail.

Endpoints :

```http
GET /api/logs/backend
GET /api/logs/mcp
GET /api/logs/cloudflare
GET /api/logs/{service}?lines=200
```

### 9.5 Test Service

Tests attendus :

1. `check_config`
2. `check_dependencies`
3. `check_garmin_token_exists`
4. `check_garmin_auth_valid`
5. `check_mcp_process`
6. `check_mcp_port`
7. `check_mcp_endpoint`
8. `check_mcp_tools_list`
9. `check_cloudflared_available`
10. `check_tunnel_process`
11. `check_tunnel_public_url`
12. `check_remote_mcp_endpoint`
13. `check_chatgpt_url_format`
14. `full_smoke_test`

Endpoints :

```http
GET /api/tests
POST /api/tests/{test_id}/run
POST /api/tests/run-all
```

---

## 10. Endpoints API attendus

Auth :

```http
GET /api/auth/status
POST /api/auth/login
POST /api/auth/verify
POST /api/auth/reauthenticate
POST /api/auth/disconnect
```

MCP :

```http
GET /api/mcp/status
POST /api/mcp/start
POST /api/mcp/stop
POST /api/mcp/restart
GET /api/mcp/tools
```

Cloudflare :

```http
GET /api/tunnel/status
POST /api/tunnel/start
POST /api/tunnel/stop
POST /api/tunnel/pause
POST /api/tunnel/resume
GET /api/tunnel/url
```

Logs :

```http
GET /api/logs/backend
GET /api/logs/mcp
GET /api/logs/cloudflare
```

Tests :

```http
GET /api/tests
POST /api/tests/{id}/run
POST /api/tests/run-all
```

Statut global :

```http
GET /api/status
```

---

## 11. Interface graphique

Le design doit rester simple, local, rapide et user friendly.

Principes UI :

- typographie lisible ;
- fond clair ou gris très léger ;
- cartes centrées ;
- bordures fines ;
- coins légèrement arrondis ;
- espacements réguliers ;
- pastilles de statut claires ;
- boutons explicites ;
- messages d’erreur précis ;
- hiérarchie visuelle nette.

---

## 12. Page `/connexion`

Cette page est affichée au premier lancement si aucun token Garmin valide n’est détecté.

Afficher :

- titre : `GarminToGPT` ;
- sous-titre : `Connecte ton compte Garmin à ChatGPT via un pont MCP local sécurisé.` ;
- texte explicatif : `L'application lance Garmin MCP localement, expose un endpoint MCP via Cloudflare Tunnel, puis fournit une URL HTTPS à utiliser dans ChatGPT.` ;
- formulaire de connexion :
  - email ;
  - mot de passe ;
  - code de confirmation / OTP si demandé ;
- bouton principal : `Se connecter à Garmin` ;
- rond de chargement pendant l’authentification ;
- message d’erreur si échec ;
- message de succès si connexion validée ;
- détection automatique de token existant.

Comportement :

1. appeler `GET /api/auth/status` au chargement ;
2. si un token valide existe, rediriger vers `/` ;
3. sinon afficher le formulaire ;
4. après succès, lancer MCP local, lancer tunnel Cloudflare, puis rediriger vers `/`.

Le mot de passe ne doit pas être stocké côté frontend. Le backend ne doit pas l’écrire dans les logs. Si la CLI `garmin-mcp-auth` ne permet pas une authentification non interactive fiable, il faut afficher une procédure assistée plutôt que bricoler une saisie fragile.

---

## 13. Page principale `/`

Afficher :

- titre : `GarminToGPT` ;
- sous-titre : `Pont local entre Garmin Connect, garmin-mcp et ChatGPT.` ;
- version de l’application dans un coin discret ;
- état global.

### Carte principale : URL Cloudflare

Afficher au centre :

- label : `URL MCP pour ChatGPT` ;
- URL complète : `https://xxxx.trycloudflare.com/mcp` ;
- bouton `Copier` ;
- message `Copié` après copie ;
- pastille verte si tunnel ouvert ;
- pastille rouge si tunnel fermé ;
- pastille orange si tunnel en démarrage ;
- bouton `Éteindre le tunnel` si tunnel ouvert ;
- bouton `Allumer le tunnel` si tunnel fermé ;
- bouton `Regénérer le lien` si tunnel quick actif ;
- indication : `Colle cette URL dans le connecteur MCP personnalisé de ChatGPT.`

### Section service local

Carte : `Service local`

Afficher :

- état du backend ;
- état du proxy MCP ;
- port local ;
- endpoint local ;
- PID si disponible ;
- dernier healthcheck ;
- bouton `Afficher les logs` ;
- bouton `Redémarrer le service local`.

### Section Garmin MCP

Carte : `Garmin MCP`

Afficher :

- état de connexion Garmin ;
- présence de token ;
- validité du token ;
- date de dernière connexion ;
- bouton `Réauthentifier` ;
- bouton `Déconnexion` ;
- bouton `Afficher les logs`.

Déconnexion :

Afficher une boîte de confirmation :

```text
Voulez-vous vraiment vous déconnecter ? Les tokens Garmin locaux seront supprimés.
```

### Section Cloudflare

Carte : `Cloudflare Tunnel`

Afficher :

- état du tunnel ;
- mode quick ou named ;
- PID ;
- URL publique brute ;
- URL finale `/mcp` ;
- dernier événement ;
- bouton `Afficher les logs` ;
- bouton `Pause` ;
- bouton `Reprendre` ;
- bouton `Arrêter`.

Afficher un bouton `Tests` qui mène vers `/tests`.

---

## 14. Page `/tests`

Afficher :

- bouton retour vers `/` ;
- titre : `Tests GarminToGPT` ;
- sous-titre : `Vérifie la configuration, Garmin MCP, le tunnel Cloudflare et l’endpoint ChatGPT.` ;
- bouton `Lancer tous les tests` ;
- liste de cartes de tests.

Pour chaque test :

- nom ;
- description courte ;
- bouton `Lancer` ;
- état : non lancé, en cours, succès, échec ;
- durée ;
- message de résultat ;
- raison de l’échec ;
- suggestion corrective.

Tests minimum :

1. Configuration chargée
2. Dépendances disponibles
3. Token Garmin détecté
4. Auth Garmin valide
5. Process MCP actif
6. Port local MCP ouvert
7. Endpoint local `/mcp`
8. Liste des outils MCP
9. Cloudflared disponible
10. Tunnel Cloudflare actif
11. URL publique détectée
12. Endpoint distant `/mcp`
13. Format URL ChatGPT valide
14. Smoke test complet

---

## 15. Docker

L’application doit pouvoir tourner dans un conteneur Docker unique, construit avec une image multistage.

Le conteneur doit embarquer :

- frontend Next.js buildé ;
- backend FastAPI ;
- runtime Python ;
- dépendances nécessaires ;
- `uv` ;
- `mcp-proxy` ;
- `cloudflared`, si possible ;
- scripts d’entrée ;
- healthcheck.

Les tokens Garmin doivent persister hors du conteneur via volumes :

```text
./data/garmin:/home/app/.garminconnect
./logs:/app/logs
./runtime:/app/runtime
./config:/app/config
```

Dockerfile multistage attendu :

```dockerfile
FROM node:22-alpine AS frontend-deps
FROM node:22-alpine AS frontend-build
FROM python:3.12-slim AS backend-deps
FROM python:3.12-slim AS runtime
```

Pour une application locale simple, préférer un frontend statique servi par FastAPI si possible.

---

## 16. Docker Compose

Créer `docker-compose.yml` :

```yaml
services:
  garmintogpt:
    image: ghcr.io/OWNER/garmintogpt:latest
    container_name: garmintogpt
    ports:
      - "3000:3000"
      - "8000:8000"
      - "8080:8080"
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./runtime:/app/runtime
      - ./data/garmin:/home/app/.garminconnect
    environment:
      - GARMINTOGPT_ENV=local
      - GARMINTOGPT_CONFIG=/app/config/app.yaml
    restart: unless-stopped
```

Si l’architecture finale sert tout via un seul port, préférer un seul mapping de port et documenter clairement les ports internes.

---

## 17. Publication GHCR

Publier automatiquement l’image Docker sur GitHub Container Registry.

Images attendues :

```text
ghcr.io/<owner>/garmintogpt:latest
ghcr.io/<owner>/garmintogpt:<version>
```

Créer `.github/workflows/docker-publish-ghcr.yml`.

Le workflow doit :

- se lancer sur push sur `main` ;
- se lancer sur tag `v*` ;
- construire l’image Docker ;
- utiliser le cache Docker Buildx ;
- se connecter à GHCR ;
- publier `latest` sur `main` ;
- publier une version semver sur tag.

Permissions :

```yaml
permissions:
  contents: read
  packages: write
```

---

## 18. GitHub Actions CI

Créer `.github/workflows/ci.yml`.

Il doit exécuter :

Frontend :

- install ;
- lint ;
- typecheck ;
- tests.

Backend :

- install ;
- ruff ;
- mypy si configuré ;
- pytest.

Docker :

- build de validation sans publication.

Smoke tests :

- démarrage backend ;
- appel `/api/status` ;
- vérification que l’application répond.

---

## 19. Tests

### Backend

Utiliser `pytest`.

Tests unitaires :

- parsing config ;
- gestion paths ;
- redaction secrets logs ;
- extraction URL Cloudflare depuis logs ;
- gestion PID ;
- détection port ;
- classification outils MCP ;
- construction URL ChatGPT.

Tests intégration :

- endpoint `/api/status` ;
- endpoint `/api/auth/status` ;
- endpoint `/api/tunnel/status` ;
- endpoint `/api/tests` ;
- simulation process manager avec mocks.

Smoke tests :

- backend démarre ;
- frontend buildé accessible ;
- `/api/status` répond ;
- `/tests` charge ;
- configuration par défaut valide.

### Frontend

Utiliser Vitest ou Jest avec Testing Library.

Tester :

- rendu page `/connexion` ;
- rendu page `/` ;
- rendu page `/tests` ;
- bouton copier ;
- affichage des pastilles ;
- modale logs ;
- modale confirmation déconnexion ;
- état loading ;
- affichage erreur API.

### End-to-end optionnel

Utiliser Playwright.

Scénarios :

1. premier lancement sans token ;
2. affichage page connexion ;
3. simulation token valide ;
4. redirection page principale ;
5. affichage URL tunnel ;
6. lancement page tests ;
7. exécution test mocké.

---

## 20. Sécurité et secrets

Créer un `.gitignore` strict :

```gitignore
.env
.env.*
!.env.example

logs/
runtime/
data/
*.log
*.pid
*.tmp

.garminconnect/
*garminconnect*
*tokens*
*secret*
*password*

__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
node_modules/
.next/
dist/
build/
coverage/

.DS_Store
Thumbs.db
```

Toute sortie de commande doit passer par un filtre de redaction.

Masquer :

- email ;
- mot de passe ;
- tokens ;
- cookies ;
- headers Authorization ;
- URLs avec tokens ;
- chemins contenant des secrets si nécessaire.

Actions nécessitant confirmation :

- suppression tokens Garmin ;
- arrêt tunnel ;
- régénération tunnel ;
- suppression logs ;
- reset complet.

---

## 21. Logs

Prévoir :

```text
logs/backend.log
logs/mcp.log
logs/cloudflared.log
logs/auth.log
logs/tests.log
```

Format recommandé :

```text
2026-06-16T12:00:00Z INFO service=mcp event=start message="MCP service started" pid=1234
```

La page doit afficher les logs dans une modale avec police monospace, bouton copier, bouton rafraîchir, bouton fermer, choix du nombre de lignes, et absence de secrets visibles.

---

## 22. États applicatifs

État global :

```text
not_configured
needs_auth
ready
degraded
error
```

État Garmin :

```text
unknown
no_token
token_found
connected
auth_invalid
reauth_required
error
```

État MCP :

```text
stopped
starting
running
unhealthy
error
```

État Cloudflare :

```text
stopped
starting
running
paused
expired
error
```

---

## 23. Gestion des erreurs

Chaque erreur doit être traduite en message utilisateur.

Exemples :

Garmin auth échoue :

```text
Connexion Garmin refusée. Vérifie l’email, le mot de passe ou le code de confirmation.
```

Token expiré :

```text
Le token Garmin existe mais n’est plus valide. Lance une réauthentification.
```

Port MCP occupé :

```text
Le port 8080 est déjà utilisé. Vérifie si GarminToGPT est déjà lancé ou change le port dans la configuration.
```

Tunnel expiré :

```text
Le tunnel Cloudflare temporaire n’est plus actif. Clique sur “Allumer le tunnel” pour générer un nouveau lien.
```

Endpoint distant inaccessible :

```text
L’URL publique ne répond pas sur /mcp. Vérifie que le tunnel est ouvert et que le service local fonctionne.
```

---

## 24. Documentation attendue

Créer :

- `README.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/troubleshooting.md`
- `docs/mcp-chatgpt.md`
- `docs/cloudflare.md`

Le README doit expliquer l’installation locale, le démarrage Docker, l’auth Garmin, le lancement du tunnel, l’ajout dans ChatGPT, les tests, les logs, la sécurité et le dépannage rapide.

---

## 25. Scripts attendus

Créer :

```text
scripts/dev.ps1
scripts/start.ps1
scripts/stop.ps1
scripts/status.ps1
scripts/test.ps1
```

`dev.ps1` lance frontend et backend en mode dev.

`start.ps1` lance l’application localement et affiche l’URL locale UI.

`stop.ps1` arrête proprement backend, frontend, MCP et Cloudflare.

`status.ps1` appelle `/api/status` si backend actif, sinon inspecte les PID.

`test.ps1` lance tests frontend, backend et smoke tests.

---

## 26. Critères d’acceptation

Le projet est accepté si :

1. le dépôt est proprement organisé ;
2. l’application démarre localement ;
3. Docker build fonctionne ;
4. Docker Compose démarre l’application ;
5. l’UI `/connexion` fonctionne ;
6. l’UI `/` affiche les statuts ;
7. l’UI `/tests` affiche les tests ;
8. l’auth Garmin peut être lancée ou guidée ;
9. les tokens Garmin sont détectés automatiquement ;
10. le service MCP local peut être lancé ;
11. l’endpoint local `/mcp` est testé ;
12. le tunnel Cloudflare peut être lancé ;
13. l’URL publique `/mcp` est affichée ;
14. l’URL peut être copiée ;
15. les logs sont consultables ;
16. les tests peuvent être lancés depuis l’UI ;
17. les erreurs sont compréhensibles ;
18. aucun secret n’est versionné ;
19. GHCR peut publier l’image ;
20. GitHub Actions exécute CI + build Docker.

---

## 27. Commandes attendues

Développement local :

```powershell
cd "C:\Users\domin\Desktop\Garmin-MCP"
.\scripts\dev.ps1
```

Lancement local :

```powershell
cd "C:\Users\domin\Desktop\Garmin-MCP"
.\scripts\start.ps1
```

Docker :

```powershell
cd "C:\Users\domin\Desktop\Garmin-MCP"
docker compose up -d
```

Status :

```powershell
.\scripts\status.ps1
```

Tests :

```powershell
.\scripts\test.ps1
```

---

## 28. Points de vigilance techniques

### 28.1 Auth Garmin

Il faut vérifier précisément ce que permet `garmin-mcp-auth`.

S’il est purement interactif, ne pas inventer une fausse API d’auth. Dans ce cas :

- afficher la procédure dans l’UI ;
- ouvrir un terminal ou lancer un processus guidé ;
- capturer uniquement les messages non sensibles ;
- détecter ensuite la présence et validité du token.

### 28.2 Tunnel Cloudflare dans Docker

Cloudflared dans Docker peut fonctionner, mais les différences réseau doivent être documentées.

Si le MCP écoute dans le même conteneur, Cloudflare doit pointer vers :

```text
http://127.0.0.1:8080
```

### 28.3 Un seul conteneur

Comme l’utilisateur demande une image unique, éviter une architecture multi-conteneurs pour la version initiale.

Cela impose :

- un entrypoint qui lance backend ;
- backend qui contrôle les sous-processus ;
- frontend servi par backend ou intégré dans le runtime final.

### 28.4 Next.js dans un seul conteneur

Option recommandée pour simplicité :

- build statique du frontend ;
- FastAPI sert les fichiers statiques.

Option alternative :

- lancer Next.js server et FastAPI dans le même conteneur ;
- nécessite supervision interne ;
- plus complexe.

---

## 29. Roadmap future

Prévoir sans forcément implémenter immédiatement :

- tunnel Cloudflare nommé via UI ;
- configuration Cloudflare Access compatible si possible ;
- mode read-only strict MCP ;
- filtre d’outils MCP ;
- export diagnostic zip ;
- mise à jour automatique de l’image Docker ;
- ajout d’un reverse proxy local avec auth par header si ChatGPT le supporte ;
- profil utilisateur multi-comptes ;
- support d’autres MCP santé/sport ;
- métriques Prometheus locales ;
- mode service Windows.

---

## 30. Résumé de l’architecture cible

GarminToGPT doit être une application locale complète :

```text
Next.js UI
  ↓
FastAPI backend
  ↓
Services internes
  ├── Garmin Auth Service
  ├── MCP Service
  ├── Cloudflare Tunnel Service
  ├── Healthcheck Service
  ├── Log Service
  └── Test Service
  ↓
garmin-mcp + mcp-proxy + cloudflared
  ↓
URL HTTPS /mcp
  ↓
ChatGPT MCP Connector
```

L’application doit être simple à utiliser, mais conçue proprement :

- frontend séparé ;
- backend séparé ;
- Docker unique ;
- GHCR ;
- GitHub Actions ;
- tests ;
- logs ;
- sécurité ;
- documentation ;
- diagnostics.

Le livrable doit être une base durable, pas un prototype fragile.
