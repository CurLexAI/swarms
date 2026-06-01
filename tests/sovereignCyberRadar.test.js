import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const TSX_BIN = join(ROOT, "node_modules", ".bin", "tsx");
const RADAR_TS = join(ROOT, "src", "security", "sovereignCyberRadar.ts");
const RADAR_SRC = readFileSync(RADAR_TS, "utf8");

function runRadar(args, ledgerPath) {
  return spawnSync(TSX_BIN, [RADAR_TS, ...args], {
    env: { ...process.env, RADAR_LEDGER_PATH: ledgerPath },
    encoding: "utf8",
    timeout: 20_000,
  });
}

function withTempLedger(fn) {
  const dir = mkdtempSync(join(tmpdir(), "radar-test-"));
  try {
    fn(join(dir, "ledger.jsonl"));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

function parseOutputDecisions(stdout) {
  // Each decision is a pretty-printed JSON block separated by whitespace.
  // Collect complete top-level objects by tracking brace depth.
  const decisions = [];
  let depth = 0;
  let current = "";

  for (const ch of stdout) {
    if (ch === "{") {
      depth++;
      current += ch;
    } else if (ch === "}") {
      current += ch;
      depth--;
      if (depth === 0 && current.trim()) {
        try {
          decisions.push(JSON.parse(current));
        } catch {
          // ignore malformed fragments
        }
        current = "";
      }
    } else if (depth > 0) {
      current += ch;
    }
  }
  return decisions;
}

// ── Static source checks ─────────────────────────────────────────────────────

test("sovereignCyberRadar source exports expected symbols", () => {
  assert.match(RADAR_SRC, /export\s+\{[\s\S]*SovereignCyberRadar/, "exports SovereignCyberRadar");
  assert.match(RADAR_SRC, /export\s+\{[\s\S]*SafeAttackSimulator/, "exports SafeAttackSimulator");
  assert.match(RADAR_SRC, /export\s+\{[\s\S]*EvidenceLedger/, "exports EvidenceLedger");
  assert.match(RADAR_SRC, /export\s+\{[\s\S]*createEvent/, "exports createEvent");
});

test("sovereignCyberRadar imports only node: built-in modules — no external network deps", () => {
  const importLines = RADAR_SRC
    .split("\n")
    .filter((line) => /^\s*import\s/.test(line));

  for (const line of importLines) {
    assert.match(
      line,
      /from\s+"node:/,
      `Import must use the node: protocol — found: ${line.trim()}`,
    );
  }
});

// ── Functional CLI tests (subprocess, no network) ────────────────────────────

test("simulate phishing exits 10 and produces SUSPICIOUS or BLOCKED verdict", () => {
  withTempLedger((ledger) => {
    const result = runRadar(["simulate", "phishing"], ledger);

    assert.equal(
      result.status,
      10,
      `Expected exit 10 (threat detected). stderr: ${result.stderr}`,
    );

    const decisions = parseOutputDecisions(result.stdout);
    assert.ok(decisions.length > 0, "Must produce at least one JSON decision");

    const hasHighVerdict = decisions.some(
      (d) => d.decision?.verdict === "SUSPICIOUS" || d.decision?.verdict === "BLOCKED",
    );
    assert.ok(
      hasHighVerdict,
      `Expected SUSPICIOUS or BLOCKED. Got: ${decisions.map((d) => d.decision?.verdict).join(", ")}`,
    );
  });
});

test("simulate prompt-injection exits 10 and flags prompt injection rule", () => {
  withTempLedger((ledger) => {
    const result = runRadar(["simulate", "prompt-injection"], ledger);

    assert.equal(result.status, 10, `Expected exit 10. stderr: ${result.stderr}`);

    const decisions = parseOutputDecisions(result.stdout);
    const injectionHit = decisions
      .flatMap((d) => d.decision?.findings ?? [])
      .some((f) => f.ruleId === "radar.prompt.injection");

    assert.ok(injectionHit, "Expected a radar.prompt.injection finding");
  });
});

test("simulate dependency-confusion exits 10 and flags dependency confusion rule", () => {
  withTempLedger((ledger) => {
    const result = runRadar(["simulate", "dependency-confusion"], ledger);

    assert.equal(result.status, 10, `Expected exit 10. stderr: ${result.stderr}`);

    const decisions = parseOutputDecisions(result.stdout);
    const depHit = decisions
      .flatMap((d) => d.decision?.findings ?? [])
      .some((f) => f.ruleId === "radar.dependency.confusion");

    assert.ok(depHit, "Expected a radar.dependency.confusion finding");
  });
});

test("scan-url exits 10 for raw-IP credential-embedded URL", () => {
  withTempLedger((ledger) => {
    // IP host + embedded credentials + long query string (>180 chars) → SUSPICIOUS
    const suspiciousUrl =
      "http://admin:secret@192.0.2.1/verify.zip?token=abc123def456&session=xyz789abc&redirect=https%3A%2F%2Faccount.example.com%2Fpassword-reset%2Fconfirm&user_email=admin%40example.com&lang=en&expires=3600&nonce=qwerty";

    const result = runRadar(["scan-url", suspiciousUrl], ledger);

    assert.equal(result.status, 10, `Expected exit 10. stderr: ${result.stderr}`);

    const [decision] = parseOutputDecisions(result.stdout);
    assert.ok(
      decision?.decision?.verdict === "SUSPICIOUS" || decision?.decision?.verdict === "BLOCKED",
      `Expected SUSPICIOUS or BLOCKED, got: ${decision?.decision?.verdict}`,
    );
  });
});

test("scan-url exits 0 for plain HTTPS domain", () => {
  withTempLedger((ledger) => {
    const result = runRadar(["scan-url", "https://www.example.com/page"], ledger);

    assert.equal(result.status, 0, `Expected exit 0 for safe URL. stderr: ${result.stderr}`);

    const [decision] = parseOutputDecisions(result.stdout);
    assert.ok(
      decision?.decision?.verdict === "SAFE" || decision?.decision?.verdict === "WATCH",
      `Expected SAFE or WATCH, got: ${decision?.decision?.verdict}`,
    );
  });
});

test("evidence ledger is written as valid JSONL with chained hashes", () => {
  withTempLedger((ledger) => {
    runRadar(["simulate", "ci-cd-abuse"], ledger);

    const lines = readFileSync(ledger, "utf8")
      .trim()
      .split("\n")
      .filter(Boolean)
      .map((l) => JSON.parse(l));

    assert.ok(lines.length >= 2, "Ledger must have at least two records");
    assert.equal(lines[0].previousHash, "GENESIS", "First record must chain to GENESIS");

    for (let i = 1; i < lines.length; i++) {
      assert.equal(
        lines[i].previousHash,
        lines[i - 1].recordHash,
        `Record ${i} previousHash must equal record ${i - 1} recordHash`,
      );
    }
  });
});
