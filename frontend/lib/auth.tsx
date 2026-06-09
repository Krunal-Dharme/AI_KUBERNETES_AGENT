"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  type AuthResult,
  extractErrorMessage,
  isVerificationRequired,
} from "@/lib/auth-utils";
import { insforge } from "@/lib/insforge";

interface AuthUser {
  id: string;
  email: string;
  profile?: { name?: string };
}

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<AuthResult>;
  signUp: (email: string, password: string, name: string) => Promise<AuthResult>;
  verifyEmail: (email: string, otp: string) => Promise<AuthResult>;
  resendVerificationEmail: (email: string) => Promise<AuthResult>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function mapUser(user: {
  id: string;
  email: string;
  profile?: { name?: string } | null;
}): AuthUser {
  return {
    id: user.id,
    email: user.email,
    profile: user.profile ? { name: user.profile.name } : undefined,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const { data, error } = await insforge.auth.getCurrentUser();
      if (error || !data?.user) {
        setUser(null);
        return;
      }
      setUser(mapUser(data.user));
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refreshUser().finally(() => setIsLoading(false));
  }, [refreshUser]);

  const signIn = useCallback(async (email: string, password: string): Promise<AuthResult> => {
    try {
      const { data, error } = await insforge.auth.signInWithPassword({
        email,
        password,
      });

      if (isVerificationRequired(error, data)) {
        return {
          status: "verify_required",
          message: extractErrorMessage(error) || "Email verification required.",
        };
      }

      if (error) {
        return { status: "error", message: extractErrorMessage(error) };
      }

      if (data?.user) {
        setUser(mapUser(data.user));
      }
      return { status: "success" };
    } catch (err) {
      if (isVerificationRequired(err)) {
        return {
          status: "verify_required",
          message: extractErrorMessage(err),
        };
      }
      return { status: "error", message: extractErrorMessage(err) };
    }
  }, []);

  const signUp = useCallback(
    async (email: string, password: string, name: string): Promise<AuthResult> => {
      try {
        const { data, error } = await insforge.auth.signUp({
          email,
          password,
          name,
          redirectTo: `${window.location.origin}/login`,
        });

        if (error) {
          return { status: "error", message: extractErrorMessage(error) };
        }

        if (isVerificationRequired(null, data) || !data?.accessToken) {
          return {
            status: "verify_required",
            message: "Account created. Enter the 6-digit code sent to your email.",
          };
        }

        if (data?.user) {
          setUser(mapUser(data.user));
        }
        return { status: "success" };
      } catch (err) {
        return { status: "error", message: extractErrorMessage(err) };
      }
    },
    [],
  );

  const verifyEmail = useCallback(async (email: string, otp: string): Promise<AuthResult> => {
    try {
      const { data, error } = await insforge.auth.verifyEmail({ email, otp });
      if (error) {
        return { status: "error", message: extractErrorMessage(error) };
      }
      if (data?.user) {
        setUser(mapUser(data.user));
      }
      return { status: "success" };
    } catch (err) {
      return { status: "error", message: extractErrorMessage(err) };
    }
  }, []);

  const resendVerificationEmail = useCallback(async (email: string): Promise<AuthResult> => {
    try {
      const { data, error } = await insforge.auth.resendVerificationEmail({
        email,
        redirectTo: `${window.location.origin}/login`,
      });
      if (error) {
        return { status: "error", message: extractErrorMessage(error) };
      }
      if (data?.success) {
        return { status: "success" };
      }
      return { status: "error", message: "Failed to resend verification code" };
    } catch (err) {
      return { status: "error", message: extractErrorMessage(err) };
    }
  }, []);

  const signOut = useCallback(async () => {
    await insforge.auth.signOut();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      isLoading,
      signIn,
      signUp,
      verifyEmail,
      resendVerificationEmail,
      signOut,
      refreshUser,
    }),
    [user, isLoading, signIn, signUp, verifyEmail, resendVerificationEmail, signOut, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
