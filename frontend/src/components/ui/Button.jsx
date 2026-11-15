export default function Button({ className = "", ...props }) {
  const classes = ["submit-button", className].filter(Boolean).join(" ");
  return <button className={classes} {...props} />;
}
