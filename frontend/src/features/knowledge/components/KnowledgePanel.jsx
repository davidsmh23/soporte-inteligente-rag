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
    <section className="knowledge-toolbar">
      <div className="knowledge-toolbar-section">
        <span className="toolbar-label">Backend</span>
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
        <button
          className="secondary-button compact-button"
          onClick={onRefreshHealth}
        >
          Reintentar conexion
        </button>
      </div>

      <div className="knowledge-toolbar-section">
        <span className="toolbar-label">Vault</span>
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
        <button
          className="primary-button compact-button"
          onClick={handleIndex}
          disabled={indexState.status === "loading"}
        >
          {indexState.status === "loading" ? "Indexando..." : "Indexar vault"}
        </button>
      </div>

      {healthError ? <p className="toolbar-note error">{healthError}</p> : null}
      {indexState.message ? (
        <p
          className={`toolbar-note ${
            indexState.status === "error" ? "error" : "success"
          }`}
        >
          {indexState.message}
        </p>
      ) : null}
    </section>
  );
}
