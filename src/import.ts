/**
 * Import command: unpacks a .tar.gz context bundle into the local OpenClaw installation.
 *
 * Merge strategy:
 *   --merge (default): skip files/skills that already exist, warn user
 *   --overwrite: replace existing files/skills
 *
 * Config fragment: NEVER written automatically; always printed as diff hint.
 */
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import * as tar from "tar";
import { resolvePaths } from "./paths.js";
import { parseManifest, skillArchivePath, type Manifest, type SkillEntry } from "./manifest.js";
import type { ConfigFragment } from "./config-fragment.js";

export type MergeMode = "merge" | "overwrite";

export interface ImportOptions {
  mergeMode?: MergeMode;
  noSkills?: boolean;
  noWorkspace?: boolean;
  noConfigFragment?: boolean;
  agentId?: string;
  dryRun?: boolean;
  json?: boolean;
}

export interface ImportResult {
  manifest: Manifest;
  skillsImported: SkillEntry[];
  skillsSkipped: SkillEntry[];
  workspaceFilesImported: string[];
  workspaceFilesSkipped: string[];
  configFragmentHint: ConfigFragment | null;
  dryRun: boolean;
}

export async function runImport(
  archivePath: string,
  opts: ImportOptions = {},
): Promise<ImportResult> {
  const mergeMode: MergeMode = opts.mergeMode ?? "merge";
  const paths = resolvePaths(process.env);

  // ── 1. Extract archive into a temp dir ───────────────────────────────────
  const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "max-ctx-import-"));
  try {
    await tar.extract({
      file: path.resolve(archivePath),
      cwd: tmpDir,
    });

    // Find the root directory inside the archive
    const entries = await fs.readdir(tmpDir, { withFileTypes: true });
    const rootEntry = entries.find((e) => e.isDirectory());
    if (!rootEntry) {
      throw new Error("Archive appears to be empty or has an unexpected structure.");
    }
    const extractedRoot = path.join(tmpDir, rootEntry.name);

    // ── 2. Read manifest ─────────────────────────────────────────────────
    const manifestPath = path.join(extractedRoot, "manifest.json");
    const manifestRaw = JSON.parse(await fs.readFile(manifestPath, "utf-8")) as unknown;
    const manifest = parseManifest(manifestRaw);

    // ── 3. Read config fragment (for display only) ───────────────────────
    let configFragmentHint: ConfigFragment | null = null;
    if (!opts.noConfigFragment && manifest.hasConfigFragment) {
      const cfPath = path.join(extractedRoot, "config-fragment.json");
      try {
        configFragmentHint = JSON.parse(await fs.readFile(cfPath, "utf-8")) as ConfigFragment;
      } catch {
        // ignore if missing
      }
    }

    // ── 4. Import skills ─────────────────────────────────────────────────
    const skillsImported: SkillEntry[] = [];
    const skillsSkipped: SkillEntry[] = [];

    if (!opts.noSkills && manifest.skills.length > 0) {
      // Resolve destination dir for each skill based on its source type.
      // Skills are always imported into the matching local source dir.
      const sourceToDir = new Map(paths.skillSources.map((s) => [s.source, s.dir]));

      for (const skillEntry of manifest.skills) {
        const dstRootDir = sourceToDir.get(skillEntry.source);
        if (!dstRootDir) {
          console.warn(`[warn] Unknown skill source "${skillEntry.source}" for skill "${skillEntry.slug}", skipping.`);
          skillsSkipped.push(skillEntry);
          continue;
        }

        const srcDir = path.join(extractedRoot, skillArchivePath(skillEntry));
        const dstDir = path.join(dstRootDir, skillEntry.slug);
        const exists = await dirExists(dstDir);

        if (exists && mergeMode === "merge") {
          skillsSkipped.push(skillEntry);
          if (!opts.dryRun) {
            console.warn(
              `[skip] Skill "${skillEntry.slug}" (${skillEntry.source}) already exists (use --overwrite to replace).`,
            );
          }
          continue;
        }

        if (!opts.dryRun) {
          await fs.mkdir(dstRootDir, { recursive: true });
          if (exists) {
            await fs.rm(dstDir, { recursive: true, force: true });
          }
          await copyDir(srcDir, dstDir);
        }
        skillsImported.push(skillEntry);
      }
    }

    // ── 5. Import workspace files ────────────────────────────────────────
    const workspaceFilesImported: string[] = [];
    const workspaceFilesSkipped: string[] = [];

    if (!opts.noWorkspace && manifest.workspaceFiles.length > 0) {
      await fs.mkdir(paths.workspaceDir, { recursive: true });
      const wsExtractDir = path.join(extractedRoot, "workspace");

      for (const fname of manifest.workspaceFiles) {
        const srcFile = path.join(wsExtractDir, fname);
        const dstFile = path.join(paths.workspaceDir, fname);
        const exists = await fileExists(dstFile);

        if (exists && mergeMode === "merge") {
          workspaceFilesSkipped.push(fname);
          if (!opts.dryRun) {
            console.warn(
              `[skip] Workspace file "${fname}" already exists (use --overwrite to replace).`,
            );
          }
          continue;
        }

        if (!opts.dryRun) {
          await fs.copyFile(srcFile, dstFile);
        }
        workspaceFilesImported.push(fname);
      }
    }

    const result: ImportResult = {
      manifest,
      skillsImported,
      skillsSkipped,
      workspaceFilesImported,
      workspaceFilesSkipped,
      configFragmentHint,
      dryRun: opts.dryRun ?? false,
    };

    if (opts.json) {
      console.log(JSON.stringify(result, null, 2));
    } else {
      printImportSummary(result, paths.workspaceDir);
    }

    return result;
  } finally {
    await fs.rm(tmpDir, { recursive: true, force: true });
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

async function fileExists(fpath: string): Promise<boolean> {
  try {
    await fs.access(fpath);
    return true;
  } catch {
    return false;
  }
}

async function dirExists(dpath: string): Promise<boolean> {
  try {
    const stat = await fs.stat(dpath);
    return stat.isDirectory();
  } catch {
    return false;
  }
}

async function copyDir(src: string, dst: string): Promise<void> {
  await fs.mkdir(dst, { recursive: true });
  const entries = await fs.readdir(src, { withFileTypes: true });
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const dstPath = path.join(dst, entry.name);
    if (entry.isDirectory()) {
      await copyDir(srcPath, dstPath);
    } else {
      await fs.copyFile(srcPath, dstPath);
    }
  }
}

