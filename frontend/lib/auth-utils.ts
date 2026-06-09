export type AuthResult =
  | { status: "success" }
  | { status: "verify_required"; message: string }
  | { status: "error"; message: string };

interface InsForgeLikeError {
  message?: string;
  error?: string;
  statusCode?: number;
}

export function extractErrorMessage(error: unknown): string {
  if (!error) return "Something went wrong";
  if (typeof error === "string") return error;
  if (error instanceof Error) return error.message;
  const obj = error as InsForgeLikeError;
  return obj.message || "Something went wrong";
}

export function isVerificationRequired(
  error: unknown,
  data?: {
    requireEmailVerification?: boolean;
    accessToken?: string | null;
    user?: { emailVerified?: boolean } | null;
  } | null,
): boolean {
  if (data?.requireEmailVerification) return true;
  if (data?.user && data.user.emailVerified === false && !data?.accessToken) {
    return true;
  }

  if (!error) return false;

  const obj = error as InsForgeLikeError;
  const code = String(obj.error || "").toUpperCase();
  const message = extractErrorMessage(error).toLowerCase();

  return (
    code.includes("VERIF") ||
    code.includes("EMAIL_NOT_VERIFIED") ||
    message.includes("verif") ||
    message.includes("not verified")
  );
}
