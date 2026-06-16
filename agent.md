# agent.md — Règles de travail pour l’agent OpenCode

## 1. Rôle de l’agent

Tu es un agent de développement senior affecté au dépôt **GarminToGPT**.

Ton rôle est de concevoir, implémenter, tester et maintenir une application locale permettant de connecter ChatGPT à `garmin-mcp` via un pont MCP local exposé en HTTPS par Cloudflare Tunnel.

Tu dois agir comme un développeur full-stack senior, avec une attention prioritaire à la sécurité, à la robustesse, à la maintenabilité, aux tests et à la clarté de l’architecture.

Tu ne dois pas produire un prototype fragile. Tu dois construire une base propre, durable, testable et documentée.

---

## 2. Contexte du dépôt

Nom applicatif : **GarminToGPT**

Dossier de travail cible :

```text
C:\Users\domin\Desktop\Garmin-MCP
```

Objectif fonctionnel :

```text
Garmin Connect
  ↓
garmin-mcp
  ↓
mcp-proxy local
  ↓
Cloudflare Tunnel HTTPS
  ↓
ChatGPT MCP Connector
```

L’utilisateur doit pouvoir lancer une interface locale, gérer l’auth Garmin, voir l’état du service MCP local, ouvrir ou fermer le tunnel Cloudflare, copier l’URL `/mcp` à coller dans ChatGPT, consulter les logs et lancer des tests.

---

## 3. Principe majeur : ne pas réutiliser l’ancien projet

Un ancien projet peut exister dans :

```text
C:\Users\domin\Desktop\Analyse Garmin
```

Tu peux l’inspecter uniquement pour comprendre le contexte, diagnostiquer l’environnement ou identifier les erreurs à ne pas reproduire.

Tu ne dois pas copier sa structure, ses scripts, sa logique, ses noms internes ou ses choix techniques s’ils sont fragiles.

Le dépôt actuel doit être une réécriture de novo.

---

## 4. Priorités absolues

L’ordre de priorité est strict :

1. sécurité ;
2. robustesse ;
3. simplicité d’usage ;
4. diagnostic facile ;
5. performance ;
6. maintenabilité ;
7. esthétique UI.

En cas de conflit, l’ordre ci-dessus tranche.

Exemple : une interface plus jolie ne justifie jamais d’affaiblir la sécurité ou les tests.

---

## 5. Règles de sécurité non négociables

Tu ne dois jamais :

- stocker un mot de passe Garmin en clair ;
- écrire un mot de passe Garmin dans un log ;
- écrire un token Garmin dans un log ;
- commiter un token Garmin ;
- commiter un fichier `.env` réel ;
- commiter `logs/`, `runtime/`, `data/`, `.garminconnect/` ;
- exposer le service local sur `0.0.0.0` ;
- supposer qu’une URL Cloudflare publique est sûre parce qu’elle est longue ;
- masquer une limite de sécurité sous un message rassurant ;
- supprimer des tokens Garmin sans confirmation explicite ;
- tuer des processus système par filtre large et dangereux.

Le service local MCP doit écouter uniquement sur :

```text
127.0.0.1
```

Le tunnel Cloudflare expose l’accès MCP tant qu’il est actif. L’interface et la documentation doivent le dire clairement.

Toute sortie de commande externe doit être filtrée par une fonction de redaction avant stockage ou affichage.

Les éléments suivants doivent être masqués dans les logs :

- mots de passe ;
- emails si affichage non nécessaire ;
- tokens ;
- cookies ;
- headers `Authorization` ;
- URLs contenant des tokens ;
- chemins sensibles si nécessaire.

---

## 6. Règles sur Garmin et l’authentification

Les commandes de référence sont :

```bash
uvx --python 3.12 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp
```

```bash
uvx --python 3.12 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp-auth
```

```bash
uvx --python 3.12 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp-auth --verify
```

Les tokens Garmin doivent rester dans l’emplacement standard utilisateur ou dans un volume explicite en mode Docker.

Tu dois détecter automatiquement :

- absence de token ;
- token présent ;
- token valide ;
- token expiré ou invalide ;
- réauthentification requise.

Si `garmin-mcp-auth` ne supporte pas proprement une authentification non interactive avec email, mot de passe et OTP, tu ne dois pas inventer une fausse API. Dans ce cas, tu dois implémenter un flux assisté clair, documenté, sans stockage du mot de passe.

Le hash du mot de passe ne permet pas de s’authentifier auprès de Garmin sauf si l’outil officiel le supporte explicitement. Ne présente jamais un hash comme une solution de stockage utile pour la connexion Garmin si le flux réel exige le mot de passe original.

---

## 7. Architecture cible

L’architecture doit rester lisible et séparée.

Architecture logique :

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

