import { getApiErrorMessage } from "./nutritionUtils.js";

export async function fetchScanHistoryPage({
  apiBaseUrl,
  accessToken,
  offset,
  limit = 20,
  fetchImpl = globalThis.fetch,
  onAuthExpired,
}) {
  const response = await fetchImpl(
    `${apiBaseUrl}/scans?limit=${limit}&offset=${offset}`,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(
      response.ok
        ? "The backend returned an unreadable scan-history response."
        : `Scan history failed (HTTP ${response.status}).`,
    );
  }
  if (!response.ok) {
    if (response.status === 401 && onAuthExpired) {
      onAuthExpired();
      const error = new Error("Your session expired. Sign in again.");
      error.status = 401;
      throw error;
    }
    throw new Error(getApiErrorMessage(data, response.status, "Scan history"));
  }
  if (!Array.isArray(data)) {
    throw new Error("The backend returned an invalid scan-history response.");
  }
  return {
    scans: data,
    hasMore: data.length === limit,
  };
}
