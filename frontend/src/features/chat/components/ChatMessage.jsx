import { SourceList } from "../../../components/SourceList";

export function ChatMessage({ message }) {
  return (
    <article className={`message-card ${message.role}`}>
      <div className="message-meta">
        <span>{message.role === "assistant" ? "Asistente" : "Operador"}</span>
      </div>
      <p className="message-content">{message.content}</p>
      <SourceList sources={message.sources} />
    </article>
  );
}
