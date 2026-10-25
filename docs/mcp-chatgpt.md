# ChatGPT MCP Connector

1. Enregistre une **clé API personnelle Garmin** via `/connexion` et vérifie-la.
   Elle alimente [Garmin Personal MCP](https://github.com/Mason-Levyy/garmin-personal-mcp).
2. Configure le **Secure MCP Tunnel OpenAI** via `/tunnel` : `tunnel_id` +
   **clé API ChatGPT** (runtime key OpenAI, Tunnels Read + Use). La validation
   passe par `tunnel-client admin tunnels get`.
3. Démarre le tunnel depuis `/tunnel` ou `Activer l'accès ChatGPT` sur l’accueil.
4. Vérifie que `http://127.0.0.1:8091/readyz` répond 200.
5. Dans ChatGPT → Settings → Connectors, choisis `Connection: Tunnel`, puis
   sélectionne le tunnel ou colle le `tunnel_id`.
6. Garde le client tunnel démarré pour les appels MCP.

Il n’y a pas d’URL publique à copier. Ne configure pas `/sse` sauf contrainte
technique démontrée.

Références :

- [Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [openai/tunnel-client](https://github.com/openai/tunnel-client)
- [Garmin Personal MCP](https://github.com/Mason-Levyy/garmin-personal-mcp)
- [Client officiel Garmin Personal API](https://github.com/garmin/connect-personal-api-python)
