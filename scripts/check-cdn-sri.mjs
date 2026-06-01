import { readFileSync } from 'node:fs';
import path from 'node:path';

const files = ['public/trust/index.html'];
let failures = 0;

for (const rel of files) {
  const fullPath = path.join(process.cwd(), rel);
  const html = readFileSync(fullPath, 'utf8');
  const matches = html.matchAll(/<script\b[^>]*\bsrc="https:\/\/[^"\s]+"[^>]*>/g);
  for (const m of matches) {
    const tag = m[0];
    const hasIntegrity = /\bintegrity="sha384-[^"]+"/.test(tag);
    const hasCrossorigin = /\bcrossorigin="anonymous"/.test(tag);
    if (!hasIntegrity || !hasCrossorigin) {
      failures += 1;
      console.error(`${rel}: missing required SRI attributes in tag: ${tag}`);
    }
  }
}

if (failures > 0) {
  process.exit(1);
}

console.log('All HTTPS script tags include integrity and crossorigin="anonymous".');
