import type { LogResult } from "../lib/types";

export function LogsModal({ service, logs, onClose, onRefresh }: { service: string | null; logs: LogResult | null; onClose: () => void; onRefresh: () => void }) {
  if (!service) return null;
  const content = logs?.lines.join("\n") ?? "Chargement...";
  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal wide" role="dialog" aria-modal="true" aria-label={`Logs ${service}`}>
        <div className="modal-title-row">
          <h2>Logs {service}</h2>
          <div className="row">
            <button className="secondary" onClick={() => navigator.clipboard?.writeText(content)}>Copier</button>
            <button className="secondary" onClick={onRefresh}>Rafraîchir</button>
            <button onClick={onClose}>Fermer</button>
          </div>
        </div>
        <pre className="logs">{content}</pre>
      </section>
    </div>
  );
}
