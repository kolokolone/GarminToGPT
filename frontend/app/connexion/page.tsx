"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppHeader } from "../../components/AppHeader";
import { LoadingButton } from "../../components/LoadingButton";
import { StatusBadge } from "../../components/StatusBadge";
import { api } from "../../lib/api";
import { commandToString } from "../../lib/format";
import type { GarminAuthResult, GarminAuthStatus } from "../../lib/types";

export default function ConnexionPage() {
  const router = useRouter();
  const [auth, setAuth] = useState<GarminAuthStatus | null>(null);
  const [result, setResult] = useState<GarminAuthResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function loadAuth() {
    const status = await api.authStatus();
    setAuth(status);
    if (status.token_valid) router.push("/");
  }

  useEffect(() => {
    void loadAuth().catch((err) => setError(err instanceof Error ? err.message : "Erreur auth"));
  }, []);

  async function submit() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await api.login({ email, password, otp });
      setResult(response);
      setAuth(response.status);
      if (response.ok) {
        setPassword("");
        setOtp("");
        router.push("/");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connexion impossible");
    } finally {
      setLoading(false);
    }
  }

  async function verifyAndStart() {
    setLoading(true);
    try {
      const authStatus = await api.verifyAuth();
      setAuth(authStatus);
      if (authStatus.token_valid) {
        await api.startMcp();
        await api.startTunnel();
        router.push("/");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Vérification impossible");
    } finally {
      setLoading(false);
    }
  }

  const needsOtp = result?.needs_otp ?? false;
  const assisted = result?.assisted ?? false;

  return (
    <main className="shell narrow">
      <AppHeader />
      <section className="card card-primary">
        <p className="section-label">COMPTE GARMIN</p>
        <h2 style={{ fontSize: "1.3rem", marginBottom: "0.5rem" }}>
          {needsOtp ? "Saisis le code de vérification" : "Connecter ton compte Garmin"}
        </h2>
        <p style={{ color: "var(--muted)", fontSize: "0.88rem", marginBottom: "var(--space-3)" }}>
          GarminToGPT utilise l&rsquo;authentification Garmin MCP locale pour vérifier l&rsquo;accès à Garmin Connect.
        </p>

        {/* Security info callout */}
        <div className="info-callout" style={{ marginBottom: "var(--space-3)" }}>
          <span className="info-callout-icon">ℹ</span>
          <span>
            GarminToGPT ne stocke pas le mot de passe. Les identifiants sont transmis temporairement à l&rsquo;outil
            d&rsquo;authentification Garmin officiel.
          </span>
        </div>

        {auth ? <StatusBadge state={auth.state} /> : null}
        {error ? <p className="error-box">{error}</p> : null}

        {result?.message && !assisted ? (
          <p className={needsOtp ? "warning-box" : ""} style={{ marginBottom: "var(--space-2)" }}>
            {result.message}
          </p>
        ) : null}

        <div className="form-grid">
          <label>
            Email Garmin
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              disabled={needsOtp}
            />
          </label>
          <label>
            Mot de passe Garmin
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              autoComplete="current-password"
              disabled={needsOtp}
            />
          </label>
          <label>
            Code de confirmation / OTP
            <input
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              autoComplete="one-time-code"
              autoFocus={needsOtp}
              placeholder={needsOtp ? "Entre le code reçu par email" : "Optionnel — nécessaire si 2FA activé"}
            />
          </label>
        </div>

        <div className="row wrap" style={{ marginTop: "var(--space-3)" }}>
          <LoadingButton loading={loading} onClick={() => void submit()}>
            {needsOtp ? "Vérifier le code" : "Se connecter à Garmin"}
          </LoadingButton>
          {!needsOtp ? (
            <LoadingButton className="secondary" loading={loading} onClick={() => void verifyAndStart()}>
              Vérifier puis démarrer
            </LoadingButton>
          ) : null}
        </div>

        {needsOtp ? (
          <p style={{ marginTop: "var(--space-2)", fontSize: "0.82rem" }}>
            <span
              className="pseudolink"
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === "Enter") { setResult(null); setOtp(""); } }}
              onClick={() => { setResult(null); setOtp(""); }}
              style={{ cursor: "pointer", color: "var(--blue)", textDecoration: "underline" }}
            >
              ← Utiliser d&rsquo;autres identifiants
            </span>
          </p>
        ) : null}

        {assisted && result ? (
          <div className="command-box" style={{ marginTop: "var(--space-3)" }}>
            <p>{result.message}</p>
            <code>{commandToString(result.command)}</code>
          </div>
        ) : null}
      </section>
    </main>
  );
}
