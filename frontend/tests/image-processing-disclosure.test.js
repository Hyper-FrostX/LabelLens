import assert from "node:assert/strict";
import test from "node:test";

import { IMAGE_PROCESSING_DISCLOSURE } from "../src/components/imageProcessingDisclosureText.js";

test("disclosure states local OCR and conditional Google Gemini image processing", () => {
  assert.match(IMAGE_PROCESSING_DISCLOSURE, /local OCR/);
  assert.match(IMAGE_PROCESSING_DISCLOSURE, /If Gemini Vision is enabled/);
  assert.match(IMAGE_PROCESSING_DISCLOSURE, /sent to Google Gemini/);
});
