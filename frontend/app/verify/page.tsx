"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/lib/auth";

function VerifyContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { verifyEmail, resendVerificationEmail } = useAuth();

  const [email, setEmail] = useState(searchParams.get("email") || "");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

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

    setInfo("Email verified! Redirecting to sign in...");
    setTimeout(() => router.push("/login"), 1500);
  };

  const handleResend = async () => {
    if (!email.trim()) {
      setError("Enter your email address first.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    const result = await resendVerificationEmail(email.trim());
    setIsSubmitting(false);
    if (result.status === "error") {
      setError(result.message);
      return;
    }
    setInfo("New verification code sent! Check your email.");
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-8">
      <div className="w-full max-w-md rounded-xl border-2 border-emerald-600 bg-slate-900 p-6 shadow-xl">
        <h1 className="text-center text-2xl font-bold text-white">Verify Your Email</h1>
        <p className="mt-2 text-center text-sm text-slate-400">
          Enter the 6-digit code sent to your email
        </p>

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

        <form onSubmit={handleVerify} className="mt-6 space-y-4">
          <input
            type="email"
            placeholder="Your email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2.5 text-white outline-none focus:border-emerald-500"
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
            className="w-full rounded-lg border-2 border-emerald-500 bg-slate-950 px-3 py-4 text-center text-2xl font-bold tracking-[0.5em] text-white outline-none"
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
            className="w-full rounded-lg border border-slate-600 py-2.5 text-sm text-slate-300 hover:border-slate-500"
          >
            Resend code
          </button>

          <a href="/login" className="block text-center text-sm text-blue-400 hover:underline">
            Back to Sign In
          </a>
        </form>
      </div>
    </main>
  );
}

export default function VerifyPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
          Loading...
        </div>
      }
    >
      <VerifyContent />
    </Suspense>
  );
}
