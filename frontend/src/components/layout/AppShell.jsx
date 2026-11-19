export default function AppShell({
  activeSection,
  onNavigate,
  headerAction,
  onboarding = false,
  children,
}) {
  return (
    <div className="app-shell">
      <header className="site-header">
        <a
          className="brand"
          href="/"
          aria-label="LabelLens home"
          onClick={(event) => {
            event.preventDefault();
            onNavigate("analyzer");
          }}
        >
          <span className="brand-mark" aria-hidden="true">LL</span>
          <span>LabelLens</span>
        </a>
        {!onboarding && (
          <nav className="header-nav" aria-label="Main navigation">
            <button
              type="button"
              className={activeSection === "analyzer" ? "active" : ""}
              aria-current={activeSection === "analyzer" ? "page" : undefined}
              onClick={() => onNavigate("analyzer")}
            >
              Label Analyzer
            </button>
            <button
              type="button"
              className={activeSection === "preferences" ? "active" : ""}
              aria-current={activeSection === "preferences" ? "page" : undefined}
              onClick={() => onNavigate("preferences")}
            >
              Health Preferences
            </button>
            <button
              type="button"
              className={activeSection === "fssai" ? "active" : ""}
              aria-current={activeSection === "fssai" ? "page" : undefined}
              onClick={() => onNavigate("fssai")}
            >
              FSSAI
            </button>
          </nav>
        )}
        <div className="header-right">
          <span className="engine-status">
            <span aria-hidden="true" />
            AI Engine Ready
          </span>
          {headerAction}
        </div>
      </header>
      <div className="main-stage">{children}</div>
      <footer className="page-footer">
        <a className="footer-brand" href="/" onClick={(event) => {
          event.preventDefault();
          onNavigate("analyzer");
        }}>LabelLens</a>
        <span>Food-label insights to help you make informed choices.</span>
      </footer>
    </div>
  );
}
