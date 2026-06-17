# GarminToGPT — Agent UI Guidelines

Ce document définit les règles que l’agent de développement doit respecter lorsqu’il modifie l’interface de GarminToGPT.

Il doit être lu avant toute modification frontend liée à l’UI, à l’UX, aux composants React, aux pages Next.js ou au CSS global.

L’objectif prioritaire est de conserver une interface simple, claire, sûre et orientée utilisateur, sans transformer l’application en dashboard technique difficile à comprendre.

---

## 1. Principe général de l’interface

GarminToGPT n’est pas seulement un outil de monitoring technique.

C’est une interface de contrôle d’accès entre :

1. Garmin Connect ;
2. le serveur MCP local ;
3. le tunnel Cloudflare ;
4. ChatGPT.

L’utilisateur doit comprendre immédiatement une question centrale :

> Est-ce que ChatGPT peut accéder à mes outils Garmin, et comment couper cet accès ?

Toute évolution UI doit renforcer cette compréhension.

Les informations techniques doivent rester accessibles, mais elles ne doivent jamais dominer la page principale.

---

## 2. Hiérarchie d’information obligatoire

La page d’accueil doit suivre cette hiérarchie :

1. état global du pont ;
2. contrôle principal de l’accès ChatGPT à Garmin ;
3. URL à copier dans ChatGPT ;
4. détails techniques secondaires ;
5. logs, tests et rafraîchissement.

L’ordre visuel doit refléter cette priorité.

Les actions de sécurité, notamment couper ou réactiver l’accès ChatGPT, doivent être plus visibles que les actions secondaires comme afficher les logs ou rafraîchir.

---

## 3. Header

Le header doit rester compact.

Il contient :

* le label `PONT MCP LOCAL` ;
* le titre `GarminToGPT` ;
* la baseline : `Pont local entre Garmin Connect, garmin-mcp et ChatGPT.` ;
* la navigation : `Accueil`, `Garmin`, `Tests` ;
* un badge de version, par exemple `v0.4.0`.

Le titre `GarminToGPT` doit rester identifiable, mais il ne doit pas prendre trop d’espace vertical sur une page fonctionnelle.

Éviter les headers massifs qui repoussent les informations utiles sous la ligne de flottaison.

---

## 4. Carte principale — État du pont

La première carte de la page d’accueil doit s’appeler :

`ÉTAT DU PONT`

Elle doit afficher un titre principal dynamique.

Exemples :

* `Accès Garmin pour ChatGPT activé`
* `Accès Garmin pour ChatGPT coupé`
* `Lien ChatGPT en cours de création`
* `Pont GarminToGPT partiellement prêt`

Elle doit aussi afficher un badge global :

* vert : `PRÊT`
* rouge : `COUPÉ`
* orange : `DÉGRADÉ`
* bleu ou orange clair : `DÉMARRAGE`
* gris : `INACTIF`

La carte doit contenir un stepper horizontal en quatre étapes :

1. Garmin connecté ;
2. MCP local actif ;
3. Tunnel Cloudflare actif ;
4. URL ChatGPT prête.

Chaque étape doit avoir :

* une icône ou pastille ;
* un label court ;
* un sous-texte explicatif ;
* une couleur d’état.

Couleurs du stepper :

* vert : étape OK ;
* gris : étape non prête ou non lancée ;
* orange : étape en cours ou état partiel ;
* rouge : étape bloquante.

Le stepper doit permettre de comprendre en moins de cinq secondes où se situe le blocage.

---

## 5. Carte prioritaire — Accès ChatGPT à Garmin

La seconde carte principale doit s’appeler :

`ACCÈS CHATGPT À GARMIN`

Elle doit être la carte d’action principale.

Elle doit expliquer si ChatGPT peut ou non accéder aux outils Garmin.

État actif :

Titre :

`ChatGPT peut accéder à vos outils Garmin`

Texte :

`Le MCP local est actif et le tunnel est ouvert. ChatGPT peut utiliser les outils Garmin via l’URL ci-dessous.`

Bouton principal :

`Couper l’accès ChatGPT`

Ce bouton doit être rouge, car il coupe l’accès.

État coupé :

Titre :

