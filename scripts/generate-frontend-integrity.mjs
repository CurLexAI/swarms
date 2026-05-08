import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const assets = [
  { id: 'vue', file: 'public/control/vendor/vue.global.prod-3.5.13.js' },
  { id: 'marked', file: 'public/control/vendor/marked.min-12.0.2.js' },
  { id: 'dompurify', file: 'public/control/vendor/purify.min-3.1.6.js' },
  { id: 'lucide', file: 'public/control/vendor/lucide.min-0.468.0.js' }
];

const manifest = {};
for (const asset of assets) {
  const fullPath = path.join(root, asset.file);
  const content = readFileSync(fullPath);
  const integrity = `sha384-${createHash('sha384').update(content).digest('base64')}`;
  manifest[asset.id] = { path: `/${asset.file.replace(/^public\//, '')}`, integrity };
}

const outPath = path.join(root, 'public/control/vendor/integrity.json');
writeFileSync(outPath, `${JSON.stringify(manifest, null, 2)}\n`);
console.log(`Wrote integrity manifest: ${outPath}`);
