import {
  BACKEND_BASE_URL,
  DEFAULT_USER_ID,
  DEFAULT_USER_TOKEN,
  GATEWAY_BASE_URL,
} from "../config/env";
import { streamJsonEvents } from "./sse";

function buildUrl(baseUrl, path) {
  if (!baseUrl) {
    return path;
  }

  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

async function parseError(response) {
  let message = "La solicitud no se pudo completar.";

  try {
    const payload = await response.json();
    message = payload.detail || payload.message || message;
  } catch {
    try {
      const text = await response.text();
      if (text.trim()) {
        message = text.trim();
      }
    } catch {
      // Keep fallback message.
    }
  }

  throw new Error(message);
}

async function request(path, options = {}, config = {}) {
  const {
    baseUrl = "",
    token,
    includeJsonContentType = true,
  } = config;

  const headers = {
    ...(includeJsonContentType ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const response = await fetch(buildUrl(baseUrl, path), {
    ...options,
    headers,
  });

  if (!response.ok) {
    await parseError(response);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export { DEFAULT_USER_ID, DEFAULT_USER_TOKEN };

export async function getBackendHealth() {
  return request("/health", { method: "GET" }, { baseUrl: BACKEND_BASE_URL });
}

export async function indexKnowledgeBase() {
  return request(
    "/api/v1/knowledge/index",
    { method: "POST" },
    { baseUrl: BACKEND_BASE_URL },
  );
}

export async function getAgentStatus({ userId, userToken }) {
  return request(
    `/api/v1/agents/${encodeURIComponent(userId)}/status`,
    { method: "GET" },
    { baseUrl: GATEWAY_BASE_URL, token: userToken },
  );
}

export async function createConversation({ userId, title, userToken }) {
  return request(
    "/api/v1/conversations",
    {
      method: "POST",
      body: JSON.stringify({ user_id: userId, title }),
    },
    { baseUrl: GATEWAY_BASE_URL, token: userToken },
  );
}

export async function listConversations({ userId, userToken }) {
  const search = new URLSearchParams({ user_id: userId });
  return request(
    `/api/v1/conversations?${search.toString()}`,
    { method: "GET" },
    { baseUrl: GATEWAY_BASE_URL, token: userToken },
  );
}

export async function getConversation({ conversationRef, userId, userToken }) {
  const search = new URLSearchParams({ user_id: userId });
  return request(
    `/api/v1/conversations/${encodeURIComponent(conversationRef)}?${search.toString()}`,
    { method: "GET" },
    { baseUrl: GATEWAY_BASE_URL, token: userToken },
  );
}

export async function streamPrompt({
  userId,
  userToken,
  payload,
  onEvent,
  signal,
}) {
  const response = await fetch(buildUrl(GATEWAY_BASE_URL, "/api/v1/session/prompt"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${userToken}`,
    },
    body: JSON.stringify({
      user_id: userId,
      ...payload,
    }),
    signal,
  });

  if (!response.ok) {
    await parseError(response);
  }

  await streamJsonEvents(response, onEvent);
}
