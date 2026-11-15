export default function Spinner({ className = "" }) {
  const classes = ["spinner", className].filter(Boolean).join(" ");
  return <span className={classes} aria-hidden="true" />;
}
