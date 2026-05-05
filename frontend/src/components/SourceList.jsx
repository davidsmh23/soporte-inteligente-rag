export function SourceList({ sources }) {
  if (!sources?.length) {
    return null;
  }

  return (
    <details className="sources">
      <summary>Fuentes consultadas</summary>
      <ul>
        {sources.map((source) => (
          <li key={source}>
            <code>{source}</code>
          </li>
        ))}
      </ul>
    </details>
  );
}
