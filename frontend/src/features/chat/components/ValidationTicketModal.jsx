function formatUpdatedAt(updatedAt) {
  if (!updatedAt) {
    return "--:--";
  }

  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(updatedAt));
}

export function ValidationTicketModal({
  conversations,
  activeConversationId,
  isOpen,
  onClose,
  onSelectConversation,
}) {
  if (!isOpen) {
    return null;
  }

  const handleSelect = async (conversationId) => {
    await onSelectConversation(conversationId);
  };

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="validation-ticket-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <p className="eyebrow">Validar ticket</p>
            <h2 id="validation-ticket-title">Selecciona una conversacion</h2>
          </div>
          <button type="button" className="secondary-button compact-button" onClick={onClose}>
            Cerrar
          </button>
        </div>

        <div className="modal-conversation-list" role="list">
          {conversations.length === 0 ? (
            <p className="empty-state">No hay conversaciones disponibles.</p>
          ) : (
            conversations.map((conversation) => {
              const isActive = conversation.conversation_id === activeConversationId;

              return (
                <button
                  key={conversation.conversation_id}
                  type="button"
                  className={`conversation-item ${isActive ? "active" : ""}`}
                  onClick={() => handleSelect(conversation.conversation_id)}
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
    </div>
  );
}
