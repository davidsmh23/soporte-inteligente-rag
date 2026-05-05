export function StatusBadge({ status, children }) {
  return <span className={`status-badge status-${status}`}>{children}</span>;
}
