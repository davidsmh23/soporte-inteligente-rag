import { useEffect, useMemo, useState } from "react";

function createResponseItems(messages) {
  return messages
    .filter((message) => message.role === "assistant" && !message.isIntro && message.content.trim())
    .map((message, index) => ({
      id: message.id || `assistant-response-${index + 1}`,
      label: index + 1,
      content: message.content,
      checked: false,
    }));
}

export function ValidationResponseModal({
  isOpen,
  conversation,
  messages,
  onClose,
  onBack,
}) {
  const [items, setItems] = useState([]);

  const title = useMemo(() => conversation?.title || "Conversacion seleccionada", [conversation]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    setItems(createResponseItems(messages));
  }, [isOpen, messages]);

  if (!isOpen) {
    return null;
  }

  const moveItem = (index, direction) => {
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= items.length) {
      return;
    }

    setItems((current) => {
      const next = [...current];
      const [item] = next.splice(index, 1);
      next.splice(nextIndex, 0, item);
      return next;
    });
  };

  const toggleChecked = (itemId) => {
    setItems((current) =>
      current.map((item) =>
        item.id === itemId ? { ...item, checked: !item.checked } : item,
      ),
    );
  };

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="modal-card validation-response-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="validation-response-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-header">
          <div>
            <p className="eyebrow">Validar ticket</p>
            <h2 id="validation-response-title">Ordena y marca respuestas de la IA</h2>
            <p className="modal-copy">
              <strong>{title}</strong>
            </p>
          </div>
          <div className="modal-actions">
            <button
              type="button"
              className="secondary-button compact-button"
              onClick={onBack}
            >
              Volver
            </button>
            <button
              type="button"
              className="secondary-button compact-button"
              onClick={onClose}
            >
              Cerrar
            </button>
          </div>
        </div>

        {items.length === 0 ? (
          <p className="empty-state">
            Esta conversacion no tiene respuestas de la IA listas para validar.
          </p>
        ) : (
          <div className="validation-response-list" role="list">
            {items.map((item, index) => (
              <article key={item.id} className="validation-response-card" role="listitem">
                <div className="validation-response-top">
                  <label className="validation-response-check">
                    <input
                      type="checkbox"
                      checked={item.checked}
                      onChange={() => toggleChecked(item.id)}
                    />
                    <span className="validation-order-badge">{index + 1}</span>
                    <span>Respuesta de IA</span>
                  </label>

                  <div className="validation-order-actions">
                    <button
                      type="button"
                      className="secondary-button compact-button"
                      onClick={() => moveItem(index, -1)}
                      disabled={index === 0}
                    >
                      Subir
                    </button>
                    <button
                      type="button"
                      className="secondary-button compact-button"
                      onClick={() => moveItem(index, 1)}
                      disabled={index === items.length - 1}
                    >
                      Bajar
                    </button>
                  </div>
                </div>

                <p className="validation-response-content">{item.content}</p>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
