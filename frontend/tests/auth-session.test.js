import assert from "node:assert/strict";
import test from "node:test";

import {
  createAuthSession,
  isAuthSessionExpired,
} from "../src/features/auth/authSession.js";

test("keeps a valid session in memory only until its server-provided expiry", () => {
  const session = createAuthSession("opaque-access-token", 60, 1000);
  assert.deepEqual(session, {
    accessToken: "opaque-access-token",
    expiresAt: 61000,
  });
  assert.equal(isAuthSessionExpired(session, 60999), false);
  assert.equal(isAuthSessionExpired(session, 61000), true);
});

test("rejects malformed or non-expiring sessions", () => {
  assert.equal(createAuthSession("", 60), null);
  assert.equal(createAuthSession("token", 0), null);
  assert.equal(createAuthSession("token", Number.NaN), null);
  assert.equal(isAuthSessionExpired(null), false);
});
