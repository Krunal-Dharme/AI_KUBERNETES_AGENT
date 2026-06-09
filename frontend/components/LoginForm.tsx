"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/lib/auth";

type Tab = "signin" | "signup" | "verify";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { signIn, signUp, verifyEmail, resendVerificationEmail } = useAuth();

  const [tab, setTab] = useState<Tab>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const status = searchParams.get("insforge_status");
    const type = searchParams.get("insforge_type");
    if (status === "success" && type === "verify_email") {
      setTab("signin");
      setInfo("Email verified! Sign in with your password.");
    }
    if (status === "error" && type === "verify_email") {
      setTab("verify");
      setError(searchParams.get("insforge_error") || "Verification failed.");
    }
  }, [searchParams]);

  const handleSignIn = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setInfo(null);
    setIsSubmitting(true);

    const result = await signIn(email, password);
    setIsSubmitting(false);

    if (result.status === "verify_required") {
      router.push(`/verify?email=${encodeURIComponent(email)}`);
      return;
    }
    if (result.status === "error") {
      if (result.message.toLowerCase().includes("verif")) {
        router.push(`/verify?email=${encodeURIComponent(email)}`);
        return;
      }
      setError(result.message);
      return;
    }
    router.push("/dashboard");
  };

  const handleSignUp = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setInfo(null);
    setIsSubmitting(true);

    const result = await signUp(email, password, name);
    setIsSubmitting(false);

    if (result.status === "verify_required") {
      router.push(`/verify?email=${encodeURIComponent(email)}`);
      return;
    }
    if (result.status === "error") {
      setError(result.message);
      return;
    }
    router.push("/dashboard");
  };

  const handleVerify = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setInfo(null);

    if (!email.trim()) {
      setError("Enter your email address.");
      return;
    }
    if (otp.trim().length !== 6) {
      setError("Enter the 6-digit code from your email.");
      return;
    }

    setIsSubmitting(true);
    const result = await verifyEmail(email.trim(), otp.trim());
    setIsSubmitting(false);

    if (result.status === "error") {
      setError(result.message);
      return;
    }

    setInfo("Email verified! You can now sign in.");
    setTab("signin");
    setOtp("");
  };

  const handleResend = async () => {
    if (!email.trim()) {
      setError("Enter your email address first.");
      return;
    }
    setError(null);
    setInfo(null);
    setIsSubmitting(true);
    const result = await resendVerificationEmail(email.trim());
    setIsSubmitting(false);
    if (result.status === "error") {
      setError(result.message);
      return;
    }
    setInfo("New code sent! Check your email.");
  };

  const tabClass = (active: boolean) =>
    `flex-1 rounded-md py-2.5 text-sm font-medium transition-colors ${
      active ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
    }`;

  return (
    <div className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-xl">
      <h1 className="text-center text-2xl font-bold text-white">AI Kubernetes Agent</h1>
      <p className="mt-2 text-center text-sm text-slate-400">
        Sign in to investigate your cluster
      </p>

      <a
        href="/verify"
        className="mt-4 block rounded-lg border-2 border-emerald-500 bg-emerald-950/40 px-4 py-3 text-center text-sm font-semibold text-emerald-300 hover:bg-emerald-950/60"
      >
        Have a verification code? Click here to verify your email
      </a>

      {/* 3 tabs - Verify Code is always visible */}
      <div className="mt-6 flex gap-1 rounded-lg bg-slate-950 p-1">
        <button type="button" onClick={() => setTab("signin")} className={tabClass(tab === "signin")}>
          Sign In
        </button>
        <button type="button" onClick={() => setTab("signup")} className={tabClass(tab === "signup")}>
          Sign Up
        </button>
        <button type="button" onClick={() => setTab("verify")} className={tabClass(tab === "verify")}>
          Verify Code
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-800 bg-red-950/50 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}
      {info && (
        <div className="mt-4 rounded-lg border border-blue-800 bg-blue-950/50 px-3 py-2 text-sm text-blue-200">
          {info}
        </div>
      )}

      {tab === "signin" && (
        <form onSubmit={handleSignIn} className="mt-6 space-y-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2.5 text-white outline-none focus:border-blue-500"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2.5 text-white outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg bg-blue-600 py-3 font-semibold text-white hover:bg-blue-500 disabled:opacity-60"
          >
            {isSubmitting ? "Please wait..." : "Sign In"}
          </button>
          <p className="text-center text-xs text-slate-500">
            Need to verify email?{" "}
            <button type="button" onClick={() => setTab("verify")} className="text-blue-400 underline">
              Go to Verify Code tab
            </button>
          </p>
        </form>
      )}

      {tab === "signup" && (
        <form onSubmit={handleSignUp} className="mt-6 space-y-4">
          <input
            type="text"
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2.5 text-white outline-none focus:border-blue-500"
          />
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2.5 text-white outline-none focus:border-blue-500"
          />
          <input
            type="password"
            placeholder="Password (min 6 characters)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2.5 text-white outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg bg-blue-600 py-3 font-semibold text-white hover:bg-blue-500 disabled:opacity-60"
          >
            {isSubmitting ? "Please wait..." : "Create Account"}
          </button>
          <p className="text-center text-xs text-slate-500">
            After sign up, use the{" "}
            <button type="button" onClick={() => setTab("verify")} className="text-blue-400 underline">
              Verify Code tab
            </button>{" "}
            to enter your 6-digit code.
          </p>
        </form>
      )}

      {tab === "verify" && (
        <form onSubmit={handleVerify} className="mt-6 space-y-4">
          <div className="rounded-lg border-2 border-emerald-600/50 bg-emerald-950/30 px-4 py-3">
            <p className="text-sm font-medium text-emerald-300">Enter your 6-digit verification code</p>
            <p className="mt-1 text-xs text-slate-400">
              Check your email inbox for the code sent by InsForge after sign up.
            </p>
          </div>

          <input
            type="email"
            placeholder="Your email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2.5 text-white outline-none focus:border-blue-500"
          />

          <input
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="000000"
            value={otp}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
            maxLength={6}
            required
            autoFocus
            className="w-full rounded-lg border-2 border-emerald-500 bg-slate-950 px-3 py-4 text-center text-2xl font-bold tracking-[0.5em] text-white outline-none focus:border-emerald-400"
          />

          <button
            type="submit"
            disabled={isSubmitting || otp.length !== 6}
            className="w-full rounded-lg bg-emerald-600 py-3 font-semibold text-white hover:bg-emerald-500 disabled:opacity-60"
          >
            {isSubmitting ? "Verifying..." : "Verify Email"}
          </button>

          <button
            type="button"
            onClick={handleResend}
            disabled={isSubmitting}
            className="w-full rounded-lg border border-slate-600 py-2.5 text-sm text-slate-300 hover:border-slate-500 disabled:opacity-60"
          >
            Resend verification code
          </button>
        </form>
      )}
    </div>
  );
}
