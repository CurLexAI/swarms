const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const TURNSTILE_SECRET = process.env.TURNSTILE_SECRET || '';

function isObject(v){ return typeof v === 'object' && v !== null && !Array.isArray(v); }

export function validateContactPayload(payload){
  if (!isObject(payload)) return { ok:false, reason:'malformed_payload' };
  const keys = Object.keys(payload);
  const allowed = ['name','email','message','company','nonce','turnstileToken'];
  const unknown = keys.filter((k)=>!allowed.includes(k));
  if (unknown.length) return { ok:false, reason:'unknown_fields', unknown };
  if (typeof payload.name !== 'string' || payload.name.trim().length < 2 || payload.name.length > 120) return { ok:false, reason:'invalid_name' };
  if (typeof payload.email !== 'string' || !EMAIL_REGEX.test(payload.email)) return { ok:false, reason:'invalid_email' };
  if (typeof payload.message !== 'string' || payload.message.trim().length < 10 || payload.message.length > 5000) return { ok:false, reason:'invalid_message' };
  if (payload.company !== undefined && typeof payload.company !== 'string') return { ok:false, reason:'invalid_company' };
  if (typeof payload.nonce !== 'string' || payload.nonce.length < 12 || payload.nonce.length > 120) return { ok:false, reason:'invalid_nonce' };
  if (typeof payload.turnstileToken !== 'string' || payload.turnstileToken.length < 10) return { ok:false, reason:'invalid_turnstile' };
  return { ok:true };
}

export function createInMemoryRateLimiter({ windowMs = 60_000, limit = 10 } = {}){
  const hits = new Map();
  return function checkRateLimit(ip){
    const now = Date.now();
    const row = hits.get(ip) || { count:0, resetAt: now + windowMs };
    if (now > row.resetAt) { row.count = 0; row.resetAt = now + windowMs; }
    row.count += 1;
    hits.set(ip,row);
    return { allowed: row.count <= limit, remaining: Math.max(0, limit - row.count), resetAt: row.resetAt };
  };
}

export async function verifyTurnstileToken(token, remoteip, fetchImpl = fetch){
  if (!TURNSTILE_SECRET) return { ok:false, reason:'SECRET_MISSING' };
  const res = await fetchImpl('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ secret: TURNSTILE_SECRET, response: token, remoteip: remoteip || '' })
  });
  if (!res.ok) return { ok:false, reason:'turnstile_http_error' };
  const data = await res.json();
  return { ok: !!data.success, reason: data['error-codes']?.[0] || null };
}

const seenNonces = new Map();
export function detectReplay(nonce, ttlMs = 5 * 60_000){
  const now = Date.now();
  for (const [key,expires] of seenNonces.entries()) {
    if (expires <= now) seenNonces.delete(key);
  }
  if (seenNonces.has(nonce)) return true;
  seenNonces.set(nonce, now + ttlMs);
  return false;
}

export function toPublicError(){
  return { error: 'Request rejected. Please verify input and retry.' };
}

export function toSanitizedLog(err, context = {}){
  const baseMessage = err instanceof Error ? err.message : String(err);
  const redacted = baseMessage.replace(/(token|secret|password)=([^\s&]+)/ig, '$1=[REDACTED]');
  return { message: redacted.slice(0, 300), context };
}
