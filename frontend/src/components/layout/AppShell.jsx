import Icon from "../ui/Icon";

const navigationGroups = [
  {
    label: "Workspace",
    items: [
      { id: "overview", label: "Overview", icon: "overview", planned: true },
      { id: "scan", label: "Scan Food", icon: "scan" },
    ],
  },
  {
    label: "Explore",
    items: [
      { id: "ingredients", label: "Ingredient Explorer", icon: "ingredients" },
      { id: "knowledge", label: "Knowledge Base", icon: "book" },
    ],
  },
  {
    label: "Product tools",
    items: [
      { id: "alternatives", label: "Stored-product Alternatives", icon: "alternatives" },
    ],
  },
  {
    label: "Your space",
    items: [
      { id: "history", label: "Scan History", icon: "history" },
      { id: "profile", label: "My Health Profile", icon: "profile" },
    ],
  },
];

export default function AppShell({
  activeSection,
  onNavigate,
  title,
  eyebrow,
  description,
  children,
}) {
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <a className="brand" href="/" aria-label="Label Lens home">
          <span className="brand-mark" aria-hidden="true">LL</span>
          <span className="brand-name">LabelLens</span>
        </a>
        <p className="brand-caption">FOOD INTELLIGENCE</p>

        <nav className="primary-nav" aria-label="Main navigation">
          {navigationGroups.map((group) => (
            <div className="nav-group" key={group.label}>
              <p className="nav-group-label">{group.label}</p>
              <div className="nav-group-items">
                {group.items.map((item) => (
                  <button
                    className={`nav-item ${activeSection === item.id ? "active" : ""} ${item.planned ? "planned" : ""}`}
                    type="button"
                    key={item.id}
                    disabled={item.planned}
                    aria-current={activeSection === item.id ? "page" : undefined}
                    title={item.planned ? "Planned for a future release" : undefined}
                    onClick={() => onNavigate(item.id)}
                  >
                    <Icon name={item.icon} size={18} />
                    <span>{item.label}</span>
                    {item.planned && <span className="planned-label">Planned</span>}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="sidebar-note">
          <span className="sidebar-note-mark" aria-hidden="true" />
          <p>Evidence-led insights. Always verify the package.</p>
        </div>
      </aside>

      <div className="main-stage">
        <header className="topbar">
          <p className="breadcrumb">
            LABEL LENS <span aria-hidden="true">/</span> {title}
          </p>
          <span className="workspace-label">Food label workspace</span>
        </header>

        <main className="main-content">
          <section className="page-intro">
            <p className="eyebrow">{eyebrow}</p>
            <h1>{title}</h1>
            <p className="intro-copy">{description}</p>
          </section>
          {children}
          <footer className="page-footer">
            <span>LabelLens</span>
            <span>Informational insights, not medical advice.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
