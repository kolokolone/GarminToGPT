# GarminToGPT — Agent UI Guidelines

Ce document décrit l’interface actuelle (v1.1.5). Lire aussi
`docs/architecture.md`, `docs/openai-tunnel.md` et `docs/security.md`.

## Principes

- Interface locale, sobre, en français.
- Une question centrale : **ChatGPT peut-il joindre Garmin ?**
- Pas de jargon inutile ; les erreurs doivent être actionnables.
- Jamais de secret complet dans le DOM, un log ou une URL.

## Pages

### `/` — Accueil

- Carte « État du pont » : étapes Garmin → MCP local → Tunnel OpenAI →
  Connecteur ChatGPT.
- Carte « Accès ChatGPT à Garmin » : activer/couper l’accès.
- Carte « Tunnel OpenAI » : tunnel ID, readiness, bouton Copier l’ID, lien
  Connecteurs ChatGPT, démarrage/arrêt/redémarrage.
- **Aucune URL publique** : ne pas afficher de champ « URL à coller ».
- Cartes techniques : Service local, Garmin API, Tunnel OpenAI.
- Sans clé Garmin : message + redirection vers `/connexion`.
- Sans tunnel configuré : lien « Configurer le tunnel ».

### `/connexion` — Garmin

- Clé API personnelle Garmin (`GCDC_…`), champ masqué.
- Validation avant sauvegarde, mise à jour, suppression confirmée.
- Afficher hint masqué, source, jeton, rotation, scopes, dernière vérification.
- Jamais de mot de passe Garmin ni de champ OTP.

### `/tunnel` — OpenAI

- Champs : `tunnel_id`, **clé API ChatGPT** (runtime key OpenAI), champ masqué.
- Liens : Platform Tunnels, Runtime API keys, Connecteurs ChatGPT.
- Validation via `tunnel-client admin tunnels get` avant sauvegarde.
- Afficher readiness `/readyz`, client installé/version, source de configuration,
  hint de clé, tableau de bord local.
- Actions : installer le client, démarrer, arrêter, redémarrer, mettre à jour,
  supprimer (confirmation).
- Si la configuration vient de l’environnement, formulaire en lecture seule et
  message expliquant de retirer les variables.
- Rappeler : ChatGPT → `Connection: Tunnel` + `tunnel_id`, aucune URL publique.

### `/tests` — Diagnostics

- Groupes : pré-requis, Garmin, MCP, tunnel OpenAI, ChatGPT.
- Lancer un test ou tous les tests, afficher message + suggestion.
- Les tests ne doivent pas exposer de secret.

## États et libellés

- Tunnel : `arrêté`, `démarrage`, `actif`, `erreur`.
- Garmin : `non configurée`, `configurée`, `valide`, `expire bientôt`,
  `expirée`, `erreur`.
- MCP : `arrêté`, `démarrage`, `actif`, `erreur`.
- Badges cohérents avec les classes CSS existantes.

## Sécurité UI

- Clés en `type="password"`, `autoComplete="off"`, `spellCheck={false}`.
- Ne jamais préremplir une clé existante.
- Ne jamais afficher la clé complète après saisie.
- Utiliser les messages API (`detail`) pour les erreurs, sans HTML.
- Les liens externes s’ouvrent avec `target="_blank"` et `rel="noreferrer"`.

## Accessibilité et style

- Labels associés aux champs, boutons explicites, focus visible.
- Réutiliser `card`, `form-grid`, `info-callout`, `warning-box`, `error-box`,
  `success-box`, `LoadingButton`, `StatusBadge`, `ConfirmDialog`.
- Éviter les tableaux de bord surchargés ; garder une hiérarchie simple.
