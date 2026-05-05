import { StatusBadge } from "../../../components/StatusBadge";
import { ChatComposer } from "./ChatComposer";
import { ChatMessage } from "./ChatMessage";

export function ChatShell({
  messages,
  backendStatus,
  isSending,
  onSendMessage,
}) {
  const statusLabel =
    backendStatus === "online"
      ? "Backend conectado"
      : backendStatus === "offline"
        ? "Backend no disponible"
        : "Verificando backend";

  const statusTone =
    backendStatus === "online"
      ? "success"
      : backendStatus === "offline"
        ? "error"
        : "neutral";

  return (
    <section className="chat-shell">
      <header className="chat-header">
        <div>
          <p className="eyebrow">Consola conversacional</p>
          <h2>Revisión de tickets con RAG</h2>
        </div>
        <StatusBadge status={statusTone}>{statusLabel}</StatusBadge>
      </header>

      <div className="chat-feed">
        {messages.map((message, index) => (
          <ChatMessage
            key={`${message.role}-${index}-${message.content.slice(0, 24)}`}
            message={message}
          />
        ))}
      </div>

      <ChatComposer disabled={isSending} onSubmit={onSendMessage} />
    </section>
  );
}
