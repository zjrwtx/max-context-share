/**
 * Resolves OpenClaw file-system paths without depending on the openclaw core package.
 * Reads conventions directly from the file system (~/.openclaw/).
 */
import { execSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export const WORKSPACE_FILES = [
  "AGENTS.md",
  "SOUL.md",
  "TOOLS.md",
  "IDENTITY.md",
  "USER.md",
  "HEARTBEAT.md",
  "BOOTSTRAP.md",
  "MEMORY.md",
] as const;

export type WorkspaceFileName = (typeof WORKSPACE_FILES)[number];

/**
 * All known skill source directories, in precedence order (lowest → highest).
 * Mirrors the merge order in src/agents/skills/workspace.ts:
 *
 *   bundled < managed < personal-agents < project-agents < workspace
 *
 * "plugin" skill dirs are dynamic (resolved from installed plugin manifests at
 * runtime) and cannot be enumerated without the core runtime; excluded here.
 */
export type SkillSource =
  | "bundled"           // <openclaw-pkg>/skills/             shipped with openclaw
  | "managed"           // ~/.openclaw/skills/                installed via `openclaw skills install`
  | "personal-agents"   // ~/.agents/skills/                  personal cross-workspace skills
  | "project-agents"    // <workspace>/.agents/skills/        project-local skills
  | "workspace";        // <workspace>/skills/                workspace-local skills

export interface SkillSourceDir {
  source: SkillSource;
  dir: string;
}

export interface OpenClawPaths {
  /** ~/.openclaw  (or $OPENCLAW_STATE_DIR) */
  stateDir: string;
  /** ~/.openclaw/workspace  (or workspace-<profile>) */
  workspaceDir: string;
  /** ~/.openclaw/openclaw.json */
  configFile: string;
  /**
   * All skill source directories, in ascending precedence order.
   * Higher-precedence sources override lower-precedence ones (same slug wins).
   * Only includes dirs that actually exist on disk.
   */
  skillSources: SkillSourceDir[];
}

/**
 * Try to locate the openclaw package's bundled skills/ directory.
 *
 * Strategy (in order):
 *   1. $OPENCLAW_BUNDLED_SKILLS_DIR env override
 *   2. Walk up from the `openclaw` binary's realpath to find <pkg-root>/skills/
 *   3. `npm root -g` → <npm-global>/openclaw/skills/
 */
function resolveBundledSkillsDir(): string | undefined {
  // 1. env override (same as core)
  const override = process.env.OPENCLAW_BUNDLED_SKILLS_DIR?.trim();
  if (override && fs.existsSync(override)) return override;

  // 2. walk up from openclaw binary realpath
  try {
    const bin = execSync("which openclaw 2>/dev/null", { stdio: ["pipe", "pipe", "ignore"] })
      .toString()
      .trim();
    if (bin) {
      const real = fs.realpathSync(bin);
      let cur = path.dirname(real);
      for (let i = 0; i < 5; i++) {
        const candidate = path.join(cur, "skills");
        if (fs.existsSync(candidate) && fs.existsSync(path.join(cur, "package.json"))) {
          return candidate;
        }
        const next = path.dirname(cur);
        if (next === cur) break;
        cur = next;
      }
    }
  } catch {
    // ignore
  }

  // 3. npm root -g
  try {
    const npmGlobal = execSync("npm root -g 2>/dev/null", {
      stdio: ["pipe", "pipe", "ignore"],
    })
      .toString()
      .trim();
    if (npmGlobal) {
      const candidate = path.join(npmGlobal, "openclaw", "skills");
      if (fs.existsSync(candidate)) return candidate;
    }
  } catch {
    // ignore
  }

  return undefined;
}

/**
 * Resolve all relevant OpenClaw paths from the environment.
 * Mirrors the logic in src/agents/workspace.ts and src/utils.ts.
 */
export function resolvePaths(env: NodeJS.ProcessEnv = process.env): OpenClawPaths {
  const home = env.HOME ?? env.USERPROFILE ?? os.homedir();

  // $OPENCLAW_STATE_DIR overrides the default ~/.openclaw directory
  const stateDir = env.OPENCLAW_STATE_DIR
    ? path.resolve(env.OPENCLAW_STATE_DIR)
    : path.join(home, ".openclaw");

  // Profile-aware workspace directory (mirrors resolveDefaultAgentWorkspaceDir)
  const profile = env.OPENCLAW_PROFILE?.trim();
  const workspaceDirName =
    profile && profile.toLowerCase() !== "default"
      ? `workspace-${profile}`
      : "workspace";
  const workspaceDir = path.join(stateDir, workspaceDirName);

  const allSources: Array<{ source: SkillSource; dir: string }> = [
    { source: "managed",         dir: path.join(stateDir, "skills") },
    { source: "personal-agents", dir: path.join(home, ".agents", "skills") },
    { source: "project-agents",  dir: path.join(workspaceDir, ".agents", "skills") },
    { source: "workspace",       dir: path.join(workspaceDir, "skills") },
  ];

  // bundled: only add if we can find it, inserted at lowest precedence
  const bundledDir = resolveBundledSkillsDir();
  if (bundledDir) {
    allSources.unshift({ source: "bundled", dir: bundledDir });
  }

  // only keep dirs that exist
  const skillSources = allSources.filter(({ dir }) => {
    try { return fs.statSync(dir).isDirectory(); } catch { return false; }
  });

  return {
    stateDir,
    workspaceDir,
    configFile: path.join(stateDir, "openclaw.json"),
    skillSources,
  };
}
