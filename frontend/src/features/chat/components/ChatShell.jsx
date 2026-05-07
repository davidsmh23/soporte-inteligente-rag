import { StatusBadge } from "../../../components/StatusBadge";
import { SourceList } from "../../../components/SourceList";
import { ChatComposer } from "./ChatComposer";
import { ChatMessage } from "./ChatMessage";

function getBackendBadge(backendStatus) {
  if (backendStatus === "online") {
    return { tone: "success", label: "Backend conectado" };
  }

  if (backendStatus === "offline") {
    return { tone: "error", label: "Backend no disponible" };
  }

  return { tone: "neutral", label: "Verificando backend" };
}

export function ChatShell({
  messages,
  traces,
  references,
  backendStatus,
  activeConversation,
  currentMode,
  modeLabel,
  isSending,
  uiError,
  onSendMessage,
}) {
  const backendBadge = getBackendBadge(backendStatus);

  return (
    <section className="chat-shell">
      <header className="chat-header">
        <div>
          <p className="eyebrow">Consola conversacional</p>
          <h2>Session Gateway + SSE</h2>
          <div className="chat-header-meta">
            <span>
              Conversacion: <code>{activeConversation?.conversation_id || "-"}</code>
            </span>
            <span>
              Codex Session:{" "}
              <code>{activeConversation?.codex_session_id || "Pendiente bind"}</code>
            </span>
            <span>
              Modo: <code>{modeLabel || currentMode}</code>
            </span>
          </div>
        </div>
        <StatusBadge status={backendBadge.tone}>{backendBadge.label}</StatusBadge>
      </header>

      {uiError ? <div className="inline-alert">{uiError}</div> : null}

      <div className="chat-feed">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
      </div>

      <div className="chat-panels">
        <details className="sources panel-card" open={references.length > 0}>
          <summary>Referencias recientes</summary>
          <SourceList sources={references} />
        </details>

        <details className="sources panel-card">
          <summary>Trazas y cambios de modo</summary>
          {traces.length ? (
            <ul className="trace-list">
              {traces.map((trace) => (
                <li key={trace.id}>
                  <code>{trace.detail}</code>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-state">Todavia no hay trazas para esta conversacion.</p>
          )}
        </details>
      </div>

      <ChatComposer disabled={isSending} onSubmit={onSendMessage} />
    </section>
  );
}
