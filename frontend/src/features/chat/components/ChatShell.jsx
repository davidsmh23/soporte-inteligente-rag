import { useEffect, useRef } from "react";

import { SourceList } from "../../../components/SourceList";
import { ChatComposer } from "./ChatComposer";
import { ChatMessage } from "./ChatMessage";

export function ChatShell({
  messages,
  traces,
  references,
  activeConversation,
  currentMode,
  modeLabel,
  isSending,
  uiError,
  onSendMessage,
}) {
  const feedEndRef = useRef(null);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  return (
    <section className="chat-shell">
      <header className="chat-header">
        <div>
          <p className="eyebrow">Validacion</p>
          <h2>Analisis del ticket</h2>
          <div className="chat-header-meta">
            <span>
              Conversacion: <code>{activeConversation?.conversation_id || "-"}</code>
            </span>
            <span>
              Modo: <code>{modeLabel || currentMode}</code>
            </span>
          </div>
        </div>
      </header>

      {uiError ? <div className="inline-alert">{uiError}</div> : null}

      <div className="chat-feed">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        <div ref={feedEndRef} aria-hidden="true" />
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
