# Dépannage

## Clé API Garmin absente

Ouvre `/connexion`, crée une clé sur
[Garmin Connect → Personal API](https://connect.garmin.com/app/settings/personalApiToken),
puis colle-la. Le pont MCP et le tunnel refusent de démarrer sans clé vérifiée.

## Clé API Garmin refusée (HTTP 400, 401 ou 403)

La clé est invalide, révoquée ou expirée. Garmin ne permet pas de la renouveler
par API : crée une nouvelle clé (30/90/180/365 jours) et mets-la à jour dans
`/connexion`. L’ancienne clé reste active tant que la nouvelle n’a pas été
vérifiée.

## Rotation / date d’expiration Garmin inconnue

Garmin ne publie pas la date d’expiration de la clé. Renseigne dans
`/connexion` la date affichée sur la page Personal API. Si Garmin renvoie un
jeton valable moins de 24 h, la date est détectée automatiquement.

## Variable d’environnement Garmin prioritaire

Si `GARMIN_PERSONAL_API_KEY` est définie, elle est prioritaire sur le fichier.
L’interface ne peut pas la remplacer : retire la variable (ou mets-la à jour)
puis recharge `/connexion`.

## Tunnel OpenAI non configuré

Ouvre `/tunnel`. Il faut :

- un `tunnel_id` créé dans
  [Platform → Tunnels](https://platform.openai.com/settings/organization/tunnels) ;
- une **clé API ChatGPT** créée dans
  [Platform → Runtime API keys](https://platform.openai.com/settings/organization/api-keys)
  avec Tunnels **Read + Use**.

Le `tunnel_id` seul ne suffit pas : `tunnel-client run` exige la clé.
La page `/tunnel` vérifie les deux valeurs via `tunnel-client admin tunnels get`
avant de les enregistrer. Voir le
[guide Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

## 401 / 403 à la validation du tunnel

La clé API ChatGPT est invalide, expirée, ou n’a pas les permissions Tunnels
Read + Use. Une admin key ne doit pas être utilisée pour le daemon. Crée une
runtime key dédiée et réessaie.

## 404 à la validation du tunnel

Le `tunnel_id` est incorrect ou le tunnel n’est pas accessible dans le
workspace OpenAI courant. Vérifie l’ID complet (ne le tronque pas) et le
workspace.

## `/readyz` reste en 503 ou refuse la connexion

- Vérifie `logs/tunnel.log`.
- Vérifie l’accès sortant HTTPS vers `api.openai.com:443`.
- Vérifie que `mcp-proxy` répond sur `http://127.0.0.1:8080/mcp`.
- Le client attend le MCP local jusqu’à 90 s (`--mcp.startup-wait-timeout`).
  Si le premier démarrage de `mcp-proxy`/`garmin-personal-mcp` est plus long,
  augmente `tunnel.mcp_startup_timeout_seconds`.
- Vérifie qu’aucun autre processus n’occupe le port 8091.
- Le client doit rester démarré pour les appels MCP.

## `connection refused` sur 8080 au démarrage

Le tunnel a démarré avant `mcp-proxy`. La version 1.1.1 attend le listener MCP
avant le premier poll. Après mise à jour, redémarre le backend puis le tunnel
depuis `/tunnel`.

## Le tunnel n’apparaît pas dans ChatGPT

- Le tunnel doit être créé dans le bon workspace OpenAI.
- L’opérateur du connecteur a besoin de Tunnels Read + Use.
- Le client doit être healthy (`/readyz` 200).
- Un tunnel très récent peut mettre quelques instants à se propager.
- Dans ChatGPT : Settings → Connectors → `Connection: Tunnel`, puis sélectionne
  le tunnel ou colle son ID.

## Variable d’environnement tunnel prioritaire

Si `CONTROL_PLANE_TUNNEL_ID` ou `CONTROL_PLANE_API_KEY` est définie, elle est
prioritaire sur les fichiers. La page `/tunnel` passe en lecture seule ;
retire les variables pour gérer le tunnel depuis l’interface.

## Téléchargement de tunnel-client refusé

Le backend télécharge la release OpenAI `v0.0.18` et vérifie son SHA-256. Un
échec de checksum est volontairement bloquant. Vérifie le réseau, puis réessaie
depuis `/tunnel` avec `Installer le client`. Tu peux aussi installer
manuellement `tunnel-client` dans le `PATH`.

## Port 8080 occupé

Le proxy MCP utilise `127.0.0.1:8080`. Arrête l’autre service ou modifie
`config/app.yaml` (`mcp.port` et `tunnel.mcp_server_url`).

## Port 8091 occupé

Le healthcheck du tunnel utilise `127.0.0.1:8091`. Arrête l’ancien client ou
modifie `tunnel.health_port` dans `config/app.yaml`.

## Docker et persistance des clés

Les volumes `garmintogpt_garmin`, `garmintogpt_openai` et
`garmintogpt_runtime` conservent les clés, le tunnel ID et l’état entre les
redémarrages. `docker compose restart` et `docker compose up -d` ne les
effacent pas. **`docker compose down -v` supprime les volumes et les clés** ;
utilise `docker compose down` pour conserver les données.

Le healthcheck `/ui` du tunnel est interne au conteneur (loopback) ;
l’application lit `/readyz` depuis le backend.

## ChatGPT ne voit pas le connecteur

Vérifie que le tunnel est prêt, que le `tunnel_id` est le bon, et que le
connecteur utilise `Connection: Tunnel` (pas une URL publique).
