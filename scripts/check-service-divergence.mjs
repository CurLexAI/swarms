import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';

const pairs = [
  ['src/services/AuditService.ts', 'src/services/AuditService.js'],
  ['src/services/unifiedAgentAdapter.ts', 'src/services/unifiedAgentAdapter.js']
];

let failed = false;
for (const [tsPath, jsPath] of pairs) {
  const absTs = path.resolve(tsPath);
  const absJs = path.resolve(jsPath);

  if (!fs.existsSync(absTs) || !fs.existsSync(absJs)) {
    continue;
  }

  const tsSource = fs.readFileSync(absTs, 'utf8');
  const jsSource = fs.readFileSync(absJs, 'utf8').trim();
  const transpiled = ts.transpileModule(tsSource, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022
    },
    fileName: absTs
  }).outputText.trim();

  if (transpiled !== jsSource) {
    failed = true;
    console.error(`DIVERGENCE_DETECTED: ${tsPath} and ${jsPath} differ.`);
    console.error('Run `npm run build` and update generated outputs from TypeScript source only.');
  }
}

if (failed) process.exit(1);
console.log('Service divergence check passed.');