`ChatGPT ne peut pas accéder à vos outils Garmin`

Texte :

`Le service MCP local est arrêté. Même si le tunnel Cloudflare existe encore, les outils Garmin ne sont plus accessibles.`

Bouton principal :

`Activer l’accès ChatGPT`

Ce bouton doit être vert, car il réactive l’accès.

La carte doit aussi contenir un bouton secondaire :

* `Redémarrer le service local`, si le service est actif ;
* `Démarrer le service local`, si le service est arrêté.

La carte doit contenir un encart d’information clair :

`Quand le MCP local est arrêté, ChatGPT ne peut plus accéder aux outils Garmin.`

Cette phrase est importante : elle explique pourquoi couper le MCP local est une mesure de sécurité suffisante pour empêcher ChatGPT d’utiliser les outils Garmin.

---

## 6. Carte URL — URL à coller dans ChatGPT

La carte URL ne doit pas afficher l’URL comme un grand titre.

Elle doit s’appeler :

`URL À COLLER DANS CHATGPT`

L’URL doit être affichée dans un champ ou bloc arrondi, avec une typographie monospace ou proche d’un style code.

Exemple :

`https://example.trycloudflare.com/mcp`

Actions :

* bouton principal : `Copier`
* bouton secondaire : `Régénérer le lien`

Badge d’état :

* vert : `ACTIVE`
* orange ou bleu : `CRÉATION`
* gris : `INDISPONIBLE`
* rouge : `ARRÊTÉ`

États à gérer :

Si le tunnel est actif mais que l’URL n’est pas encore détectée :

`Lien en cours de création…`

Si le tunnel est arrêté :

`Tunnel Cloudflare non actif`

Si l’URL est disponible :

afficher l’URL complète dans le bloc de copie.

Si aucune URL n’est disponible, le bouton `Copier` doit être désactivé.

---

## 7. Cartes techniques secondaires

Les cartes techniques doivent être secondaires et compactes.

Elles doivent apparaître sous la carte URL.

Cartes attendues :

1. `Service local`
2. `Garmin MCP`
3. `Cloudflare Tunnel`

Chaque carte doit suivre la même structure :

* icône discrète ;
* titre ;
* badge d’état ;
* phrase de résumé ;
* détails techniques en grille deux colonnes.

### Carte Service local

Résumé actif :

`Le service MCP local est en cours d’exécution.`

Résumé arrêté :

`Le service MCP local est arrêté.`

Détails possibles :

* endpoint ;
* PID ;
* port ;
* dernier démarrage ;
* dernier arrêt ;
* dernier événement.

### Carte Garmin MCP

Résumé connecté :

`Connexion à Garmin établie et valide.`

Résumé non connecté :

`Connexion Garmin à vérifier.`

Détails possibles :

* token ;
* validité ;
* dernière connexion ;
* message.

### Carte Cloudflare Tunnel

Résumé actif :

`Le tunnel sécurisé est opérationnel.`

Résumé en démarrage :

`Le tunnel est en cours de démarrage.`

Résumé arrêté :

`Le tunnel est arrêté.`

Détails possibles :

* mode ;
* PID ;
* URL publique ;
* dernier événement.

Les boutons techniques ne doivent pas surcharger ces cartes. Les actions secondaires doivent être regroupées ailleurs lorsque c’est possible.

---

## 8. Barre d’actions secondaires

En bas de la page principale, prévoir une zone d’actions secondaires avec :

* `Afficher les logs`
* `Ouvrir les tests`
* `Rafraîchir`

Ces boutons doivent être visuellement plus discrets que le bouton principal de sécurité.

Ils ne doivent pas rivaliser avec :

* `Couper l’accès ChatGPT`
* `Activer l’accès ChatGPT`

---

## 9. Page Garmin / Connexion

La page de connexion doit inspirer confiance.

Dans la navigation, préférer le libellé :

`Garmin`

ou :

`Compte Garmin`

plutôt que seulement `Connexion`.

La route peut rester inchangée si cela évite de casser le routing.

La page doit indiquer avant les champs :

`GarminToGPT ne stocke pas le mot de passe Garmin.`

Cette information ne doit pas être placée après les champs, car elle est essentielle pour la confiance utilisateur.

