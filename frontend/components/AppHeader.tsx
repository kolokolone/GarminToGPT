import Link from "next/link";

export function AppHeader({ version }: { version?: string }) {
  return (
    <header className="app-header">
      <div>
        <p className="eyebrow">Pont MCP local</p>
        <h1>GarminToGPT</h1>
        <p className="subtitle">Pont local entre Garmin Connect, garmin-mcp et ChatGPT.</p>
      </div>
      <nav className="header-actions" aria-label="Navigation principale">
        <Link href="/">Accueil</Link>
        <Link href="/connexion">Connexion</Link>
        <Link href="/tests">Tests</Link>
        {version ? <span className="version">v{version}</span> : null}
      </nav>
    </header>
  );
}
