import assert from "node:assert/strict";
import test from "node:test";

import { fetchScanHistoryPage } from "../src/features/nutrition/scanHistoryApi.js";

function response(status, data) {
  return {
    status,
    ok: status >= 200 && status < 300,
    async json() {
      return data;
    },
  };
}

test("requests the requested history offset and reports another page", async () => {
  let request;
  const result = await fetchScanHistoryPage({
    apiBaseUrl: "http://localhost:8000",
    accessToken: "in-memory-token",
    offset: 20,
    limit: 20,
    fetchImpl: async (url, options) => {
      request = { url, options };
      return response(200, Array.from({ length: 20 }, (_, id) => ({ id })));
    },
  });

  assert.equal(request.url, "http://localhost:8000/scans?limit=20&offset=20");
  assert.equal(request.options.headers.Authorization, "Bearer in-memory-token");
  assert.equal(result.scans.length, 20);
  assert.equal(result.hasMore, true);
});

test("marks a short final page and invalidates expired authentication", async () => {
  const finalPage = await fetchScanHistoryPage({
    apiBaseUrl: "http://localhost:8000",
    accessToken: "token",
    offset: 20,
    fetchImpl: async () => response(200, [{ id: 21 }]),
  });
  assert.equal(finalPage.hasMore, false);

  let expired = 0;
  await assert.rejects(
    fetchScanHistoryPage({
      apiBaseUrl: "http://localhost:8000",
      accessToken: "expired-token",
      offset: 0,
      onAuthExpired: () => { expired += 1; },
      fetchImpl: async () => response(401, { detail: "Not authenticated" }),
    }),
    /session expired/i,
  );
  assert.equal(expired, 1);
});
