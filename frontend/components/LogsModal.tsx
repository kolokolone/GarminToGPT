"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { LogResult } from "../lib/types";

export function LogsModal({
  service,
  logs,
  onClose,
  onRefresh,
  error,
}: {
  service: string | null;
  logs: LogResult | null;
  onClose: () => void;
  onRefresh: () => void;
  error?: string | null;
}) {
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState("");
  const logsRef = useRef<HTMLPreElement>(null);

  // Derived state — safe before any conditional return
  const allLines = logs?.lines ?? [];
  const filteredLines = filter
    ? allLines.filter((line) => line.toLowerCase().includes(filter.toLowerCase()))
    : allLines;
  const content = filteredLines.join("\n") || "(aucune ligne correspondante)";

  // ── All hooks MUST live before the early return ──

  // Auto-scroll when new content arrives
  useEffect(() => {
    if (autoScroll && logsRef.current) {
      logsRef.current.scrollTop = logsRef.current.scrollHeight;
    }
  }, [content, autoScroll]);

  const handleScroll = useCallback(() => {
    if (!logsRef.current) return;
    const el = logsRef.current;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    if (!atBottom) setAutoScroll(false);
  }, []);

  const toggleAutoScroll = useCallback(() => {
    setAutoScroll((prev) => {
      const next = !prev;
      if (next && logsRef.current) {
        logsRef.current.scrollTop = logsRef.current.scrollHeight;
      }
      return next;
    });
  }, []);

  const handleCopy = useCallback(() => {
    navigator.clipboard?.writeText(allLines.join("\n"));
  }, [allLines]);

  // Early return after all hooks — non-négociable pour React
  if (!service) return null;

  const hasError = !!error;

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal wide" role="dialog" aria-modal="true" aria-label={`Logs ${service}`}>
        <div className="modal-header">
          <h2>Logs {service}</h2>
          <div className="row">
            <button className="secondary" onClick={handleCopy}>Copier</button>
            <button className="secondary" onClick={onRefresh}>Rafraîchir</button>
            <button onClick={onClose}>Fermer</button>
          </div>
        </div>
        <div className="modal-body">
          <input
            type="text"
            placeholder="Filtrer les logs…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{ marginBottom: "var(--space-2)", width: "100%" }}
          />
          <pre
            ref={logsRef}
            className="logs"
            onScroll={handleScroll}
            tabIndex={0}
          >
            {content}
          </pre>
        </div>
        <div className="row wrap" style={{ marginTop: "var(--space-2)", justifyContent: "space-between" }}>
          <span style={{ fontSize: "0.78rem", color: "var(--muted)" }}>
            {hasError ? <span style={{ color: "var(--red)" }}>Erreur : {error}</span> : null}
            {filteredLines.length} ligne{filteredLines.length !== 1 ? "s" : ""}
            {filter ? ` (filtré sur ${allLines.length})` : ""}
          </span>
          <button
            className={`secondary ${autoScroll ? "" : ""}`}
            onClick={toggleAutoScroll}
            style={autoScroll ? { background: "var(--gray-light)" } : {}}
          >
            {autoScroll ? "Suivre les logs" : "Autoscroll désactivé"}
          </button>
        </div>
      </section>
    </div>
  );
}
