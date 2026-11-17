export function createAuthSession(accessToken, expiresInSeconds, now = Date.now()) {
  const lifetime = Number(expiresInSeconds);
  if (
    typeof accessToken !== "string" ||
    !accessToken.trim() ||
    !Number.isFinite(lifetime) ||
    lifetime <= 0
  ) {
    return null;
  }
  return {
    accessToken,
    expiresAt: now + lifetime * 1000,
  };
}

export function isAuthSessionExpired(session, now = Date.now()) {
  return Boolean(session && (!Number.isFinite(session.expiresAt) || now >= session.expiresAt));
}