La page doit clarifier que l’authentification repose sur la procédure Garmin MCP existante.

Bouton principal :

`Se connecter à Garmin`

Bouton secondaire :

`Vérifier puis démarrer`

Ne pas modifier la logique sensible d’authentification sans justification technique claire.

Ne pas stocker de mot de passe.

Ne pas afficher de secrets dans les logs ou dans l’interface.

---

## 10. Page Tests

La page Tests doit rester complète mais moins répétitive.

Elle doit contenir en haut une carte résumé :

`Diagnostics GarminToGPT`

Cette carte doit afficher :

* bouton principal : `Lancer tous les tests`
* nombre de tests OK ;
* nombre de tests échoués ;
* nombre de tests non lancés ;
* état global du diagnostic.

Les tests doivent être groupés visuellement par sections :

1. Pré-requis ;
2. Garmin ;
3. MCP local ;
4. Cloudflare ;
5. ChatGPT.

Les tests individuels peuvent rester sous forme de cartes, mais elles doivent être compactes.

L’état `Non lancé` doit être gris, pas orange.

Palette des tests :

* gris : non lancé ;
* bleu : en cours ;
* vert : OK ;
* orange : avertissement ;
* rouge : erreur.

---

## 11. Modale logs

La modale logs doit rester lisible pour un développeur, mais ne doit pas être agressive pour l’utilisateur.

Conserver :

* terminal noir ;
* bouton `Copier` ;
* bouton `Rafraîchir` ;
* bouton `Fermer`.

Améliorations souhaitées si simples à implémenter :

* hauteur maximale responsive ;
* autoscroll optionnel ;
* recherche texte ;
* filtre par niveau si les logs contiennent `INFO`, `WARN`, `ERROR`.

La modale ne doit pas déborder de l’écran.

Elle doit rester utilisable sur desktop, tablette et mobile.

---

## 12. Design system

L’interface doit rester cohérente.

Palette recommandée :

* vert foncé : couleur principale ;
* vert clair : succès ;
* rouge : action destructive ou erreur ;
* gris : état neutre ou non lancé ;
* orange : vrai avertissement ;
* bleu discret : labels techniques ou informations froides.

Ne pas utiliser l’orange pour `non lancé`, sauf si l’état représente un problème réel.

Les badges doivent avoir une taille et une forme homogènes.

Les boutons doivent être classés ainsi :

* primaire ;
* secondaire ;
* danger ;
* désactivé.

Les espacements doivent être réguliers.

Les cartes doivent avoir des rayons cohérents.

Les ombres doivent être douces mais pas excessives.

Éviter les cartes trop grandes, trop espacées ou trop décoratives.

L’interface doit rester dense, lisible et professionnelle.

---

## 13. Responsive

L’interface doit être correcte sur :

* desktop large ;
* laptop ;
* tablette ;
* mobile.

Desktop :

* stepper horizontal ;
* cartes techniques en trois colonnes ;
* actions bien alignées.

Tablette :

* cartes techniques en une ou deux colonnes ;
* boutons suffisamment larges ;
* URL lisible.

Mobile :

* stepper vertical ou compact ;
* boutons pleine largeur ;
* URL scrollable horizontalement ou contenue dans un bloc copiable ;
* aucune zone ne doit déborder.

---

## 14. États fonctionnels à respecter

L’UI doit gérer au minimum les états suivants :

### Tout est prêt

* Garmin connecté ;
* MCP local actif ;
* Cloudflare actif ;
* URL disponible ;
* badge global `PRÊT` ;
* bouton principal `Couper l’accès ChatGPT`.

### MCP local arrêté

* Garmin éventuellement connecté ;
* tunnel éventuellement actif ;
* MCP local arrêté ;
* ChatGPT ne peut pas accéder aux outils Garmin ;
* badge global `COUPÉ` ou `DÉGRADÉ` selon le reste de l’état ;
* bouton principal `Activer l’accès ChatGPT`.

### Tunnel en démarrage

* MCP local actif ;
* Cloudflare en démarrage ;
* URL absente ;
* message `Lien en cours de création…` ;
* badge `DÉMARRAGE`.

