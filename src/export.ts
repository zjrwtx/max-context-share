/**
 * Export command: packages skills + workspace files + config fragment
 * into a timestamped .tar.gz bundle.
 */
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import * as tar from "tar";
import { resolvePaths, WORKSPACE_FILES, type SkillSource, type SkillSourceDir } from "./paths.js";
import { createManifest, skillArchivePath, type SkillEntry } from "./manifest.js";
import { extractConfigFragment } from "./config-fragment.js";

export interface ExportOptions {
  output?: string;
  /** Specific slugs to include (searched across all sources). */
  skills?: string[];
  allSkills?: boolean;
  /** Limit export to specific source types. Default: all user-owned sources. */
  sources?: SkillSource[];
  noWorkspace?: boolean;
  noConfigFragment?: boolean;
  agentId?: string;
  dryRun?: boolean;
  json?: boolean;
}

export interface ExportResult {
  outputFile: string;
  skills: SkillEntry[];
  workspaceFiles: string[];
  hasConfigFragment: boolean;
  dryRun: boolean;
}

export async function runExport(opts: ExportOptions): Promise<ExportResult> {
  const paths = resolvePaths(process.env);

  // ── 1. Collect skills from all sources ───────────────────────────────────
  // Scan each source dir; higher-precedence sources override same-slug entries.
  // Precedence order in skillSources: managed < personal-agents < project-agents < workspace
  const slugToEntry = new Map<string, { entry: SkillEntry; dir: string }>();

  for (const src of paths.skillSources) {
    if (opts.sources && !opts.sources.includes(src.source)) continue;
    const slugs = await listSkillSlugs(src.dir);
    for (const slug of slugs) {
      slugToEntry.set(slug, {
        entry: { slug, source: src.source },
        dir: src.dir,
      });
    }
  }

  // Filter to requested slugs if specified
  let selectedEntries: Array<{ entry: SkillEntry; dir: string }>;
  if (opts.skills && opts.skills.length > 0) {
    const unknown = opts.skills.filter((s) => !slugToEntry.has(s));
    if (unknown.length > 0) {
      throw new Error(`Unknown skills: ${unknown.join(", ")}`);
    }
    selectedEntries = opts.skills.map((s) => slugToEntry.get(s)!);
  } else {
    selectedEntries = Array.from(slugToEntry.values());
  }

  // ── 2. Collect workspace files ───────────────────────────────────────────
  const selectedWorkspaceFiles: string[] = [];
  if (!opts.noWorkspace) {
    for (const fname of WORKSPACE_FILES) {
      const fpath = path.join(paths.workspaceDir, fname);
      if (await fileExists(fpath)) {
        selectedWorkspaceFiles.push(fname);
      }
    }
  }

  // ── 3. Config fragment ───────────────────────────────────────────────────
  let configFragment: object | null = null;
  if (!opts.noConfigFragment) {
    configFragment = await extractConfigFragment(paths.configFile);
  }

  const result: ExportResult = {
    outputFile: "",
    skills: selectedEntries.map((e) => e.entry),
    workspaceFiles: selectedWorkspaceFiles,
    hasConfigFragment: configFragment !== null,
    dryRun: opts.dryRun ?? false,
  };

  if (opts.dryRun) {
    if (!opts.json) printDryRunSummary(result, paths.skillSources);
    return result;
  }

  // ── 4. Determine output path ─────────────────────────────────────────────
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-").replace("T", "_").slice(0, 19);
  const defaultOutput = path.join(process.cwd(), `${timestamp}-openclaw-context.tar.gz`);
  const outputFile = opts.output ? path.resolve(opts.output) : defaultOutput;
  result.outputFile = outputFile;

  // ── 5. Build the tar archive in a temp dir ───────────────────────────────
  const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "max-ctx-export-"));
  try {
    const rootName = `${timestamp}-openclaw-context`;
    const stageDir = path.join(tmpDir, rootName);
    await fs.mkdir(stageDir, { recursive: true });

    // Write manifest
    const manifest = createManifest({
      skills: result.skills,
      workspaceFiles: selectedWorkspaceFiles,
      hasConfigFragment: configFragment !== null,
    });
    await fs.writeFile(
      path.join(stageDir, "manifest.json"),
      JSON.stringify(manifest, null, 2),
      "utf-8",
    );

    // Copy skills — archived as skills/<source>/<slug>/
    for (const { entry, dir } of selectedEntries) {
      const srcDir = path.join(dir, entry.slug);
      const dstDir = path.join(stageDir, skillArchivePath(entry));
      await copyDir(srcDir, dstDir);
    }

    // Copy workspace files
    if (selectedWorkspaceFiles.length > 0) {
      const wsStageDir = path.join(stageDir, "workspace");
      await fs.mkdir(wsStageDir, { recursive: true });
      for (const fname of selectedWorkspaceFiles) {
        await fs.copyFile(
          path.join(paths.workspaceDir, fname),
          path.join(wsStageDir, fname),
        );
      }
    }

    // Write config fragment
    if (configFragment !== null) {
      await fs.writeFile(
        path.join(stageDir, "config-fragment.json"),
        JSON.stringify(configFragment, null, 2),
        "utf-8",
      );
    }

    // Create tar.gz
    await tar.create(
      {
        gzip: true,
        file: outputFile,
        cwd: tmpDir,
      },
      [rootName],
    );
  } finally {
    await fs.rm(tmpDir, { recursive: true, force: true });
  }

  return result;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

async function listSkillSlugs(dir: string): Promise<string[]> {
  try {
    const entries = await fs.readdir(dir, { withFileTypes: true });
    return entries
      .filter((e) => e.isDirectory())
      .map((e) => e.name)
      .sort();
  } catch (err: unknown) {
    if (isNodeError(err) && err.code === "ENOENT") return [];
    throw err;
  }
}

async function fileExists(fpath: string): Promise<boolean> {
  try {
    await fs.access(fpath);
    return true;
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

function printDryRunSummary(result: ExportResult, skillSources: SkillSourceDir[]): void {
  console.log("[dry-run] Would export:");

  if (result.skills.length > 0) {
    // Group by source for readability
    const bySource = new Map<SkillSource, string[]>();
    for (const e of result.skills) {
      const list = bySource.get(e.source) ?? [];
      list.push(e.slug);
      bySource.set(e.source, list);
    }
    console.log("  Skills:");
    for (const [source, slugs] of bySource) {
      const srcDef = skillSources.find((s) => s.source === source);
      console.log(`    [${source}]  ${srcDef?.dir ?? ""}`);
      for (const slug of slugs) {
        console.log(`      - ${slug}`);
      }
    }
  } else {
    console.log("  Skills: (none)");
  }

  if (result.workspaceFiles.length > 0) {
    console.log(`  Workspace files:`);
    for (const f of result.workspaceFiles) {
      console.log(`    - ${f}`);
    }
  } else {
    console.log("  Workspace files: (none)");
  }

  console.log(`  Config fragment: ${result.hasConfigFragment ? "yes" : "no"}`);
}

function isNodeError(err: unknown): err is NodeJS.ErrnoException {
  return err instanceof Error && "code" in err;
}
