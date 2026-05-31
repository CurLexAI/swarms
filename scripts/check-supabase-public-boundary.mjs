import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';

const repoRoot = process.cwd();

const SKIP_DIRS = new Set([
  '.git',
  '.next',
  '.turbo',
  '.venv',
  '.venv-modal',
  'build',
  'coverage',
  'dist',
  'node_modules',
]);

const PUBLIC_CLIENT_DIR_NAMES = new Set([
  'app',
  'browser',
  'client',
  'components',
  'frontend',
  'pages',
  'public',
  'static',
  'ui',
  'web',
]);

const TEXT_EXTENSIONS = new Set([
  '.cjs',
  '.css',
  '.cts',
  '.html',
  '.js',
  '.json',
  '.jsx',
  '.mjs',
  '.mts',
  '.svelte',
  '.ts',
  '.tsx',
  '.vue',
]);

const CLIENT_FILE_PATTERNS = [
  /(^|[./_-])client[./_-]/i,
  /(^|[./_-])browser[./_-]/i,
  /\.client\.[cm]?[jt]sx?$/i,
  /\.browser\.[cm]?[jt]sx?$/i,
  /(^|\/)[^/]*client[^/]*\.[cm]?[jt]sx?$/i,
  /(^|\/)[^/]*browser[^/]*\.[cm]?[jt]sx?$/i,
];

const FORBIDDEN_PATTERNS = [
  /SUPABASE_SERVICE_ROLE_KEY/g,
  /service[_-]?role/gi,
  /SUPABASE_[A-Z0-9_]*SERVICE[A-Z0-9_]*KEY/g,
];

function isTextFile(filePath) {
  return TEXT_EXTENSIONS.has(path.extname(filePath));
}

function isPublicOrClientPath(relativePath) {
  const normalized = relativePath.split(path.sep).join('/');
  const segments = normalized.split('/');

  if (segments.some((segment) => PUBLIC_CLIENT_DIR_NAMES.has(segment.toLowerCase()))) {
    return true;
  }

  return CLIENT_FILE_PATTERNS.some((pattern) => pattern.test(normalized));
}

function walk(directory, files = []) {
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if (entry.isDirectory() && SKIP_DIRS.has(entry.name)) {
      continue;
    }

    const absolutePath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      walk(absolutePath, files);
      continue;
    }

    if (entry.isFile() && isTextFile(absolutePath)) {
      files.push(absolutePath);
    }
  }

  return files;
}

function findForbiddenMatches(filePath) {
  const content = readFileSync(filePath, 'utf8');
  const lines = content.split(/\r?\n/);
  const matches = [];

  lines.forEach((line, index) => {
    for (const pattern of FORBIDDEN_PATTERNS) {
      pattern.lastIndex = 0;
      if (pattern.test(line)) {
        matches.push({ line: index + 1, text: line.trim() });
      }
    }
  });

  return matches;
}

if (!existsSync(repoRoot) || !statSync(repoRoot).isDirectory()) {
  console.error(`Repository root is not readable: ${repoRoot}`);
  process.exit(1);
}

const filesToScan = walk(repoRoot).filter((absolutePath) => {
  const relativePath = path.relative(repoRoot, absolutePath);
  return isPublicOrClientPath(relativePath);
});

const findings = [];
for (const filePath of filesToScan) {
  const relativePath = path.relative(repoRoot, filePath);
  for (const match of findForbiddenMatches(filePath)) {
    findings.push(`${relativePath}:${match.line}: ${match.text}`);
  }
}

if (findings.length > 0) {
  console.error('Supabase public/client boundary violation: service-role material is forbidden in browser/public paths.');
  for (const finding of findings) {
    console.error(`- ${finding}`);
  }
  process.exit(1);
}

console.log(`Supabase public/client boundary passed (${filesToScan.length} files scanned).`);
