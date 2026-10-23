import { useEffect, useState } from "react";

export default function KnowledgeBaseExplorer({ apiBaseUrl }) {
  const [additives, setAdditives] = useState([]);
  const [filterLevel, setFilterLevel] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchKnowledgeBase() {
      setIsLoading(true);
      setError("");
      try {
        let url = `${apiBaseUrl}/additives/knowledge-base`;
        const params = new URLSearchParams();
        if (filterLevel !== "all") {
          params.append("concern_level", filterLevel);
        }
        if (searchQuery.trim()) {
          params.append("query", searchQuery.trim());
        }
        if (params.toString()) {
          url += `?${params.toString()}`;
        }

        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`Failed to load knowledge base (HTTP ${response.status})`);
        }
        const data = await response.json();
        setAdditives(data.additives || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }

    fetchKnowledgeBase();
  }, [apiBaseUrl, filterLevel, searchQuery]);

  return (
    <div className="knowledge-base-container">
      <div className="kb-header-card">
        <div className="card-heading">
          <div>
            <p className="step-label">CURATED ENCYCLOPEDIA</p>
            <h2>Food Additive & Ingredient Knowledge Base</h2>
          </div>
          <span className="optional-label">{additives.length} Entries</span>
        </div>
        <p className="kb-intro-text">
          Browse our scientifically vetted catalog of common food additives and ingredients. Each
          profile includes its primary functional purpose in food manufacturing, scientific
          evidence from regulatory agencies (EFSA, FDA, WHO/JECFA), and clear guidance on safety
          versus health concerns.
        </p>

        {/* Filter & Search Bar */}
        <div className="kb-controls">
          <div className="kb-filter-pills">
            <button
              type="button"
              className={`filter-pill ${filterLevel === "all" ? "active" : ""}`}
              onClick={() => setFilterLevel("all")}
            >
              All Additives
            </button>
            <button
              type="button"
              className={`filter-pill filter-high ${filterLevel === "high" ? "active" : ""}`}
              onClick={() => setFilterLevel("high")}
            >
              High Concern
            </button>
            <button
              type="button"
              className={`filter-pill filter-moderate ${
                filterLevel === "moderate" ? "active" : ""
              }`}
              onClick={() => setFilterLevel("moderate")}
            >
              Moderate Concern
            </button>
            <button
              type="button"
              className={`filter-pill filter-low ${filterLevel === "low" ? "active" : ""}`}
              onClick={() => setFilterLevel("low")}
            >
              Safe / Functional
            </button>
          </div>

          <div className="kb-search-box">
            <input
              type="text"
              placeholder="Search by name, E-number, or purpose (e.g. E171, sweetener, titanium)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search food additives knowledge base"
            />
            {searchQuery && (
              <button
                type="button"
                className="search-clear-btn"
                onClick={() => setSearchQuery("")}
                aria-label="Clear search"
              >
                ✕
              </button>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="form-error kb-error" role="alert">
          <span aria-hidden="true">!</span>
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="kb-loading">
          <span className="spinner" aria-hidden="true" />
          <p>Loading curated knowledge base…</p>
        </div>
      ) : additives.length === 0 ? (
        <div className="kb-empty">
          <p>No additives match your current filters or search query.</p>
          <button
            type="button"
            className="filter-pill active"
            onClick={() => {
              setFilterLevel("all");
              setSearchQuery("");
            }}
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="kb-grid">
          {additives.map((item) => {
            const levelClass = `level-${item.concern_level}`;
            const levelText =
              item.concern_level === "high"
                ? "High Concern"
                : item.concern_level === "moderate"
                ? "Moderate Concern"
                : "Safe / Functional";

            return (
              <article className={`kb-card ${levelClass}`} key={item.id}>
                <div className="kb-card-top">
                  <div>
                    <h3 className="kb-card-title">{item.name}</h3>
                    {item.e_number && <span className="e-number-pill">{item.e_number}</span>}
                  </div>
                  <span className={`concern-badge ${levelClass}`}>{levelText}</span>
                </div>

                <div className="kb-card-section">
                  <span className="kb-section-label">Functional Purpose:</span>
                  <p className="kb-section-content">{item.purpose}</p>
                </div>

                <div className="kb-card-section">
                  <span className="kb-section-label">Scientific Evidence & Health Notes:</span>
                  <p className="kb-section-content evidence-summary">{item.concern_summary}</p>
                </div>

                <div className="kb-card-section">
                  <span className="kb-section-label">Regulatory Status:</span>
                  <p className="kb-section-content regulatory-val">{item.regulatory_status}</p>
                </div>

                <div className="kb-recommendation-box">
                  <span className="tip-icon" aria-hidden="true">💡</span>
                  <p>{item.recommendation}</p>
                </div>

                <div className="kb-card-footer">
                  <span>Source: {item.evidence_source}</span>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
