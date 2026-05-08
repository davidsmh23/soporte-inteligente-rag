import { ThemeToggle } from "../../../components/ThemeToggle";

function formatUpdatedAt(updatedAt) {
  if (!updatedAt) {
    return "--:--";
  }

  return new Intl.DateTimeFormat("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(updatedAt));
}

export function ConversationSidebar({
  conversations,
  activeConversationId,
  activeConversation,
  userId,
  onSelectConversation,
  onOpenValidationSelector,
  onCreateConversation,
  isLoadingConversations,
  errorMessage,
  theme,
  onToggleTheme,
}) {
  return (
    <section className="conversation-sidebar">
      <div className="conversation-sidebar-header">
        <div>
          <p className="eyebrow">Operador</p>
          <h2>{userId}</h2>
        </div>
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>

      <div className="session-panel">
        <span className="field-label compact">Conversacion activa</span>
        <code>{activeConversation?.conversation_id || "Sin seleccionar"}</code>
      </div>

      {errorMessage ? <div className="inline-alert sidebar-alert">{errorMessage}</div> : null}

      <div className="sidebar-actions">
        <button
          type="button"
          className="primary-button sidebar-action-button"
          onClick={onOpenValidationSelector}
        >
          Validar ticket
        </button>

        <button
          type="button"
          className="secondary-button sidebar-action-button"
          onClick={onCreateConversation}
        >
          Nueva conversacion
        </button>
      </div>

      <div className="conversation-list-header">
        <p className="field-label compact">Conversaciones</p>
      </div>

      <div className="conversation-list" role="list">
        {isLoadingConversations ? (
          <p className="empty-state">Cargando conversaciones...</p>
        ) : conversations.length === 0 ? (
          <p className="empty-state">Sin conversaciones guardadas todavia.</p>
        ) : (
          conversations.map((conversation) => {
            const isActive =
              conversation.conversation_id === activeConversationId;

            return (
              <button
                key={conversation.conversation_id}
                type="button"
                className={`conversation-item ${isActive ? "active" : ""}`}
                onClick={() => onSelectConversation(conversation.conversation_id)}
              >
                <div className="conversation-item-top">
                  <strong>{conversation.title}</strong>
                  <span>{formatUpdatedAt(conversation.last_message_at)}</span>
                </div>
                <p>{conversation.preview}</p>
              </button>
            );
          })
        )}
      </div>
    </section>
  );
}
