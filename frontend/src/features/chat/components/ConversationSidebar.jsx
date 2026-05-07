import { ThemeToggle } from "../../../components/ThemeToggle";
import { StatusBadge } from "../../../components/StatusBadge";

function formatUpdatedAt(updatedAt) {
  if (!updatedAt) {
    return "--:--";
  }

  return new Intl.DateTimeFormat("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(updatedAt));
}

function getAgentBadge(agentStatus) {
  if (!agentStatus) {
    return { tone: "warning", label: "Sin estado" };
  }

  if (!agentStatus.connected) {
    return { tone: "warning", label: "No conectado" };
  }

  if (agentStatus.busy) {
    return { tone: "neutral", label: "Conectado y ocupado" };
  }

  return { tone: "success", label: "Conectado y libre" };
}

export function ConversationSidebar({
  conversations,
  activeConversationId,
  activeConversation,
  userId,
  userToken,
  onUserIdChange,
  onUserTokenChange,
  onSelectConversation,
  onCreateConversation,
  isLoadingConversations,
  agentStatus,
  theme,
  onToggleTheme,
}) {
  const agentBadge = getAgentBadge(agentStatus);

  return (
    <section className="conversation-sidebar">
      <div className="conversation-sidebar-header">
        <div>
          <p className="eyebrow">Sesion</p>
          <h2>Gateway</h2>
        </div>
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>

      <div className="session-panel">
        <label className="field-label" htmlFor="user-id-input">
          User ID
        </label>
        <input
          id="user-id-input"
          className="text-input"
          value={userId}
          onChange={(event) => onUserIdChange(event.target.value)}
        />

        <label className="field-label" htmlFor="user-token-input">
          User Token
        </label>
        <input
          id="user-token-input"
          className="text-input"
          type="password"
          value={userToken}
          onChange={(event) => onUserTokenChange(event.target.value)}
        />

        <div className="status-row">
          <span className="field-label compact">Agente local</span>
          <StatusBadge status={agentBadge.tone}>{agentBadge.label}</StatusBadge>
        </div>

        <div className="session-meta">
          <span>Conversacion activa</span>
          <code>{activeConversation?.conversation_id || "Sin seleccionar"}</code>
        </div>
        <div className="session-meta">
          <span>Codex Session ID</span>
          <code>{activeConversation?.codex_session_id || "Pendiente bind"}</code>
        </div>
      </div>

      <button
        type="button"
        className="secondary-button sidebar-action-button"
        onClick={onCreateConversation}
      >
        Nueva conversacion
      </button>

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
                <div className="conversation-item-meta">
                  <code>{conversation.codex_session_id || "Pendiente bind"}</code>
                  <span>{conversation.status || "unknown"}</span>
                </div>
              </button>
            );
          })
        )}
      </div>
    </section>
  );
}
