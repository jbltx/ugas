import { manifest } from './generated/data.js';

/** One file shipped in this package, as listed by the release manifest (index.json). */
export interface Resource {
  id: string;
  /** e.g. `schema`, `schema-bundle`, `spec-section`, `genre-entity`, `example`, `conformance`. */
  kind: string;
  title: string;
  /** Path inside this package, e.g. `schemas/bundle.json`. */
  path: string;
  /** Canonical URL of the same file on ugas.jbltx.com. */
  url: string;
  mediaType: string;
  bytes: number;
  sha256: string;
}

export interface FilesFilter {
  /** Keep only these manifest kinds. */
  kind?: string | readonly string[];
}

interface ManifestResource extends Omit<Resource, 'path'> {
  path: string;
}

const prefix = `v${manifest.version}/`;

/**
 * Every file in the package, from the manifest, with package-relative paths. The same
 * list (ids, kinds, sha256) the site publishes at ugas.jbltx.com/v<version>/index.json.
 */
export function files(filter: FilesFilter = {}): Resource[] {
  const kinds = filter.kind === undefined ? null : new Set([filter.kind].flat());
  return (manifest.resources as ManifestResource[])
    .filter((r) => kinds === null || kinds.has(r.kind))
    .map((r) => ({ ...r, path: r.path.startsWith(prefix) ? r.path.slice(prefix.length) : r.path }));
}

/**
 * URL of a packaged file, for reading it from disk in Node:
 * `readFileSync(fileUrl('schemas/bundle.json'))`. In a bundler, import the file through
 * its subpath export instead (`ugas/schemas/bundle.json`).
 */
export function fileUrl(path: string): URL {
  return new URL(`../${path.replace(/^\/+/, '')}`, import.meta.url);
}
