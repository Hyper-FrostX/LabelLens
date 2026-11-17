import { useState } from "react";

import Button from "../../components/ui/Button";
import { getAssistantModeLabel } from "./productAnalysisUtils";
import { requestProductAnswer } from "./productQuestionApi";

export default function ProductQuestionAnswer({
  apiBaseUrl,
  productContext,
  explanationLevel,
  accessToken,
  onAuthExpired,
}) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState("");
  const [isAsking, setIsAsking] = useState(false);

  async function submitQuestion(event) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isAsking) return;

    setError("");
    setAnswer(null);
    try {
      const responseData = await requestProductAnswer({
        apiBaseUrl,
        productContext: {
          question: trimmedQuestion,
          context: productContext,
        },
        explanationLevel,
        accessToken,
        onAuthExpired,
        onLoadingChange: setIsAsking,
      });
      setAnswer(responseData);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  return (
    <section className="product-qa-section" aria-labelledby="product-qa-title">
      <h3 id="product-qa-title">Ask about this product</h3>
      <p>
        Uses the configured server-side AI assistant when available, otherwise
        a deterministic product-data fallback. AI explanations are not verified
        facts and are limited to this report.
      </p>
      <p className="product-qa-privacy">
        When enabled by the server, your question and this report context
        (including any profile assessment) are sent to the configured AI
        provider. Avoid including personal information in your question.
      </p>
      <form onSubmit={submitQuestion} aria-busy={isAsking}>
        <label className="input-group" htmlFor="product-question">
          <span className="input-label">Your question</span>
          <textarea
            id="product-question"
            rows="3"
            maxLength="500"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="For example, what does the label say about added sugar?"
            required
          />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <Button type="submit" disabled={isAsking || !question.trim()}>
          {isAsking ? "Asking…" : "Ask about this label"}
        </Button>
      </form>
      {answer && (
        <div className="product-qa-answer" aria-live="polite">
          <p className="product-qa-mode" role="status">
            {getAssistantModeLabel(answer)}
          </p>
          {typeof answer.answer === "string" ? (
            <p>{answer.answer}</p>
          ) : answer.answer != null ? (
            <pre>{JSON.stringify(answer.answer, null, 2)}</pre>
          ) : (
            <p>The backend did not return an answer.</p>
          )}
          {answer.evidence != null && (
            <details>
              <summary>
                {answer.response_mode === "AI_GENERATED"
                  ? "Evidence paths supplied to the AI"
                  : "Evidence used"}
              </summary>
              <pre>{JSON.stringify(answer.evidence, null, 2)}</pre>
            </details>
          )}
          {answer.missing_information?.length > 0 && (
            <div>
              <strong>Information not available</strong>
              <ul>
                {answer.missing_information.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {answer.limitations != null && (
            <div>
              <strong>Limitations</strong>
              {Array.isArray(answer.limitations) ? (
                <ul>
                  {answer.limitations.map((limitation, index) => (
                    <li key={index}>{typeof limitation === "string" ? limitation : JSON.stringify(limitation)}</li>
                  ))}
                </ul>
              ) : (
                <p>{typeof answer.limitations === "string" ? answer.limitations : JSON.stringify(answer.limitations)}</p>
              )}
            </div>
          )}
          {answer.limitations == null && (
            <p className="product-qa-limitation-status">
              No separate limitations field was returned by the backend.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
