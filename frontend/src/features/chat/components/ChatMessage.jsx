import { SourceList } from "../../../components/SourceList";

function MessageAvatar({ role }) {
  if (role === "assistant") {
    return (
      <span className="message-avatar" aria-hidden="true">
        <svg viewBox="0 0 24 24" focusable="false">
          <path d="M12 2a1 1 0 0 1 1 1v1.07a8 8 0 0 1 6 6H20a1 1 0 1 1 0 2h-1.07a8 8 0 0 1-6 6V20a1 1 0 1 1-2 0v-1.07a8 8 0 0 1-6-6H4a1 1 0 1 1 0-2h1.07a8 8 0 0 1 6-6V3a1 1 0 0 1 1-1Zm0 4a6 6 0 1 0 0 12a6 6 0 0 0 0-12Zm-2 4a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0v-2a1 1 0 0 1 1-1Zm4 0a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0v-2a1 1 0 0 1 1-1Z" />
        </svg>
      </span>
    );
  }

  return (
    <span className="message-avatar" aria-hidden="true">
      <svg viewBox="0 0 24 24" focusable="false">
        <path d="M12 12a4 4 0 1 0-4-4a4 4 0 0 0 4 4Zm0 2c-4.42 0-8 2.24-8 5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1c0-2.76-3.58-5-8-5Z" />
      </svg>
    </span>
  );
}

function renderTokenUsage(tokenUsage) {
  if (!tokenUsage) {
    return null;
  }

  return (
    <p className="token-usage">
      Tokens: entrada={tokenUsage.input_tokens || 0} salida=
      {tokenUsage.output_tokens || 0} total={tokenUsage.total_tokens || 0} metodo=
      {tokenUsage.method || "unknown"}
    </p>
  );
}

export function ChatMessage({ message }) {
  const speakerLabel = message.role === "assistant" ? "Asistente IA" : "Operador";

  return (
    <article className={`message-card ${message.role}`}>
      <div className="message-row">
        <MessageAvatar role={message.role} />
        <div className="message-body">
          <div className="message-meta">
            <span>{speakerLabel}</span>
            {message.isStreaming ? <span className="streaming-dot">Streaming</span> : null}
          </div>
          <p className="message-content">{message.content}</p>
          {renderTokenUsage(message.tokenUsage)}
          <SourceList sources={message.references} />
        </div>
      </div>
    </article>
  );
}
