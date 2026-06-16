"use client";

import { useEffect, useState } from "react";
import { AppHeader } from "../../components/AppHeader";
import { LoadingButton } from "../../components/LoadingButton";
import { TestCard } from "../../components/TestCard";
import { api } from "../../lib/api";
import type { TestDefinition, TestResult } from "../../lib/types";

export default function TestsPage() {
  const [tests, setTests] = useState<TestDefinition[]>([]);
  const [results, setResults] = useState<Record<string, TestResult>>({});
  const [running, setRunning] = useState<string | "all" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api.tests().then((payload) => setTests(payload.tests)).catch((err) => setError(err instanceof Error ? err.message : "Erreur tests"));
  }, []);

  async function run(id: string) {
    setRunning(id);
    try {
      const result = await api.runTest(id);
      setResults((current) => ({ ...current, [id]: result }));
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
      setResults(Object.fromEntries(payload.results.map((result) => [result.id, result])));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Tests impossibles");
    } finally {
      setRunning(null);
    }
  }

  return (
    <main className="shell">
      <AppHeader />
      <section className="status-strip card">
        <div>
          <p className="eyebrow">Diagnostics</p>
          <h2>Tests GarminToGPT</h2>
          <p>Vérifie la configuration, Garmin MCP, le tunnel Cloudflare et l’endpoint ChatGPT.</p>
        </div>
        <LoadingButton loading={running === "all"} onClick={() => void runAll()}>Lancer tous les tests</LoadingButton>
      </section>
      {error ? <p className="error-box">{error}</p> : null}
      <section className="test-list">
        {tests.map((definition) => (
          <TestCard key={definition.id} definition={definition} result={results[definition.id]} running={running === definition.id} onRun={() => void run(definition.id)} />
        ))}
      </section>
      <a className="button-link" href="/">Retour vers l’accueil</a>
    </main>
  );
}
