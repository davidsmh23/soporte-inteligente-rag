import { useState } from "react";

export function ChatComposer({ disabled, onSubmit }) {
  const [value, setValue] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmedValue = value.trim();

    if (!trimmedValue || disabled) {
      return;
    }

    setValue("");
    await onSubmit(trimmedValue);
  };

  return (
    <form className="composer" onSubmit={handleSubmit}>
      <label className="composer-label" htmlFor="ticket-input">
        Describe el ticket o pega el caso completo
      </label>
      <textarea
        id="ticket-input"
        className="composer-input"
        placeholder="Ejemplo: El usuario no puede acceder por VPN desde macOS y recibe error de autenticacion."
        rows="4"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        disabled={disabled}
      />
      <div className="composer-actions">
        <p className="composer-hint">
          El historial se envía completo para mantener contexto.
        </p>
        <button className="primary-button" type="submit" disabled={disabled}>
          {disabled ? "Analizando..." : "Enviar"}
        </button>
      </div>
    </form>
  );
}