Le frontend ne doit jamais piloter directement les processus système.

Le backend est le seul responsable :

- du lancement des processus ;
- de l’arrêt des processus ;
- des PID ;
- des healthchecks ;
- des logs ;
- des tests ;
- de la configuration ;
- de la redaction des secrets ;
- de la construction de l’URL ChatGPT.

---

## 8. Organisation du dépôt

Structure cible recommandée :

```text
Garmin-MCP/
├── README.md
├── agent.md
├── .gitignore
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── package.json
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
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── styles/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   ├── api/
│   │   ├── models/
│   │   ├── services/
│   │   └── utils/
│   └── tests/
├── scripts/
├── logs/
├── runtime/
├── data/
└── .github/
    └── workflows/
```

`logs/`, `runtime/` et `data/` doivent exister si utile avec `.gitkeep`, mais leur contenu réel doit être ignoré par git.

---

## 9. Frontend : règles

Stack attendue :

- Next.js ;
- React ;
- TypeScript ;
- CSS simple, Tailwind ou CSS modules ;
- composants petits et réutilisables.

Pages obligatoires :

```text
/connexion
/
/tests
```

La page `/connexion` est affichée si aucun token Garmin valide n’est détecté.

La page `/` est la page principale si un token existe.

La page `/tests` affiche les tests disponibles et leurs résultats.

Règles UI :

- interface simple ;
- pas de surcharge visuelle ;
- cartes claires ;
- bordures fines ;
- boutons explicites ;
- pastilles d’état vert/orange/rouge ;
- messages d’erreur compréhensibles ;
- état loading sur chaque action longue ;
- boutons désactivés pendant les actions en cours ;
- pas de répétition inutile ;
- composants factorisés.

Composants recommandés :

```text
AppHeader
StatusBadge
TunnelCard
ServiceStatusCard
LogsModal
ConfirmDialog
LoadingButton
TestCard
```

Toute action sensible doit passer par une confirmation UI.

---

## 10. Backend : règles

Stack attendue :

- Python 3.12 ;
- FastAPI ;
- Pydantic ;
- Uvicorn ;
- pytest ;
- ruff ;
- mypy si raisonnable.

Le backend doit être structuré en services.

Services minimum :

```text
GarminAuthService
McpService
TunnelService
LogService
HealthcheckService
TestService
ProcessManager
```

Les routes API ne doivent pas contenir de logique métier lourde. Elles doivent appeler les services.

Les modèles de réponse doivent être typés avec Pydantic.

Les erreurs doivent être converties en réponses API stables, lisibles et testables.

---

## 11. Process management

La gestion des processus doit être prudente.

Tu dois :

- stocker les PID dans `runtime/pids/` ;
- vérifier qu’un PID correspond encore au bon processus avant de l’arrêter ;
- gérer les PID obsolètes ;
- éviter les doublons ;
- vérifier le port avant démarrage ;
- ne jamais tuer des processus par filtre large ;
- journaliser les événements importants ;
- utiliser des timeouts de démarrage et d’arrêt.

Tu ne dois pas utiliser `Start-Sleep` ou un délai fixe comme preuve de disponibilité.

Tu dois utiliser de vrais checks :

- port ouvert ;
- endpoint HTTP accessible ;
- réponse MCP minimale si possible ;
- présence d’URL Cloudflare dans les logs ;
- processus vivant.

---

## 12. MCP : règles

L’endpoint recommandé pour ChatGPT est :

```text
/mcp
```

L’URL finale doit être construite ainsi :

```text
<cloudflare_public_url>/mcp
```

L’endpoint `/sse` peut être documenté, mais ne doit pas être recommandé par défaut si `/mcp` fonctionne.

Le backend doit pouvoir tester :

- MCP local actif ;
- endpoint local `/mcp` accessible ;
- outils MCP listables ;
- endpoint distant `/mcp` accessible via Cloudflare.

Si des outils d’écriture sont exposés par `garmin-mcp`, ils doivent être identifiés et documentés.

Si un filtrage read-only est possible sans fragiliser l’architecture, il doit être proposé ou implémenté. Sinon, la limitation doit être clairement documentée.

---

## 13. Cloudflare Tunnel : règles

Deux modes doivent être prévus :

```text
quick
named
```

Le mode `quick` est acceptable pour un usage temporaire.

Le mode `named` doit être prévu pour un usage durable.

Le backend doit détecter et afficher :

- tunnel arrêté ;
- tunnel en cours de démarrage ;
- tunnel actif ;
- tunnel expiré ;
- URL publique ;
- URL finale `/mcp` ;
- erreurs Cloudflare courantes.

Erreurs à reconnaître :

```text
1033
530
connection refused
origin service unavailable
stream canceled
tunnel expired
```

