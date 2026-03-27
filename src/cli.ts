/**
 * Commander CLI program setup and command registration.
 */
import { Command } from "commander";
import { runExport, type ExportOptions } from "./export.js";
import { runImport, type MergeMode } from "./import.js";

export function createProgram(): Command {
  const program = new Command();
  program
    .name("max-ctx")
    .description("Export and import OpenClaw skills, workspace context files, and config fragments")
    .version("0.1.0");
  return program;
}

export function registerCommands(program: Command): void {
  registerExportCommand(program);
  registerImportCommand(program);
}

// ── export ───────────────────────────────────────────────────────────────────

function registerExportCommand(program: Command): void {
  program
    .command("export")
    .description("Package skills + workspace files + config fragment into a .tar.gz bundle")
    .option("-o, --output <file.tar.gz>", "Output file path (default: <timestamp>-openclaw-context.tar.gz)")
    .option("--skills <slugs>", "Comma-separated skill slugs to include (default: all managed skills)")
    .option("--all-skills", "Include all managed skills (same as default)")
    .option("--no-workspace", "Exclude workspace files")
    .option("--no-config-fragment", "Exclude config fragment")
    .option("--agent <id>", "Agent ID (for future use)")
    .option("--dry-run", "List what would be exported without creating the archive")
    .option("--json", "Output result as JSON")
    .action(async (cmdOpts: Record<string, unknown>) => {
      const opts: ExportOptions = {
        output: cmdOpts.output as string | undefined,
        skills: typeof cmdOpts.skills === "string"
          ? cmdOpts.skills.split(",").map((s) => s.trim()).filter(Boolean)
          : undefined,
        allSkills: cmdOpts.allSkills === true,
        noWorkspace: cmdOpts.workspace === false,
        noConfigFragment: cmdOpts.configFragment === false,
        agentId: cmdOpts.agent as string | undefined,
        dryRun: cmdOpts.dryRun === true,
        json: cmdOpts.json === true,
      };

      try {
        const result = await runExport(opts);
        if (opts.json) {
          console.log(JSON.stringify(result, null, 2));
        } else if (!opts.dryRun) {
          console.log(`✓ Exported to: ${result.outputFile}`);
          console.log(`  Skills: ${result.skills.length}`);
          console.log(`  Workspace files: ${result.workspaceFiles.length}`);
          console.log(`  Config fragment: ${result.hasConfigFragment ? "yes" : "no"}`);
        }
      } catch (err) {
        console.error("Export failed:", err instanceof Error ? err.message : String(err));
        process.exit(1);
      }
    });
}

// ── import ───────────────────────────────────────────────────────────────────

function registerImportCommand(program: Command): void {
  program
    .command("import <archive>")
    .description("Import skills + workspace files from a .tar.gz bundle")
    .option("--merge", "Skip existing files/skills (default)")
    .option("--overwrite", "Overwrite existing files/skills")
    .option("--no-skills", "Skip importing skills")
    .option("--no-workspace", "Skip importing workspace files")
    .option("--no-config-fragment", "Skip showing config fragment hint")
    .option("--agent <id>", "Agent ID (for future use)")
    .option("--dry-run", "Show what would be imported without making changes")
    .option("--json", "Output result as JSON")
    .action(async (archive: string, cmdOpts: Record<string, unknown>) => {
      let mergeMode: MergeMode = "merge";
      if (cmdOpts.overwrite === true) mergeMode = "overwrite";
      else if (cmdOpts.merge === true) mergeMode = "merge";

      try {
        await runImport(archive, {
          mergeMode,
          noSkills: cmdOpts.skills === false,
          noWorkspace: cmdOpts.workspace === false,
          noConfigFragment: cmdOpts.configFragment === false,
          agentId: cmdOpts.agent as string | undefined,
          dryRun: cmdOpts.dryRun === true,
          json: cmdOpts.json === true,
        });
      } catch (err) {
        console.error("Import failed:", err instanceof Error ? err.message : String(err));
        process.exit(1);
      }
    });
}
