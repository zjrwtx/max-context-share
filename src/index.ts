#!/usr/bin/env node
/**
 * CLI entry point for max-context-share.
 * Registers all commands and parses argv.
 */
import { createProgram, registerCommands } from "./cli.js";

const program = createProgram();
registerCommands(program);
program.parseAsync(process.argv).catch((err: unknown) => {
  console.error(err instanceof Error ? err.message : String(err));
  process.exit(1);
});
