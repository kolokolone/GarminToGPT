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
    try {
      const response = await api.login({ email, password, otp });
      setPassword("");
      setResult(response);
      setAuth(response.status);
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

  return (
    <main className="shell narrow">
      <AppHeader />
      <section className="card card-primary">
        <p className="section-label">COMPTE GARMIN</p>
        <h2 style={{ fontSize: "1.3rem", marginBottom: "0.5rem" }}>
          Connecter ton compte Garmin
        </h2>
        <p style={{ color: "var(--muted)", fontSize: "0.88rem", marginBottom: "var(--space-3)" }}>
          GarminToGPT utilise l&rsquo;authentification Garmin MCP locale pour vérifier l&rsquo;accès à Garmin Connect.
        </p>

        {/* Security info callout BEFORE the form */}
        <div className="info-callout" style={{ marginBottom: "var(--space-3)" }}>
          <span className="info-callout-icon">ℹ</span>
          <span>
            GarminToGPT ne stocke pas le mot de passe. Si la CLI officielle est interactive, l&rsquo;interface affiche une procédure assistée plutôt que de simuler une API fragile.
          </span>
        </div>

        {auth ? <StatusBadge state={auth.state} /> : null}
        {error ? <p className="error-box">{error}</p> : null}

        <div className="form-grid">
          <label>
            Email Garmin
            <input value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
          </label>
          <label>
            Mot de passe Garmin
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" autoComplete="current-password" />
          </label>
          <label>
            Code de confirmation / OTP
            <input value={otp} onChange={(e) => setOtp(e.target.value)} autoComplete="one-time-code" />
          </label>
        </div>

        <div className="row wrap" style={{ marginTop: "var(--space-3)" }}>
          <LoadingButton loading={loading} onClick={() => void submit()}>
            Se connecter à Garmin
          </LoadingButton>
          <LoadingButton className="secondary" loading={loading} onClick={() => void verifyAndStart()}>
            Vérifier puis démarrer
          </LoadingButton>
        </div>

        {result?.assisted ? (
          <div className="command-box" style={{ marginTop: "var(--space-3)" }}>
            <p>{result.message}</p>
            <code>{commandToString(result.command)}</code>
          </div>
        ) : null}
      </section>
    </main>
  );
}
