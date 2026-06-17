"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function AppHeader({ version }: { version?: string }) {
  const pathname = usePathname();

  const isActive = (href: string) => pathname === href;

  return (
    <header className="app-header">
      <div className="app-header-left">
        <p className="app-header-eyebrow">PONT MCP LOCAL</p>
        <h1 className="app-header-title">GarminToGPT</h1>
        <p className="app-header-subtitle">Pont local entre Garmin Connect, garmin-mcp et ChatGPT.</p>
      </div>
      <nav className="app-header-nav" aria-label="Navigation principale">
        <Link href="/" className={isActive("/") ? "active" : ""}>Accueil</Link>
        <Link href="/connexion" className={isActive("/connexion") ? "active" : ""}>Garmin</Link>
        <Link href="/tests" className={isActive("/tests") ? "active" : ""}>Tests</Link>
        {version ? <span className="version-badge">v{version}</span> : null}
      </nav>
    </header>
  );
}
