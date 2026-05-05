export function ThemeToggle({ theme, onToggle }) {
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={onToggle}
      aria-label={`Cambiar a modo ${isDark ? "claro" : "oscuro"}`}
      aria-pressed={isDark}
    >
      <span className="theme-toggle-track">
        <span className="theme-toggle-label">{isDark ? "Dark" : "Light"}</span>
        <span className="theme-toggle-thumb" />
      </span>
    </button>
  );
}
