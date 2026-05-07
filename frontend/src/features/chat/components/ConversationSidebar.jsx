import { ThemeToggle } from "../../../components/ThemeToggle";

function getPreview(messages) {
  const lastMessage = [...messages]
    .reverse()
    .find((message) => !message.isIntro);

  return lastMessage?.content || "Sin actividad todavia";
}

function formatUpdatedAt(updatedAt) {
  return new Intl.DateTimeFormat("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(updatedAt);
}

export function ConversationSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onCreateConversation,
  theme,
  onToggleTheme,
}) {
  return (
    <section className="conversation-sidebar">
      <div className="conversation-sidebar-header">
        <div>
          <p className="eyebrow">Conversaciones</p>
          <h2>Historial</h2>
        </div>
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>

      <button
        type="button"
        className="secondary-button sidebar-action-button"
        onClick={onCreateConversation}
      >
        Nueva conversacion
      </button>

      <div className="conversation-list" role="list">
        {conversations.map((conversation) => {
          const isActive = conversation.id === activeConversationId;

          return (
            <button
              key={conversation.id}
              type="button"
              className={`conversation-item ${isActive ? "active" : ""}`}
              onClick={() => onSelectConversation(conversation.id)}
            >
              <div className="conversation-item-top">
                <strong>{conversation.title}</strong>
                <span>{formatUpdatedAt(conversation.updatedAt)}</span>
              </div>
              <p>{getPreview(conversation.messages)}</p>
            </button>
          );
        })}
      </div>
    </section>
  );
}
