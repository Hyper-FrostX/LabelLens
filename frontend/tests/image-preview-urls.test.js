import assert from "node:assert/strict";
import test from "node:test";

import { revokeInactiveImagePreviewUrls } from "../src/components/imagePreviewUrls.js";

test("revokes replaced image URLs but retains the active preview", () => {
  const ownedUrls = new Set(["old-preview", "active-preview"]);
  const revokedUrls = [];

  revokeInactiveImagePreviewUrls(ownedUrls, "active-preview", (url) => {
    revokedUrls.push(url);
  });

  assert.deepEqual(revokedUrls, ["old-preview"]);
  assert.deepEqual([...ownedUrls], ["active-preview"]);
});

test("revokes all remaining image URLs when the component unmounts", () => {
  const ownedUrls = new Set(["first-preview", "second-preview"]);
  const revokedUrls = [];

  revokeInactiveImagePreviewUrls(ownedUrls, null, (url) => {
    revokedUrls.push(url);
  });

  assert.deepEqual(revokedUrls, ["first-preview", "second-preview"]);
  assert.equal(ownedUrls.size, 0);
});
