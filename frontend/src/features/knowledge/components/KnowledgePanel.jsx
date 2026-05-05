import { useState } from "react";

import { StatusBadge } from "../../../components/StatusBadge";
import { indexKnowledgeBase } from "../../../services/api";

export function KnowledgePanel({
  backendStatus,
  healthError,
  isCheckingHealth,
  onRefreshHealth,
}) {
  const [indexState, setIndexState] = useState({
    status: "idle",
    message: "",
  });

  const handleIndex = async () => {
    setIndexState({ status: "loading", message: "" });

    try {
      const result = await indexKnowledgeBase();
      setIndexState({
        status: result.success ? "success" : "warning",
        message: result.message || "Indexacion completada.",
      });
    } catch (error) {
      setIndexState({
        status: "error",
        message: error.message,
      });
    }
  };

  return (
    <section className="knowledge-panel">
      <div className="panel-header">
        <p className="eyebrow">Base de conocimiento</p>
        <h2>Obsidian Vault</h2>
      </div>

      <div className="panel-block">
        <div className="status-row">
          <span>Estado del backend</span>
          <StatusBadge
            status={
              backendStatus === "online"
                ? "success"
                : backendStatus === "offline"
                  ? "error"
                  : "neutral"
            }
          >
            {isCheckingHealth
              ? "Verificando"
              : backendStatus === "online"
                ? "Disponible"
                : "Sin conexion"}
          </StatusBadge>
        </div>

        <button className="secondary-button" onClick={onRefreshHealth}>
          Reintentar conexion
        </button>

        {healthError ? <p className="panel-note error">{healthError}</p> : null}
      </div>

      <div className="panel-block">
        <div className="status-row">
          <span>Indice vectorial</span>
          <StatusBadge
            status={
              indexState.status === "success"
                ? "success"
                : indexState.status === "error"
                  ? "error"
                  : indexState.status === "warning"
                    ? "warning"
                    : "neutral"
            }
          >
            {indexState.status === "loading"
              ? "Indexando"
              : indexState.status === "success"
                ? "Actualizado"
                : indexState.status === "error"
                  ? "Error"
                  : indexState.status === "warning"
                    ? "Revision"
                    : "Pendiente"}
          </StatusBadge>
        </div>

        <button
          className="primary-button"
          onClick={handleIndex}
          disabled={indexState.status === "loading"}
        >
          {indexState.status === "loading"
            ? "Indexando vault..."
            : "Indexar Obsidian Vault"}
        </button>

        <p className="panel-note">
          Recorre los documentos del vault y actualiza la base vectorial para
          respuestas con contexto.
        </p>

        {indexState.message ? (
          <p
            className={`panel-note ${
              indexState.status === "error" ? "error" : "success"
            }`}
          >
            {indexState.message}
          </p>
        ) : null}
      </div>
    </section>
  );
}
