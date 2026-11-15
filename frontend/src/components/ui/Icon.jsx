const iconPaths = {
  overview: (
    <>
      <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
      <rect x="13.5" y="3.5" width="7" height="7" rx="1.5" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="1.5" />
      <rect x="13.5" y="13.5" width="7" height="7" rx="1.5" />
    </>
  ),
  scan: (
    <>
      <path d="M8 3.75H5.75A2 2 0 0 0 3.75 5.75V8" />
      <path d="M16 3.75h2.25a2 2 0 0 1 2 2V8" />
      <path d="M20.25 16v2.25a2 2 0 0 1-2 2H16" />
      <path d="M8 20.25H5.75a2 2 0 0 1-2-2V16" />
      <path d="M7.5 12h9" />
    </>
  ),
  ingredients: (
    <>
      <circle cx="5" cy="6" r="1" />
      <path d="M9 6h10" />
      <circle cx="5" cy="12" r="1" />
      <path d="M9 12h10" />
      <circle cx="5" cy="18" r="1" />
      <path d="M9 18h10" />
    </>
  ),
  book: (
    <>
      <path d="M4.5 5.25A2.25 2.25 0 0 1 6.75 3H20v17H6.75A2.25 2.25 0 0 0 4.5 22z" />
      <path d="M4.5 5.25v16.5M8 7h8M8 11h7" />
    </>
  ),
  compare: (
    <>
      <path d="M7 4v16M17 4v16M4 8l3-4 3 4M14 16l3 4 3-4" />
      <path d="M10 8h4M10 16h4" />
    </>
  ),
  alternatives: (
    <>
      <path d="M12 20.5s-7.5-4.2-7.5-10.1A4.4 4.4 0 0 1 12 7.7a4.4 4.4 0 0 1 7.5 2.7c0 5.9-7.5 10.1-7.5 10.1z" />
      <path d="M12 4.5V2.75M8.25 5.4 7 4.15M15.75 5.4 17 4.15" />
    </>
  ),
  history: (
    <>
      <path d="M4.25 8.5A8 8 0 1 1 4 13" />
      <path d="M4.25 4.5v4h4M12 7.5v5l3 1.75" />
    </>
  ),
  profile: (
    <>
      <circle cx="12" cy="8" r="3.25" />
      <path d="M5 20a7 7 0 0 1 14 0" />
    </>
  ),
  sparkle: (
    <>
      <path d="m12 3 1.55 5.45L19 10l-5.45 1.55L12 17l-1.55-5.45L5 10l5.45-1.55z" />
      <path d="m19 15 .75 2.25L22 18l-2.25.75L19 21l-.75-2.25L16 18l2.25-.75z" />
    </>
  ),
  check: <path d="m5 12.5 4.25 4.25L19 7" />,
  close: (
    <>
      <path d="m6 6 12 12" />
      <path d="M18 6 6 18" />
    </>
  ),
};

export default function Icon({ name, size = 20, className = "" }) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {iconPaths[name] ?? iconPaths.sparkle}
    </svg>
  );
}
