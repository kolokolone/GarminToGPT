import type { TestDefinition, TestResult } from "../lib/types";
import { LoadingButton } from "./LoadingButton";
import { StatusBadge } from "./StatusBadge";

export function TestCard({ definition, result, running, onRun }: { definition: TestDefinition; result?: TestResult; running: boolean; onRun: () => void }) {
  return (
    <article className="card test-card">
      <div>
        <div className="card-title-row">
          <h2>{definition.name}</h2>
          <StatusBadge state={result?.state ?? "not_run"} />
        </div>
        <p>{definition.description}</p>
        {result ? (
          <p className="result-text">
            {result.message} {result.suggestion ? <strong>Suggestion: {result.suggestion}</strong> : null}
          </p>
        ) : null}
      </div>
      <LoadingButton loading={running} onClick={onRun}>Lancer</LoadingButton>
    </article>
  );
}
