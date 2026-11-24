// Fails when a package of package-lock.json is not under a free / open source
// licence. Run with `npm run licenses` (also run by the CI).
import { readFileSync } from 'node:fs';

// Permissive licences, allowed everywhere (shipped to the browser or not).
const PERMISSIVE = new Set([
  '0BSD',
  'Apache-2.0',
  'BlueOak-1.0.0',
  'BSD-2-Clause',
  'BSD-3-Clause',
  'CC0-1.0',
  'ISC',
  'MIT',
  'Python-2.0',
  'Unlicense',
]);

// Free licences accepted for build / test tools only (not shipped to the browser):
// MPL-2.0 (lightningcss, weak file-level copyleft), CC-BY-4.0 (caniuse-lite data).
const DEV_ONLY = new Set(['MPL-2.0', 'CC-BY-4.0']);

/** Minimal SPDX expression check: "A OR B" needs one allowed, otherwise all. */
function isAllowed(expression, allowed) {
  const cleaned = expression.replace(/[()]/g, ' ').trim();
  if (/\sOR\s/.test(cleaned) && !/\sAND\s/.test(cleaned)) {
    return cleaned.split(/\s+OR\s+/).some((id) => allowed.has(id));
  }
  return cleaned.split(/\s+(?:AND|OR)\s+/).every((id) => allowed.has(id));
}

const lock = JSON.parse(readFileSync(new URL('../package-lock.json', import.meta.url), 'utf8'));
const problems = [];

for (const [path, info] of Object.entries(lock.packages ?? {})) {
  if (!path) continue; // the project itself
  const name = path.slice(path.lastIndexOf('node_modules/') + 'node_modules/'.length);
  const license = typeof info.license === 'string' ? info.license : null;
  const allowed = info.dev ? new Set([...PERMISSIVE, ...DEV_ONLY]) : PERMISSIVE;
  if (!license || !isAllowed(license, allowed)) {
    problems.push(`${name}@${info.version} (${info.dev ? 'dev' : 'runtime'}): ${license ?? 'no licence declared'}`);
  }
}

if (problems.length) {
  console.error('Packages without an accepted free licence:\n  ' + problems.join('\n  '));
  process.exit(1);
}
console.log(`Licences OK (${Object.keys(lock.packages).length - 1} packages).`);
