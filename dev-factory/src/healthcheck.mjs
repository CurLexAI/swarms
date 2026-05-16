import { request } from 'node:http';
import { Socket } from 'node:net';

const httpTargets = [
  { name: 'Qdrant', url: 'http://127.0.0.1:6333/readyz' },
  { name: 'MinIO', url: 'http://127.0.0.1:9000/minio/health/live' },
  { name: 'Ollama', url: 'http://127.0.0.1:11434/api/tags' }
];

const tcpTargets = [
  { name: 'PostgreSQL', host: '127.0.0.1', port: 5432 },
  { name: 'Redis', host: '127.0.0.1', port: 6379 }
];

function checkHttp(name, url) {
  return new Promise((resolve) => {
    const req = request(url, { method: 'GET', timeout: 4000 }, (res) => {
      const ok = (res.statusCode ?? 500) < 500;
      resolve({ name, ok, detail: `HTTP ${res.statusCode ?? 'ERR'}` });
      res.resume();
    });

    req.on('timeout', () => {
      req.destroy(new Error('timeout'));
    });

    req.on('error', (error) => {
      resolve({ name, ok: false, detail: error.message });
    });

    req.end();
  });
}

function checkTcp(name, host, port) {
  return new Promise((resolve) => {
    const socket = new Socket();
    socket.setTimeout(4000);

    socket.on('connect', () => {
      socket.destroy();
      resolve({ name, ok: true, detail: `TCP ${host}:${port}` });
    });

    socket.on('timeout', () => {
      socket.destroy();
      resolve({ name, ok: false, detail: 'timeout' });
    });

    socket.on('error', (error) => {
      resolve({ name, ok: false, detail: error.message });
    });

    socket.connect(port, host);
  });
}

async function main() {
  const results = [
    ...(await Promise.all(httpTargets.map((target) => checkHttp(target.name, target.url)))),
    ...(await Promise.all(tcpTargets.map((target) => checkTcp(target.name, target.host, target.port))))
  ];

  let failed = false;
  for (const result of results) {
    const status = result.ok ? 'OK' : 'FAIL';
    console.log(`${status.padEnd(4)} ${result.name} - ${result.detail}`);
    if (!result.ok) {
      failed = true;
    }
  }

  if (failed) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