### Tunnel arrêté

* MCP local éventuellement actif ;
* Cloudflare arrêté ;
* URL indisponible ;
* message `Tunnel Cloudflare non actif`.

### État dégradé

* un ou plusieurs composants ne sont pas prêts ;
* message clair indiquant quoi vérifier ;
* aucun faux état positif.

---

## 15. Règles de wording

Le wording doit être orienté utilisateur.

Préférer :

* `Couper l’accès ChatGPT`
* `Activer l’accès ChatGPT`
* `ChatGPT peut accéder à vos outils Garmin`
* `ChatGPT ne peut pas accéder à vos outils Garmin`
* `URL à coller dans ChatGPT`

Éviter comme action principale :

* `Stop MCP`
* `Start process`
* `Kill service`
* `Pause tunnel`
* `PID`
* `healthcheck`

Ces termes peuvent exister dans les détails techniques, mais pas comme message principal.

---

## 16. Contraintes techniques

Avant toute modification :

1. inspecter les composants existants ;
2. identifier les états déjà disponibles ;
3. réutiliser les types existants ;
4. éviter les refactors inutiles ;
5. ne pas casser les endpoints existants ;
6. ne pas supprimer de fonctionnalité.

Fichiers probablement concernés :

* `frontend/app/page.tsx`
* `frontend/app/connexion/page.tsx`
* `frontend/app/tests/page.tsx`
* `frontend/components/AppHeader.tsx`
* `frontend/components/TunnelCard.tsx`
* `frontend/components/ServiceStatusCard.tsx`
* `frontend/components/TestCard.tsx`
* `frontend/components/LogsModal.tsx`
* `frontend/styles/globals.css`
* types frontend éventuels.

Ne pas déplacer une fonctionnalité sans vérifier qu’elle reste accessible ailleurs.

Ne pas renommer des routes si cela casse l’application.

Ne pas modifier la logique backend sans nécessité.

---

## 17. Sécurité et confidentialité

Ne jamais afficher :

* mot de passe Garmin ;
* token complet sensible ;
* secrets ;
* variables d’environnement sensibles ;
* chemins contenant des données privées inutiles ;
* logs contenant des credentials.

Si un secret doit être mentionné, le masquer.

Exemple :

`Token détecté`

ou :

`Token valide`

Ne pas afficher le token brut.

---

## 18. Critères d’acceptation

Après modification, l’interface doit permettre de comprendre en moins de cinq secondes :

* si Garmin est connecté ;
* si le MCP local est actif ;
* si Cloudflare est actif ;
* si l’URL ChatGPT est prête ;
* si ChatGPT peut accéder aux outils Garmin ;
* comment couper immédiatement cet accès.

Le bouton principal de sécurité doit être évident :

* actif : `Couper l’accès ChatGPT`
* coupé : `Activer l’accès ChatGPT`

Les détails techniques doivent rester disponibles, mais ils ne doivent plus dominer la page.

Les pages principales doivent rester cohérentes entre elles.

Le build frontend doit passer.

Les erreurs TypeScript, React ou CSS doivent être corrigées avant de considérer la tâche terminée.

---

## 19. Checklist avant commit

Avant de finaliser une modification UI, vérifier :

* la page d’accueil en état prêt ;
* la page d’accueil en état MCP arrêté ;
* la page d’accueil en état tunnel en création ;
* la page d’accueil en état tunnel arrêté ;
* la page Garmin / connexion ;
* la page Tests ;
* la modale logs ;
* le responsive desktop ;
* le responsive mobile ;
* les boutons de démarrage, arrêt, redémarrage ;
* la copie de l’URL ;
* l’absence de secrets dans l’UI ;
* le lint ;
* le build.

---

## 20. Résumé de la direction UI

GarminToGPT doit ressembler à un outil local sérieux, clair et rassurant.

L’interface doit être sobre, premium et lisible.

L’utilisateur ne doit pas avoir besoin de comprendre tous les détails MCP pour utiliser l’application.

La page principale doit répondre à une question :

> ChatGPT a-t-il accès à Garmin, oui ou non ?

Puis permettre une action immédiate :

> Couper ou réactiver cet accès.

Tout le reste est secondaire.
