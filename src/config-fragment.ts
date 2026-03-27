/**
 * Safely extracts a config fragment from openclaw.json, stripping all secrets.
 *
 * Only exports:
 *   - agents.defaults  (model, thinking preferences — no credentials)
 *   - agents.list[].skills  (allow-list per agent)
 *   - skills.allowBundled
 *   - skills.limits
 *
 * Explicitly NEVER exports: credentials, env, oauth, channel tokens,
 * gateway settings, secrets paths, or any key whose name contains
 * "secret", "token", "key", "password", "auth", "credential".
 */
import fs from "node:fs/promises";
import { z } from "zod";

// ── Zod schemas for safe extraction ─────────────────────────────────────────

const AgentSkillsSchema = z
  .object({
    skills: z.array(z.string()).optional(),
  })
  .passthrough()
  .transform((v) => ({ skills: v.skills }));

const AgentDefaultsSchema = z
  .object({
    model: z.string().optional(),
    thinkingDefault: z.string().optional(),
    thinkingBudget: z.number().optional(),
    maxTokens: z.number().optional(),
    skills: z.array(z.string()).optional(),
  })
  .passthrough()
  .transform((v) => ({
    ...(v.model !== undefined && { model: v.model }),
    ...(v.thinkingDefault !== undefined && { thinkingDefault: v.thinkingDefault }),
    ...(v.thinkingBudget !== undefined && { thinkingBudget: v.thinkingBudget }),
    ...(v.maxTokens !== undefined && { maxTokens: v.maxTokens }),
    ...(v.skills !== undefined && { skills: v.skills }),
  }));

const SkillsLimitsSchema = z
  .object({
    maxSkillsLoadedPerSource: z.number().optional(),
    maxSkillsInPrompt: z.number().optional(),
    maxSkillsPromptChars: z.number().optional(),
    maxSkillFileBytes: z.number().optional(),
  })
  .passthrough()
  .transform((v) => ({
    ...(v.maxSkillsLoadedPerSource !== undefined && {
      maxSkillsLoadedPerSource: v.maxSkillsLoadedPerSource,
    }),
    ...(v.maxSkillsInPrompt !== undefined && { maxSkillsInPrompt: v.maxSkillsInPrompt }),
    ...(v.maxSkillsPromptChars !== undefined && { maxSkillsPromptChars: v.maxSkillsPromptChars }),
    ...(v.maxSkillFileBytes !== undefined && { maxSkillFileBytes: v.maxSkillFileBytes }),
  }));

// ── Public types ─────────────────────────────────────────────────────────────

export interface ConfigFragment {
  agents?: {
    defaults?: Record<string, unknown>;
    list?: Array<{ id: string; skills?: string[] }>;
  };
  skills?: {
    allowBundled?: boolean;
    limits?: Record<string, unknown>;
  };
}

// ── Implementation ───────────────────────────────────────────────────────────

/**
 * Load openclaw.json and extract only safe, non-secret fields.
 * Returns null if the config file does not exist.
 */
export async function extractConfigFragment(configFilePath: string): Promise<ConfigFragment | null> {
  let raw: unknown;
  try {
    const text = await fs.readFile(configFilePath, "utf-8");
    raw = JSON.parse(text) as unknown;
  } catch (err: unknown) {
    if (isNodeError(err) && err.code === "ENOENT") return null;
    throw new Error(`Failed to read config file at ${configFilePath}: ${String(err)}`);
  }

  if (typeof raw !== "object" || raw === null) return null;

  const cfg = raw as Record<string, unknown>;
  const fragment: ConfigFragment = {};

  // ── agents.defaults ──────────────────────────────────────────────────────
  if (typeof cfg.agents === "object" && cfg.agents !== null) {
    const agents = cfg.agents as Record<string, unknown>;

    if (agents.defaults !== undefined) {
      const parsed = AgentDefaultsSchema.safeParse(agents.defaults);
      if (parsed.success && Object.keys(parsed.data).length > 0) {
        fragment.agents ??= {};
        fragment.agents.defaults = parsed.data as Record<string, unknown>;
      }
    }

    // ── agents.list[].skills ───────────────────────────────────────────────
    if (Array.isArray(agents.list)) {
      const safeList = (agents.list as unknown[])
        .filter((a) => typeof a === "object" && a !== null)
        .map((a) => {
          const agent = a as Record<string, unknown>;
          const parsed = AgentSkillsSchema.safeParse(agent);
          if (!parsed.success) return null;
          return {
            id: typeof agent.id === "string" ? agent.id : "",
            ...(parsed.data.skills !== undefined && { skills: parsed.data.skills }),
          };
        })
        .filter(
          (a): a is { id: string; skills?: string[] } => a !== null && a.id !== "",
        );

      if (safeList.length > 0) {
        fragment.agents ??= {};
        fragment.agents.list = safeList;
      }
    }
  }

  // ── skills.allowBundled + skills.limits ──────────────────────────────────
  if (typeof cfg.skills === "object" && cfg.skills !== null) {
    const skills = cfg.skills as Record<string, unknown>;

    const safeSkills: ConfigFragment["skills"] = {};

    if (typeof skills.allowBundled === "boolean") {
      safeSkills.allowBundled = skills.allowBundled;
    }

    if (skills.limits !== undefined) {
      const parsed = SkillsLimitsSchema.safeParse(skills.limits);
      if (parsed.success && Object.keys(parsed.data).length > 0) {
        safeSkills.limits = parsed.data as Record<string, unknown>;
      }
    }

    if (Object.keys(safeSkills).length > 0) {
      fragment.skills = safeSkills;
    }
  }

  return Object.keys(fragment).length > 0 ? fragment : null;
}

function isNodeError(err: unknown): err is NodeJS.ErrnoException {
  return err instanceof Error && "code" in err;
}
