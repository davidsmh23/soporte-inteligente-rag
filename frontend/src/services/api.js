import { API_BASE_URL } from "../config/env";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = "La solicitud no se pudo completar.";

    try {
      const payload = await response.json();
      message = payload.detail || payload.message || message;
    } catch {
      // Keep the generic fallback when the server does not return JSON.
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export async function getHealth() {
  return request("/health", { method: "GET" });
}

export async function indexKnowledgeBase() {
  return request("/api/v1/knowledge/index", { method: "POST" });
}

export async function sendChatMessages(messages) {
  return request("/api/v1/chat/", {
    method: "POST",
    body: JSON.stringify({ messages }),
  });
}
