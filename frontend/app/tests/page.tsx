"use client";

import { useEffect, useState } from "react";
import { AppHeader } from "../../components/AppHeader";
import { LoadingButton } from "../../components/LoadingButton";
import { TestCard } from "../../components/TestCard";
import { api } from "../../lib/api";
import type { TestDefinition, TestResult } from "../../lib/types";

type GroupKey = "config" | "garmin" | "mcp" | "tunnel" | "chatgpt";

const GROUP_LABELS: Record<GroupKey, string> = {
  config: "PRÉ-REQUIS",
  garmin: "GARMIN",
  mcp: "MCP LOCAL",
  tunnel: "CLOUDFLARE",
  chatgpt: "CHATGPT",
};

const GROUP_PREFIXES: { key: GroupKey; prefix: string }[] = [
  { key: "config", prefix: "config-" },
  { key: "garmin", prefix: "garmin-" },
  { key: "mcp", prefix: "mcp-" },
  { key: "tunnel", prefix: "tunnel-" },
  { key: "chatgpt", prefix: "chatgpt-" },
];

function guessGroup(id: string): GroupKey {
  for (const { key, prefix } of GROUP_PREFIXES) {
    if (id.startsWith(prefix)) return key;
  }
  return "config";
}

export default function TestsPage() {
  const [tests, setTests] = useState<TestDefinition[]>([]);
  const [results, setResults] = useState<Record<string, TestResult>>({});
  const [running, setRunning] = useState<string | "all" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api.tests()
      .then((payload) => setTests(payload.tests))
      .catch((err) => setError(err instanceof Error ? err.message : "Erreur tests"));
  }, []);

  async function run(id: string) {
    setRunning(id);
    try {
      const result = await api.runTest(id);
      setResults((cur) => ({ ...cur, [id]: result }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test impossible");
    } finally {
      setRunning(null);
    }
  }

  async function runAll() {
    setRunning("all");
    try {
      const payload = await api.runAllTests();
      setResults(Object.fromEntries(payload.results.map((r) => [r.id, r])));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tests impossibles");
    } finally {
      setRunning(null);
    }
  }

  // Compute summary stats
  const values = Object.values(results);
  const okCount = values.filter((r) => r.state === "success").length;
  const failCount = values.filter((r) => r.state === "failed").length;
  const skipCount = values.filter((r) => r.state === "skipped" || r.state === "not_run").length;
  const runningCount = values.filter((r) => r.state === "running").length;
  const notRunCount = tests.length - values.length;

  // Group tests by prefix
  const grouped = new Map<GroupKey, TestDefinition[]>();
  for (const t of tests) {
    const g = guessGroup(t.id);
    if (!grouped.has(g)) grouped.set(g, []);
    grouped.get(g)!.push(t);
  }

  return (
    <main className="shell">
      <AppHeader />

      {/* Summary card */}
      <section className="card card-primary">
        <p className="section-label">DIAGNOSTICS GARMINTOGPT</p>
        <div className="row between" style={{ flexWrap: "wrap", gap: "var(--space-2)" }}>
          <div>
            <h2 style={{ fontSize: "1.25rem" }}>Vérification complète</h2>
            <p style={{ color: "var(--muted)", fontSize: "0.88rem", marginTop: "0.25rem" }}>
              Vérifie la configuration, Garmin MCP, le tunnel Cloudflare et l&rsquo;endpoint ChatGPT.
            </p>
          </div>
          <LoadingButton
            loading={running === "all"}
            onClick={() => void runAll()}
            className="primary-green"
          >
            Lancer tous les tests
          </LoadingButton>
        </div>
        <div className="test-summary-grid">
          <div className="test-stat stat-ok">
            <div className="test-stat-value">{okCount}</div>
            <div className="test-stat-label">OK</div>
          </div>
          <div className="test-stat stat-fail">
            <div className="test-stat-value">{failCount}</div>
            <div className="test-stat-label">Échecs</div>
          </div>
          <div className="test-stat stat-pending">
            <div className="test-stat-value">{notRunCount + skipCount}</div>
            <div className="test-stat-label">Non lancés</div>
          </div>
          <div className="test-stat stat-running">
            <div className="test-stat-value">{runningCount}</div>
            <div className="test-stat-label">En cours</div>
          </div>
        </div>
      </section>

      {error ? <p className="error-box">{error}</p> : null}

      {/* Grouped test cards */}
      <section className="test-list">
        {Array.from(grouped.entries()).map(([groupKey, groupTests]) => (
          <div key={groupKey}>
            <p className="test-section-label">{GROUP_LABELS[groupKey]}</p>
            {groupTests.map((def) => (
              <TestCard
                key={def.id}
                definition={def}
                result={results[def.id]}
                running={running === def.id}
                onRun={() => void run(def.id)}
              />
            ))}
          </div>
        ))}
      </section>

      <div className="action-bar-center" style={{ marginTop: "var(--space-2)" }}>
        <a className="button-link ghost" href="/">Retour vers l&rsquo;accueil</a>
      </div>
    </main>
  );
}
