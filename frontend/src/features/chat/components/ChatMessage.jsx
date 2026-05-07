import { SourceList } from "../../../components/SourceList";

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
  return (
    <article className={`message-card ${message.role}`}>
      <div className="message-meta">
        <span>{message.role === "assistant" ? "Asistente" : "Operador"}</span>
        {message.isStreaming ? <span className="streaming-dot">Streaming</span> : null}
      </div>
      <p className="message-content">{message.content}</p>
      {renderTokenUsage(message.tokenUsage)}
      <SourceList sources={message.references} />
    </article>
  );
}
