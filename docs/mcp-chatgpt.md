# ChatGPT MCP Connector

1. Enregistre une clé Personal API Garmin via `/connexion` et vérifie-la.
2. Configure le tunnel OpenAI via `/tunnel` : `tunnel_id` + runtime API key
   (Tunnels Read + Use). La validation passe par OpenAI.
3. Démarre le tunnel depuis `/tunnel` ou `Activer l'accès ChatGPT` sur l’accueil.
4. Vérifie que `http://127.0.0.1:8091/readyz` répond 200.
5. Dans ChatGPT → Settings → Connectors, choisis `Connection: Tunnel`, puis
   sélectionne le tunnel ou colle le `tunnel_id`.
6. Garde le client tunnel démarré pour les appels MCP.

Il n’y a pas d’URL publique `https://…/mcp` à copier. Ne configure pas
`/sse` sauf contrainte technique démontrée.
