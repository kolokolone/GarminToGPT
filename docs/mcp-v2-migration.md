# Préparation de la migration MCP Python SDK v1 vers v2

GarminToGPT reste actuellement sur le SDK MCP v1 avec les contraintes suivantes :

- `mcp-proxy==0.12.0` ;
- `mcp>=1.28.1,<2` dans l'environnement du proxy ;
- `mcp>=1.28.1,<2` dans l'environnement de `garmin-mcp`.

Ne retire pas la borne `<2` avant d'avoir traité les points bloquants ci-dessous.

## Comparaison ciblée

| Zone | Version actuelle (MCP v1) | Cible MCP v2 | Changement à prévoir pour GarminToGPT |
|---|---|---|---|
| Dépendance SDK | `mcp>=1.28.1,<2` | `mcp>=2,<3` | Ne changer la contrainte qu'après migration et tests de bout en bout. Ne pas contraindre `mcp-types` séparément : MCP v2 l'installe avec une version exacte. |
| Serveur haut niveau Garmin | `from mcp.server.fastmcp import FastMCP` | `from mcp.server import MCPServer` | Remplacer l'import et `FastMCP(...)` par `MCPServer(...)` dans `garmin_mcp`. |
| Configuration HTTP | `FastMCP(name, host=..., port=...)` | `MCPServer(name)` puis paramètres sur `run()` | Retirer `host` et `port` du constructeur. Pour HTTP, appeler `run(transport="streamable-http", host=..., port=...)`. Pour stdio, ne transmettre aucun paramètre HTTP. |
| Décorateurs Garmin | `@app.tool()`, `@app.resource()` | Identiques | Les modules qui enregistrent les outils devraient rester majoritairement inchangés. Vérifier néanmoins le wrapper `_ToolFilter` et ses types. |
| Fonctions synchrones | Exécutées sur le thread de la boucle | Exécutées dans un worker thread | Vérifier que le client Garmin partagé et ses sessions HTTP supportent les appels concurrents. Ajouter un verrou ou sérialiser les appels si nécessaire. |
| Champs des modèles MCP | Plusieurs champs camelCase, par exemple `inputSchema`, `serverInfo`, `isError` | Attributs Python snake_case : `input_schema`, `server_info`, `is_error` | Adapter tout code qui lit ou construit directement des modèles MCP. Le JSON sur le réseau conserve ses noms protocolaires. |
| Contexte de requête bas niveau | `request_ctx.get()` ou `server.request_context` | Contexte reçu comme premier argument du handler | Réécrire les handlers bas niveau concernés. C'est le blocage actuel de `mcp-proxy`. |
| Enregistrement des handlers bas niveau | Mutation de `request_handlers` et `notification_handlers` | Handlers `on_*` au constructeur ou `add_request_handler()` | `mcp-proxy 0.12.0` doit être porté en profondeur ou remplacé avant MCP v2. |
| Client MCP | Transport + `ClientSession` + `initialize()` manuel | Client haut niveau `Client(...)` recommandé | Le probe HTTP maison peut rester en JSON-RPC legacy au départ, car v2 reste compatible avec les anciens clients. Une migration vers `Client` réduirait ensuite le code spécifique. |
| Transport Streamable HTTP côté client | Retourne `(read, write, get_session_id)` | Retourne `(read, write)` | Adapter les consommateurs du transport SDK. La récupération directe du callback de session disparaît. |
| HTTP interne au SDK | `httpx` et `httpx-sse` | `httpx2` | Vérifier les fabriques de clients et types personnalisés. Le backend GarminToGPT peut garder sa propre dépendance `httpx` tant qu'il ne la passe pas au SDK MCP. |
| Erreurs SDK | `McpError`, souvent autour de `ErrorData` | `MCPError(code, message, data=...)` | Renommer les imports et adapter les constructions/lectures d'erreurs. Les timeouts MCP utilisent désormais le code JSON-RPC `-32001`. |
| Ressources | URI souvent représentées par `AnyUrl` | URI exposées comme `str`, validation de chemins plus stricte | Tester les ressources de modèles d'entraînement et toute URI contenant chemins, valeurs absolues ou `..`. |
| Taille HTTP | Pas de limite v2 équivalente par défaut | Corps Streamable HTTP limité à 4 Mio | Mesurer les grosses réponses Garmin. Augmenter explicitement `max_request_body_size` seulement si nécessaire. |
| Protocole | Handshake `initialize`, session HTTP | MCP 2026-07-28 sans handshake ni session pour les clients modernes | Les clients legacy restent acceptés. Mettre les probes à jour pour tester les deux modes avant bascule. |
| Logging, roots, sampling | Capacités actives | Dépréciées ; pas de back-channel dans le protocole 2026 | Vérifier qu'aucun outil Garmin ne dépend de `ctx.info()`, sampling, roots ou elicitation push. Préférer les nouveaux résultats multi-échanges si nécessaire. |
| Tests | Tests de décorateurs et handshake v1 | Nouveaux imports, négociation v2 et callbacks concurrents | Tester `tools/list`, plusieurs appels simultanés, annulation, grosses réponses, HTTP direct et connexion ChatGPT via Cloudflare. |

## Architecture recommandée pour la v2

`garmin-mcp` sait maintenant servir directement en `streamable-http`. La migration la plus
simple consiste donc à supprimer `mcp-proxy` du chemin d'exécution :

```text
ChatGPT -> Cloudflare Tunnel -> garmin-mcp Streamable HTTP -> Garmin Connect
```

Pour y parvenir, GarminToGPT devra transmettre explicitement au processus enfant :

```text
GARMIN_MCP_TRANSPORT=streamable-http
GARMIN_MCP_HOST=127.0.0.1
GARMIN_MCP_PORT=8080
```

Le `ProcessManager` devra accepter un dictionnaire d'environnement contrôlé, sans passer par
un shell. Cette option évite de dépendre de la migration bas niveau de `mcp-proxy`.

## Ordre de migration recommandé

1. Conserver le pin v1 actuel en production.
2. Figer également `garmin-mcp` sur un commit Git connu au lieu de suivre `main`.
3. Créer une branche de migration et porter `garmin-mcp` vers `MCPServer`.
4. Faire passer `host` et `port` du constructeur à `run()`.
5. Ajouter le support d'environnement contrôlé au `ProcessManager` et lancer Garmin directement en HTTP.
6. Tester les outils, ressources, erreurs, appels concurrents et tailles de réponses sous MCP v2.
7. Tester l'endpoint local puis ChatGPT à travers Cloudflare.
8. Remplacer seulement alors la contrainte `<2` par `mcp>=2,<3`.

## Références

- [Guide officiel de migration MCP Python SDK v1 vers v2](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md)
- [Nouveautés MCP Python SDK v2](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/whats-new.md)
- [Serveur Garmin MCP](https://github.com/Taxuspt/garmin_mcp)
- [Documentation des environnements isolés uvx](https://docs.astral.sh/uv/guides/tools/)
