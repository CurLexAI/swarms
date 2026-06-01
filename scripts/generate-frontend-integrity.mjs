import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const localAssets = [
  { id: 'vue', file: 'public/control/vendor/vue.global.prod-3.5.13.js' },
  { id: 'marked', file: 'public/control/vendor/marked.min-12.0.2.js' },
  { id: 'dompurify', file: 'public/control/vendor/purify.min-3.1.6.js' },
  { id: 'lucide', file: 'public/control/vendor/lucide.min-0.468.0.js' }
];

const cdnAssets = [
  {
    id: 'trustFallbackLib',
    src: 'https://cdn.example.com/trust/fallback-lib.js',
    localFile: 'public/trust/vendor/fallback-lib.js'
  }
];

const sha384 = (content) => `sha384-${createHash('sha384').update(content).digest('base64')}`;

const localManifest = {};
for (const asset of localAssets) {
  const fullPath = path.join(root, asset.file);
  if (!existsSync(fullPath)) {
    console.warn(`Skipping missing local asset: ${asset.file}`);
    continue;
  }
  const content = readFileSync(fullPath);
  localManifest[asset.id] = { path: `/${asset.file.replace(/^public\//, '')}`, integrity: sha384(content) };
}

const cdnManifest = {};
for (const asset of cdnAssets) {
  const fullPath = path.join(root, asset.localFile);
  if (!existsSync(fullPath)) {
    throw new Error(`Missing local CDN mirror for SRI generation: ${asset.localFile}`);
  }
  const content = readFileSync(fullPath);
  cdnManifest[asset.id] = { src: asset.src, integrity: sha384(content), crossorigin: 'anonymous' };
}

const localOutPath = path.join(root, 'public/control/vendor/integrity.json');
mkdirSync(path.dirname(localOutPath), { recursive: true });
writeFileSync(localOutPath, `${JSON.stringify(localManifest, null, 2)}\n`);

const cdnOutPath = path.join(root, 'public/trust/cdn-integrity.json');
mkdirSync(path.dirname(cdnOutPath), { recursive: true });
writeFileSync(cdnOutPath, `${JSON.stringify(cdnManifest, null, 2)}\n`);
console.log(`Wrote integrity manifests: ${localOutPath} and ${cdnOutPath}`);
