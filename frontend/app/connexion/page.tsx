"use client";

import { useCallback, useEffect, useState } from "react";
import { AppHeader } from "../../components/AppHeader";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { LoadingButton } from "../../components/LoadingButton";
import { StatusBadge } from "../../components/StatusBadge";
import { api } from "../../lib/api";
import { formatDate, formatDay } from "../../lib/format";
import type {
  GarminAuthResult,
  GarminAuthStatus,
  RotationSource,
} from "../../lib/types";

const KEY_PAGE = "https://connect.garmin.com/app/settings/personalApiToken";

const ROTATION_SOURCE_LABEL: Record<RotationSource, string> = {
  declared: "date déclarée",
  observed: "détectée par Garmin",
  unknown: "inconnue",
};

export default function ConnexionPage() {
  const [auth, setAuth] = useState<GarminAuthStatus | null>(null);
  const [result, setResult] = useState<GarminAuthResult | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [newKeyExpiresOn, setNewKeyExpiresOn] = useState("");
  const [rotationDraft, setRotationDraft] = useState("");
  const [editing, setEditing] = useState(false);
  const [editingExpiry, setEditingExpiry] = useState(false);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [savingExpiry, setSavingExpiry] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const applyStatus = useCallback((status: GarminAuthStatus) => {
    setAuth(status);
    setRotationDraft(status.rotation.expires_on ?? "");
  }, []);

  const loadAuth = useCallback(async () => {
    const status = await api.authStatus();
    setAuth(status);
    setRotationDraft(status.rotation.expires_on ?? "");
    setEditing(!status.configured);
    setNewKeyExpiresOn("");
    if (status.state === "configured") {
      const verified = await api.verifyAuth();
      applyStatus(verified);
    }
  }, [applyStatus]);

  useEffect(() => {
    void loadAuth().catch((err) =>
      setError(err instanceof Error ? err.message : "Impossible de charger l'état Garmin"),
    );
  }, [loadAuth]);

  async function saveKey() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await api.configureKey({
        api_key: apiKey,
        expires_on: newKeyExpiresOn || null,
      });
      applyStatus(response.status);
      setResult(response);
      setApiKey("");
      setNewKeyExpiresOn("");
      setEditing(false);
      setEditingExpiry(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Clé API refusée");
    } finally {
      setLoading(false);
    }
  }

  async function verify() {
    setVerifying(true);
    setError(null);
    setResult(null);
    try {
      applyStatus(await api.verifyAuth());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Vérification impossible");
    } finally {
      setVerifying(false);
    }
  }

  async function saveExpiration(value: string | null) {
    setSavingExpiry(true);
    setError(null);
    try {
      const status = await api.updateKeyExpiration(value);
      applyStatus(status);
      setEditingExpiry(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Date d'expiration refusée");
    } finally {
      setSavingExpiry(false);
    }
  }

  async function removeKey() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await api.removeKey();
      applyStatus(response.status);
      setResult(response);
      setEditing(true);
      setApiKey("");
      setNewKeyExpiresOn("");
      setRotationDraft("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suppression impossible");
    } finally {
      setLoading(false);
      setConfirmDelete(false);
    }
  }

  if (!auth) {
    return (
      <main className="shell narrow">
        <AppHeader />
        <section className="card card-primary">
          <p className="section-label">CONNEXION GARMIN</p>
          <p style={{ color: "var(--muted)" }}>Chargement de l&rsquo;état de la clé API…</p>
        </section>
      </main>
    );
  }

  const configured = auth.configured;
  const sourceLabel =
    auth.key.source === "env" ? "variable d'environnement" : "fichier officiel Garmin";

  return (
    <main className="shell narrow">
      <AppHeader />

      <section className="card card-primary">
        <p className="section-label">CONNEXION GARMIN</p>
        <div className="row between" style={{ gap: "var(--space-2)", flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: "18rem" }}>
            <h2 style={{ fontSize: "1.3rem", marginBottom: "0.5rem" }}>
              {configured ? "Clé Personal API Garmin" : "Connecter Garmin avec une clé API"}
            </h2>
            <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
              GarminToGPT utilise la Personal API officielle de Garmin. Aucun mot de passe
              Garmin n&rsquo;est demandé : la clé est échangée contre un jeton de 24&nbsp;h.
            </p>
          </div>
          <StatusBadge state={auth.state} />
        </div>

        <div className="info-callout" style={{ marginTop: "var(--space-3)" }}>
          <span className="info-callout-icon">ℹ</span>
          <span>
            La clé n&rsquo;est jamais renvoyée à l&rsquo;interface. Elle est stockée dans le
            fichier officiel Garmin (<code>~/.config/garmin/connect-personal-api-key</code>)
            avec des permissions restreintes.
          </span>
        </div>

        {error ? <p className="error-box">{error}</p> : null}
        {result ? <p className="success-box">{result.message}</p> : null}

        {!configured ? (
          <div style={{ marginTop: "var(--space-3)" }}>
            <ol style={{ marginLeft: "1.2rem", color: "var(--muted)", fontSize: "0.88rem" }}>
              <li>
                Ouvre{" "}
                <a href={KEY_PAGE} target="_blank" rel="noreferrer">
                  Garmin Connect → Personal API
                </a>
                .
              </li>
              <li>Crée une clé et choisis sa durée de vie (30, 90, 180 ou 365 jours).</li>
              <li>Copie la clé immédiatement : Garmin ne l&rsquo;affiche qu&rsquo;une fois.</li>
              <li>Colle-la ci-dessous, puis vérifie la connexion.</li>
            </ol>
            <KeyForm
              apiKey={apiKey}
              setApiKey={setApiKey}
              expiresOn={newKeyExpiresOn}
              setExpiresOn={setNewKeyExpiresOn}
              loading={loading}
              onSubmit={saveKey}
              submitLabel="Tester et enregistrer"
            />
          </div>
        ) : null}
      </section>

      {configured ? (
        <>
          <section className="card">
            <div className="row between" style={{ gap: "var(--space-2)", flexWrap: "wrap" }}>
              <div>
                <p className="section-label">ÉTAT DE LA CLÉ</p>
                <h2 style={{ fontSize: "1.15rem" }}>
                  {auth.display_name ? `Compte ${auth.display_name}` : "Compte Garmin"}
                </h2>
              </div>
              <StatusBadge state={auth.state} />
            </div>

            <p
              className={
                auth.state === "error" || auth.state === "expired"
                  ? "error-box"
                  : auth.state === "expiring_soon"
                    ? "warning-box"
                    : ""
              }
              style={{ color: "var(--muted)", fontSize: "0.88rem" }}
            >
              {auth.message}
            </p>

            <div className="details-grid">
              <div className="details-item">
                <span className="details-label">Clé</span>
                <span className="details-value">{auth.key.hint ?? "absente"}</span>
              </div>
              <div className="details-item">
                <span className="details-label">Source</span>
                <span className="details-value">{sourceLabel}</span>
              </div>
              <div className="details-item">
                <span className="details-label">Token</span>
                <span className="details-value">
                  {auth.token_expires_at ? `expire le ${formatDate(auth.token_expires_at)}` : "aucun jeton en cache"}
                </span>
              </div>
              <div className="details-item">
                <span className="details-label">Dernière vérification</span>
                <span className="details-value">{formatDate(auth.last_verified_at)}</span>
              </div>
              <div className="details-item">
                <span className="details-label">Rotation de la clé</span>
                <span className="details-value">
                  {formatDay(auth.rotation.expires_on)} · {ROTATION_SOURCE_LABEL[auth.rotation.source]}
                  {auth.rotation.days_remaining !== null
                    ? ` · ${auth.rotation.days_remaining} jour(s)`
                    : ""}
                </span>
              </div>
              <div className="details-item">
                <span className="details-label">Scopes</span>
                <span className="details-value">
                  {auth.token_scopes.length > 0 ? auth.token_scopes.join(", ") : "non disponibles"}
                </span>
              </div>
            </div>

            {auth.key.source === "env" ? (
              <p className="warning-box" style={{ marginTop: "var(--space-2)" }}>
                La clé provient de <code>GARMIN_PERSONAL_API_KEY</code>, qui est prioritaire.
                Retire cette variable d&rsquo;environnement pour gérer la clé depuis cette page.
              </p>
            ) : null}

            <div className="row wrap" style={{ marginTop: "var(--space-3)" }}>
              <LoadingButton loading={verifying} onClick={() => void verify()} className="secondary">
                Vérifier maintenant
              </LoadingButton>
              <button className="secondary" onClick={() => setEditing((value) => !value)}>
                {editing ? "Annuler la mise à jour" : "Mettre à jour la clé"}
              </button>
              <button className="danger" onClick={() => setConfirmDelete(true)} disabled={loading}>
                Supprimer la clé
              </button>
            </div>
          </section>

          {editing ? (
            <section className="card">
              <p className="section-label">NOUVELLE CLÉ</p>
              <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                La nouvelle clé est vérifiée auprès de Garmin avant d&rsquo;être enregistrée.
                L&rsquo;ancienne clé reste active si la vérification échoue.
              </p>
              <KeyForm
                apiKey={apiKey}
                setApiKey={setApiKey}
                expiresOn={newKeyExpiresOn}
                setExpiresOn={setNewKeyExpiresOn}
                loading={loading}
                onSubmit={saveKey}
                submitLabel="Vérifier et remplacer"
              />
            </section>
          ) : null}

          <section className="card">
            <p className="section-label">DATE DE ROTATION</p>
            <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
              Garmin ne permet pas de lire la date d&rsquo;expiration de la clé par API.
              Renseigne la date affichée dans Garmin Connect pour un compte à rebours exact.
              Elle est détectée automatiquement quand Garmin renvoie un jeton plus court que 24&nbsp;h.
            </p>
            {editingExpiry ? (
              <div className="row wrap" style={{ marginTop: "var(--space-2)" }}>
                <label style={{ flex: 1, minWidth: "14rem" }}>
                  Date d&rsquo;expiration
                  <input
                    type="date"
                    value={rotationDraft}
                    onChange={(event) => setRotationDraft(event.target.value)}
                  />
                </label>
                <LoadingButton
                  loading={savingExpiry}
                  onClick={() => void saveExpiration(rotationDraft || null)}
                  className="primary-green"
                >
                  Enregistrer la date
                </LoadingButton>
                <button
                  className="secondary"
                  onClick={() => {
                    setRotationDraft("");
                    void saveExpiration(null);
                  }}
                  disabled={savingExpiry}
                >
                  Effacer
                </button>
              </div>
            ) : (
              <div className="row wrap" style={{ marginTop: "var(--space-2)" }}>
                <span className="details-value">
                  {formatDay(auth.rotation.expires_on)} ({ROTATION_SOURCE_LABEL[auth.rotation.source]})
                </span>
                <button className="secondary" onClick={() => setEditingExpiry(true)}>
                  Modifier la date
                </button>
              </div>
            )}
          </section>
        </>
      ) : null}

      <div className="action-bar-center" style={{ marginTop: "var(--space-2)" }}>
        <a className="button-link ghost" href="/">Retour vers l&rsquo;accueil</a>
        <a className="button-link ghost" href="/tests">Ouvrir les tests</a>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        title="Supprimer la clé API Garmin ?"
        message="La clé locale sera supprimée et le pont MCP/Cloudflare sera arrêté. Tu pourras enregistrer une nouvelle clé à tout moment."
        confirmLabel="Supprimer"
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => void removeKey()}
      />
    </main>
  );
}

function KeyForm({
  apiKey,
  setApiKey,
  expiresOn,
  setExpiresOn,
  loading,
  onSubmit,
  submitLabel,
}: {
  apiKey: string;
  setApiKey: (value: string) => void;
  expiresOn: string;
  setExpiresOn: (value: string) => void;
  loading: boolean;
  onSubmit: () => void;
  submitLabel: string;
}) {
  return (
    <div style={{ marginTop: "var(--space-3)" }}>
      <div className="form-grid">
        <label>
          Clé API Garmin
          <input
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            autoComplete="off"
            spellCheck={false}
            placeholder="GCDC_…"
          />
        </label>
        <label>
          Date d&rsquo;expiration (optionnelle)
          <input
            type="date"
            value={expiresOn}
            onChange={(event) => setExpiresOn(event.target.value)}
          />
        </label>
      </div>
      <div className="row wrap" style={{ marginTop: "var(--space-3)" }}>
        <LoadingButton
          loading={loading}
          onClick={onSubmit}
          className="primary-green"
          disabled={apiKey.trim().length === 0}
        >
          {submitLabel}
        </LoadingButton>
      </div>
    </div>
  );
}