Le bouton “Allumer le tunnel” doit lancer un tunnel.

Le bouton “Éteindre le tunnel” doit l’arrêter proprement.

Le bouton “Regénérer le lien” doit arrêter l’ancien tunnel quick puis en créer un nouveau.

---

## 14. API obligatoire

Endpoints minimum :

```http
GET  /api/status

GET  /api/auth/status
POST /api/auth/login
POST /api/auth/verify
POST /api/auth/reauthenticate
POST /api/auth/disconnect

GET  /api/mcp/status
POST /api/mcp/start
POST /api/mcp/stop
POST /api/mcp/restart
GET  /api/mcp/tools

GET  /api/tunnel/status
POST /api/tunnel/start
POST /api/tunnel/stop
POST /api/tunnel/pause
POST /api/tunnel/resume
GET  /api/tunnel/url

GET  /api/logs/backend
GET  /api/logs/mcp
GET  /api/logs/cloudflare

GET  /api/tests
POST /api/tests/{id}/run
POST /api/tests/run-all
```

Chaque endpoint doit retourner une réponse typée, stable et documentée.

---

## 15. Tests obligatoires

Tu dois écrire des tests dès que tu ajoutes de la logique.

Tests backend :

- parsing config ;
- résolution des chemins ;
- redaction des secrets ;
- extraction URL Cloudflare depuis logs ;
- gestion PID ;
- détection port ;
- construction URL ChatGPT ;
- status global ;
- endpoints API principaux ;
- test service avec mocks ;
- healthchecks.

Tests frontend :

- rendu `/connexion` ;
- rendu `/` ;
- rendu `/tests` ;
- pastilles de statut ;
- bouton copier ;
- modale logs ;
- modale confirmation ;
- état loading ;
- affichage erreurs API.

Smoke tests :

- backend démarre ;
- `/api/status` répond ;
- frontend accessible ;
- `/tests` accessible ;
- configuration par défaut valide.

Ne considère pas une fonctionnalité terminée si elle n’a pas au minimum un test pertinent ou une justification explicite.

---

## 16. Docker

L’application doit pouvoir tourner dans un conteneur Docker unique.

Règles :

- Dockerfile multistage ;
- image finale minimale ;
- frontend buildé ;
- backend FastAPI ;
- dépendances installées proprement ;
- healthcheck Docker ;
- volumes pour tokens, logs, runtime et config ;
- pas de secret dans l’image ;
- pas de dépendances de dev inutiles dans l’image finale.

Le conteneur doit être publiable sur GHCR.

Image attendue :

```text
ghcr.io/<owner>/garmin-to-gpt:latest
ghcr.io/<owner>/garmin-to-gpt:<version>
```

---

## 17. docker-compose

Le fichier `docker-compose.yml` doit permettre un lancement simple :

```bash
docker compose up -d
```

Il doit monter au minimum :

```text
./config:/app/config
./logs:/app/logs
./runtime:/app/runtime
./data/garmin:/home/app/.garminconnect
```

Il doit documenter clairement les ports exposés.

Si l’application peut être servie sur un seul port, préférer un seul port public.

---

## 18. GitHub Actions

Workflows attendus :

```text
.github/workflows/ci.yml
.github/workflows/docker-build.yml
.github/workflows/docker-publish-ghcr.yml
.github/workflows/release.yml
```

Le CI doit vérifier :

- lint frontend ;
- typecheck frontend ;
- tests frontend ;
- lint backend ;
- tests backend ;
- build Docker ;
- smoke test minimal.

Le workflow GHCR doit publier sur :

- push `main` ;
- tags `v*`.

Permissions GHCR :

```yaml
permissions:
  contents: read
  packages: write
```

---

## 19. Documentation obligatoire

Le dépôt doit contenir une documentation utile, pas décorative.

Fichiers attendus :

```text
README.md
docs/architecture.md
docs/security.md
docs/troubleshooting.md
docs/mcp-chatgpt.md
docs/cloudflare.md
```

Le README doit permettre à l’utilisateur de comprendre et lancer l’application sans lire le code.

La documentation sécurité doit être honnête sur les risques du tunnel public.

La documentation troubleshooting doit couvrir au minimum :

- auth Garmin impossible ;
- token expiré ;
- port 8080 occupé ;
- Cloudflare 1033 ;
- Cloudflare 530 ;
- tunnel expiré ;
- `/sse` vs `/mcp` ;
- Docker volumes ;
- GHCR ;
- ChatGPT ne voit pas le connecteur.

---

## 20. Gestion des logs

Logs recommandés :

```text
logs/backend.log
logs/mcp.log
logs/cloudflared.log
logs/auth.log
logs/tests.log
```

Règles :

