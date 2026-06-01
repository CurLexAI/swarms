export function buildContentSecurityPolicy(apiOrigin: string): string {
  const trimmed = apiOrigin.trim();
  if (!trimmed) throw new Error('CONFIG_NOT_FOUND: API_ORIGIN is required');
  const normalizedApi = new URL(trimmed).origin;
  return [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "font-src 'self'",
    `connect-src 'self' ${normalizedApi}`,
    "frame-ancestors 'none'",
    "base-uri 'self'"
  ].join('; ');
}