function printImportSummary(result: ImportResult, workspaceDir: string): void {
  const prefix = result.dryRun ? "[dry-run] " : "";

  if (result.skillsImported.length > 0) {
    console.log(`${prefix}Skills imported:`);
    for (const e of result.skillsImported) {
      console.log(`  ✓ ${e.slug}  [${e.source}]`);
    }
  }
  if (result.skillsSkipped.length > 0) {
    console.log(`${prefix}Skills skipped (already exist):`);
    for (const e of result.skillsSkipped) {
      console.log(`  ~ ${e.slug}  [${e.source}]`);
    }
  }

  if (result.workspaceFilesImported.length > 0) {
    console.log(`${prefix}Workspace files imported to ${workspaceDir}:`);
    for (const f of result.workspaceFilesImported) {
      console.log(`  ✓ ${f}`);
    }
  }
  if (result.workspaceFilesSkipped.length > 0) {
    console.log(`${prefix}Workspace files skipped (already exist):`);
    for (const f of result.workspaceFilesSkipped) {
      console.log(`  ~ ${f}`);
    }
  }

  if (result.configFragmentHint !== null) {
    console.log(
      "\n⚠️  Config fragment detected — NOT written automatically.",
    );
    console.log(
      "   Review the settings below and apply manually via `openclaw config set ...`:\n",
    );
    console.log(JSON.stringify(result.configFragmentHint, null, 2));
  }

  if (
    result.skillsImported.length === 0 &&
    result.workspaceFilesImported.length === 0 &&
    result.configFragmentHint === null
  ) {
    console.log(`${prefix}Nothing to import.`);
  }
}