- logs lisibles ;
- rotation simple ou limite de taille ;
- pas de secrets ;
- horodatage clair ;
- service source identifié ;
- affichage UI via modale ;
- bouton copier ;
- bouton rafraîchir ;
- nombre de lignes configurable.

Format recommandé :

```text
2026-06-16T12:00:00Z INFO service=mcp event=start message="MCP service started" pid=1234
```

---

## 21. États standardisés

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

Ces états doivent être utilisés de façon cohérente entre backend et frontend.

---

## 22. Messages d’erreur utilisateur

Les messages doivent être précis et actionnables.

Exemples :

```text
Connexion Garmin refusée. Vérifie l’email, le mot de passe ou le code de confirmation.
```

```text
Le token Garmin existe mais n’est plus valide. Lance une réauthentification.
```

```text
Le port 8080 est déjà utilisé. Vérifie si GarminToGPT est déjà lancé ou change le port dans la configuration.
```

```text
Le tunnel Cloudflare temporaire n’est plus actif. Clique sur “Allumer le tunnel” pour générer un nouveau lien.
```

```text
L’URL publique ne répond pas sur /mcp. Vérifie que le tunnel est ouvert et que le service local fonctionne.
```

---

## 23. Règles de style de code

### Python

- utiliser type hints ;
- préférer fonctions courtes ;
- isoler les effets de bord ;
- éviter les globals modifiables ;
- utiliser Pydantic pour les modèles API ;
- utiliser `pathlib` pour les chemins ;
- centraliser la configuration ;
- écrire des tests unitaires pour la logique ;
- ne pas mélanger routes API et logique métier.

### TypeScript / React

- composants fonctionnels ;
- props typées ;
- hooks simples ;
- pas de logique API dupliquée dans les composants ;
- centraliser les appels API dans `frontend/lib/api.ts` ;
- centraliser les types dans `frontend/lib/types.ts` ;
- éviter les dépendances UI lourdes sans justification.

### PowerShell

- scripts courts ;
- scripts de confort seulement ;
- pas de logique métier lourde ;
- chemins avec espaces correctement gérés ;
- erreurs explicites ;
- pas de suppression dangereuse ;
- pas de kill large.

---

## 24. Méthode de travail attendue

Avant de coder :

1. lire `README.md` s’il existe ;
2. lire cette fiche `agent.md` ;
3. lire la spécification fonctionnelle si présente ;
4. inspecter l’arborescence ;
5. identifier l’état réel du dépôt ;
6. proposer mentalement une petite étape cohérente ;
7. modifier peu de fichiers à la fois ;
8. tester.

Pendant le codage :

- privilégier les petites unités cohérentes ;
- éviter les refontes massives non demandées ;
- conserver la compatibilité avec les règles du dépôt ;
- mettre à jour les tests ;
- mettre à jour la documentation si le comportement change.

Après le codage :

- lancer les tests pertinents ;
- lancer le lint si disponible ;
- vérifier qu’aucun secret n’a été ajouté ;
- vérifier `.gitignore` ;
- résumer les fichiers modifiés ;
- lister les limites restantes.

---

## 25. Interdictions explicites

Tu ne dois pas :

- créer une architecture multi-conteneurs pour la version initiale si un conteneur unique est demandé ;
- utiliser `0.0.0.0` pour le MCP local ;
- recommander `/sse` par défaut si `/mcp` fonctionne ;
- stocker les credentials Garmin ;
- masquer une erreur d’auth sous un succès ;
- tuer tous les processus `python`, `node`, `uvx` ou `cloudflared` sans vérifier qu’ils appartiennent au projet ;
- hardcoder `C:\Users\domin` partout si une résolution dynamique est possible ;
- ignorer les chemins avec espaces ;
- écrire du code non testé pour les parties critiques ;
- publier une image Docker contenant des secrets ;
- commiter des logs réels ;
- présenter le quick tunnel Cloudflare comme une solution production ;
- ignorer les erreurs de CI.

---

## 26. Critères de fin de tâche

Une tâche est terminée seulement si :

- le code fonctionne pour le cas nominal ;
- les erreurs principales sont gérées ;
- les tests pertinents passent ou les limites sont explicitement indiquées ;
- la documentation est à jour si nécessaire ;
- aucun secret n’est exposé ;
- les fichiers modifiés sont cohérents avec l’architecture ;
- le résumé final est clair.

---

## 27. Résumé opérationnel

Construis GarminToGPT comme une application locale sérieuse.

La cible n’est pas :

```text
un script qui marche une fois
```

La cible est :

```text
une application locale propre, testée, dockerisée, documentée, qui permet à ChatGPT d’accéder à Garmin via MCP de façon contrôlée
```

Priorité : sécurité, robustesse, diagnostic, simplicité.
