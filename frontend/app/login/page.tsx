"use client";

import { Suspense, useEffect } from "react";
import { useRouter } from "next/navigation";

import { LoginForm } from "@/components/LoginForm";
import { useAuth } from "@/lib/auth";

function LoginContent() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user) {
      router.replace("/dashboard");
    }
  }, [user, isLoading, router]);

  if (isLoading || user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        Loading...
      </div>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-8">
      <LoginForm />
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
          Loading...
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
