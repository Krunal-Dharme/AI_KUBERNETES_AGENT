import type { Diagnosis, Finding } from "@/types/investigation";

const MAX_EVIDENCE = 3;
const MAX_COMMANDS = 3;
const MAX_VERIFICATION = 3;
const MAX_TEXT = 200;
const MAX_ANALYSIS_LINES = 4;

/** Never iterate a string character-by-character — always produce string[]. */
export function toTextLines(
  value: unknown,
  maxItems = MAX_EVIDENCE,
  maxLen = MAX_TEXT,
): string[] {
  if (value == null) return [];

  let items: string[];

  if (Array.isArray(value)) {
    items = value.map((v) => (v == null ? "" : String(v)));
  } else if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return [];
    items = trimmed.includes("; ") ? trimmed.split("; ") : [trimmed];
  } else {
    items = [String(value)];
  }

  // Repair accidental per-character arrays (e.g. string spread into list)
  if (items.length > 8 && items.every((s) => s.length <= 1)) {
    items = [items.join("")];
  }

  return items
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => truncate(s, maxLen))
    .slice(0, maxItems);
}

/** Render confidence_reasoning as bullet lines — supports string or string[]. */
export function toBulletLines(value: unknown, maxItems = 6): string[] {
  if (value == null) return [];

  if (Array.isArray(value)) {
    const flat = value.flatMap((item) => toBulletLines(item, maxItems));
    return flat.slice(0, maxItems);
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return [];
    if (trimmed.includes("; ")) {
      return trimmed
        .split("; ")
        .map((s) => s.trim())
        .filter(Boolean)
        .slice(0, maxItems);
    }
    if (trimmed.includes("\n")) {
      return trimmed
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean)
        .slice(0, maxItems);
    }
    return [truncate(trimmed, MAX_TEXT)];
  }

  return [truncate(String(value), MAX_TEXT)];
}

export function truncate(value: string, maxLen = MAX_TEXT): string {
  if (!value) return "";
  return value.length > maxLen ? `${value.slice(0, maxLen)}…` : value;
}

export function limitAnalysis(value: unknown, maxLines = MAX_ANALYSIS_LINES): string {
  const text = value == null ? "" : String(value).trim();
  if (!text) return "";

  const lines = text
    .split(/\n+/)
    .map((l) => l.trim())
    .filter(Boolean)
    .slice(0, maxLines)
    .map((l) => truncate(l, MAX_TEXT));

  return lines.join("\n");
}

export function safeString(value: unknown, fallback = ""): string {
  if (value == null) return fallback;
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(String).join("; ");
  return String(value);
}

export function safeCommands(value: unknown, max = MAX_COMMANDS): string[] {
  return toTextLines(value, max, 500);
}

export function dedupeFindings(findings: Finding[] | null | undefined): Finding[] {
  if (!findings?.length) return [];

  const seen = new Set<string>();
  const unique: Finding[] = [];

  for (const finding of findings) {
    const key = [
      finding.namespace,
      finding.resource_type,
      finding.affected_resource,
      finding.title,
    ].join("|");
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(finding);
  }

  return unique;
}

/** Sanitize API diagnosis for safe UI rendering. */
export function sanitizeDiagnosis(diagnosis: Diagnosis | null | undefined): Diagnosis | null {
  if (!diagnosis) return null;

  const findings = dedupeFindings(diagnosis.findings).map((finding) => ({
    ...finding,
    root_cause: truncate(safeString(finding.root_cause)),
    explanation: limitAnalysis(finding.explanation),
    evidence: toTextLines(finding.evidence as unknown),
    investigation_commands: safeCommands(finding.investigation_commands),
    confidence_reasoning: finding.confidence_reasoning ?? "",
    remediation: {
      immediate_fix: truncate(safeString(finding.remediation?.immediate_fix)),
      verification_steps: safeCommands(finding.remediation?.verification_steps, MAX_VERIFICATION),
      rollback_steps: [],
    },
  }));

  return {
    ...diagnosis,
    root_cause: truncate(safeString(diagnosis.root_cause)),
    explanation: limitAnalysis(diagnosis.explanation),
    fix: truncate(safeString(diagnosis.fix)),
    executive_summary: truncate(safeString(diagnosis.executive_summary), 400),
    findings,
  };
}
