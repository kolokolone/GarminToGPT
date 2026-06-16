# ChatGPT MCP Connector

1. Authentifie Garmin via `/connexion`.
2. Démarre le service local MCP.
3. Démarre le tunnel Cloudflare.
4. Copie l’URL affichée : `https://xxxx.trycloudflare.com/mcp`.
5. Colle cette URL dans le connecteur MCP personnalisé de ChatGPT.

Ne recommande pas `/sse` sauf contrainte technique démontrée.
