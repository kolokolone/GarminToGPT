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
      const status = await api.verifyAuth();
      setAuth(status);
      if (status.token_valid) {
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
      <section className="card hero-card">
        <p className="eyebrow">Connexion Garmin</p>
        <h2>Connecte ton compte Garmin à ChatGPT via un pont MCP local sécurisé.</h2>
        <p>L'application lance Garmin MCP localement, expose un endpoint MCP via Cloudflare Tunnel, puis fournit une URL HTTPS à utiliser dans ChatGPT.</p>
        {auth ? <StatusBadge state={auth.state} /> : null}
        {error ? <p className="error-box">{error}</p> : null}
        <div className="form-grid">
          <label>Email Garmin<input value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" /></label>
          <label>Mot de passe Garmin<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" /></label>
          <label>Code de confirmation / OTP<input value={otp} onChange={(event) => setOtp(event.target.value)} autoComplete="one-time-code" /></label>
        </div>
        <p className="warning">GarminToGPT ne stocke pas le mot de passe. Si la CLI officielle est interactive, l’UI affiche une procédure assistée au lieu de simuler une API fragile.</p>
        <div className="row wrap">
          <LoadingButton loading={loading} onClick={() => void submit()}>Se connecter à Garmin</LoadingButton>
          <LoadingButton className="secondary" loading={loading} onClick={() => void verifyAndStart()}>Vérifier puis démarrer</LoadingButton>
        </div>
        {result?.assisted ? (
          <div className="command-box">
            <p>{result.message}</p>
            <code>{commandToString(result.command)}</code>
          </div>
        ) : null}
      </section>
    </main>
  );
}
