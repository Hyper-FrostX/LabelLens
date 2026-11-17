import assert from "node:assert/strict";
import test from "node:test";

import { getAssistantModeLabel } from "../src/features/nutrition/productAnalysisUtils.js";
import { requestProductAnswer } from "../src/features/nutrition/productQuestionApi.js";

function response(status, payload, { malformed = false } = {}) {
  return {
    status,
    ok: status >= 200 && status < 300,
    async json() {
      if (malformed) throw new SyntaxError("invalid JSON");
      return payload;
    },
  };
}

test("requests an answer, exposes loading transitions, and preserves AI labeling", async () => {
  const calls = [];
  const loading = [];
  const answer = {
    answer: "The submitted label reports 6 g of protein.",
    response_mode: "AI_GENERATED",
    provider_status: "AVAILABLE",
    provider: "gemini",
  };

  const result = await requestProductAnswer({
    apiBaseUrl: "http://localhost:8000",
    productContext: {
      question: "How much protein?",
      context: { nutrition: { protein_g: 6 } },
    },
    explanationLevel: "expert",
    accessToken: "test-access-token",
    onLoadingChange: (value) => loading.push(value),
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      return response(200, answer);
    },
  });

  assert.deepEqual(loading, [true, false]);
  assert.equal(result.response_mode, "AI_GENERATED");
  assert.equal(
    getAssistantModeLabel(result),
    "AI-generated explanation · gemini · not independently verified"
  );
  assert.equal(
    calls[0].url,
    "http://localhost:8000/analyze/product/ask"
  );
  assert.equal(calls[0].options.headers.Authorization, "Bearer test-access-token");
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    question: "How much protein?",
    context: { nutrition: { protein_g: 6 } },
    explanation_level: "detailed",
  });
});

test("labels deterministic provider fallback separately from AI output", async () => {
  const result = await requestProductAnswer({
    apiBaseUrl: "http://localhost:8000",
    productContext: { question: "Question", context: {} },
    explanationLevel: "standard",
    fetchImpl: async () => response(200, {
      answer: "The report has no protein value.",
      response_mode: "DETERMINISTIC_FALLBACK",
      provider_status: "PROVIDER_RATE_LIMITED",
    }),
  });

  assert.equal(
    getAssistantModeLabel(result),
    "Deterministic analysis · provider rate limited"
  );
});

test("falls back to the legacy route only when the ask route is unavailable", async () => {
  const urls = [];
  const result = await requestProductAnswer({
    apiBaseUrl: "http://localhost:8000",
    productContext: { question: "Question", context: {} },
    explanationLevel: "standard",
    fetchImpl: async (url) => {
      urls.push(url);
      return urls.length === 1
        ? response(404, { detail: "Not found" })
        : response(200, { answer: "Legacy answer" });
    },
  });

  assert.deepEqual(urls, [
    "http://localhost:8000/analyze/product/ask",
    "http://localhost:8000/analyze/product/question",
  ]);
  assert.equal(result.answer, "Legacy answer");
});

test("returns readable HTTP and malformed-response errors and clears loading state", async () => {
  const loading = [];

  await assert.rejects(
    requestProductAnswer({
      apiBaseUrl: "http://localhost:8000",
      productContext: { question: "Question", context: {} },
      explanationLevel: "standard",
      onLoadingChange: (value) => loading.push(value),
      fetchImpl: async () => response(503, { detail: "Service unavailable" }),
    }),
    /Service unavailable/
  );
  assert.deepEqual(loading, [true, false]);

  await assert.rejects(
    requestProductAnswer({
      apiBaseUrl: "http://localhost:8000",
      productContext: { question: "Question", context: {} },
      explanationLevel: "standard",
      fetchImpl: async () => response(200, null, { malformed: true }),
    }),
    /unreadable answer/
  );
});

test("converts network failures into actionable frontend errors", async () => {
  await assert.rejects(
    requestProductAnswer({
      apiBaseUrl: "http://localhost:8000",
      productContext: { question: "Question", context: {} },
      explanationLevel: "standard",
      fetchImpl: async () => {
        throw new TypeError("fetch failed");
      },
    }),
    /Could not connect to the Label Lens API at http:\/\/localhost:8000/
  );
});
