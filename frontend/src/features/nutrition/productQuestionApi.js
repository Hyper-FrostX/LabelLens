import { getApiErrorMessage } from "./nutritionUtils.js";
import { isRouteUnavailableStatus } from "./productAnalysisUtils.js";

export async function requestProductAnswer({
  apiBaseUrl,
  productContext,
  explanationLevel,
  accessToken,
  fetchImpl = globalThis.fetch,
  onLoadingChange = () => {},
  onAuthExpired = () => {},
}) {
  const headers = {
    "Content-Type": "application/json",
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
  };
  const body = JSON.stringify({
    question: productContext.question,
    context: productContext.context,
    explanation_level: explanationLevel === "expert" ? "detailed" : "standard",
  });
  const legacyBody = JSON.stringify({
    question: productContext.question,
    context: productContext.context,
  });

  onLoadingChange(true);
  try {
    let response = await fetchImpl(`${apiBaseUrl}/analyze/product/ask`, {
      method: "POST",
      headers,
      body,
    });
    if (isRouteUnavailableStatus(response.status)) {
      response = await fetchImpl(`${apiBaseUrl}/analyze/product/question`, {
        method: "POST",
        headers,
        body: legacyBody,
      });
    }
    if (response.status === 401 && accessToken) {
      onAuthExpired();
      const error = new Error("Your session expired. Sign in again.");
      error.status = 401;
      throw error;
    }

    let responseData;
    try {
      responseData = await response.json();
    } catch {
      throw new Error(
        response.ok
          ? "The backend returned an unreadable answer."
          : `Product Q&A failed (HTTP ${response.status}).`
      );
    }

    if (!response.ok) {
      if (isRouteUnavailableStatus(response.status)) {
        throw new Error(
          "Product Q&A is not available on this backend yet. Your label analysis is still available."
        );
      }
      throw new Error(
        getApiErrorMessage(responseData, response.status, "Product Q&A")
      );
    }
    if (!responseData || typeof responseData !== "object") {
      throw new Error("The backend returned an invalid answer.");
    }
    return responseData;
  } catch (requestError) {
    if (requestError instanceof TypeError) {
      throw new Error(
        `Could not connect to the Label Lens API at ${apiBaseUrl}. Check that the backend is running and the API URL is correct.`
      );
    }
    throw requestError;
  } finally {
    onLoadingChange(false);
  }
}
