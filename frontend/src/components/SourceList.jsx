export function SourceList({ sources }) {
  if (!sources?.length) {
    return null;
  }

  return (
    <div className="sources-body">
      <ul>
        {sources.map((source, index) => {
          const label =
            typeof source === "string"
              ? source
              : source.ticket_id
                ? `${source.ticket_id} (${source.source || "unknown"})`
                : source.source || `Referencia ${index + 1}`;
          const snippet =
            typeof source === "string"
              ? ""
              : source.snippet || source.problem_title || "";

          return (
            <li key={`${label}-${index}`}>
              <code>{label}</code>
              {snippet ? <p>{snippet}</p> : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
