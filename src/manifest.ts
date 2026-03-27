/**
 * Manifest schema and helpers for the .tar.gz context bundle.
 */
import { z } from "zod";
import type { SkillSource } from "./paths.js";

export const MANIFEST_SCHEMA_VERSION = 1;

export const SkillEntrySchema = z.object({
  slug: z.string(),
  source: z.enum(["bundled", "managed", "personal-agents", "project-agents", "workspace"]),
});

export type SkillEntry = z.infer<typeof SkillEntrySchema>;

export const ManifestSchema = z.object({
  schemaVersion: z.literal(1),
  createdAt: z.string().datetime(),
  /** Skills included, with their source directory type. */
  skills: z.array(SkillEntrySchema),
  workspaceFiles: z.array(z.string()),
  hasConfigFragment: z.boolean(),
});

export type Manifest = z.infer<typeof ManifestSchema>;

export function createManifest(opts: {
  skills: SkillEntry[];
  workspaceFiles: string[];
  hasConfigFragment: boolean;
}): Manifest {
  return {
    schemaVersion: MANIFEST_SCHEMA_VERSION,
    createdAt: new Date().toISOString(),
    skills: opts.skills,
    workspaceFiles: opts.workspaceFiles,
    hasConfigFragment: opts.hasConfigFragment,
  };
}

export function parseManifest(raw: unknown): Manifest {
  return ManifestSchema.parse(raw);
}

/** Unique archive path for a skill: `skills/<source>/<slug>/` */
export function skillArchivePath(entry: SkillEntry): string {
  return `skills/${entry.source}/${entry.slug}`;
}
