import { useEffect, useMemo, useState } from "react";

import {
  DEFAULT_USER_ID,
  DEFAULT_USER_TOKEN,
  createConversation,
  getAgentStatus,
  getBackendHealth,
  getConversation,
  listConversations,
  streamPrompt,
} from "../../../services/api";

const MODE_LABELS = {
  triage_inicial: "Triage inicial",
  chat_generico: "Chat generico",
  resuelto_por_referencia: "Resuelto por referencia",
};

function createId(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

function createWelcomeMessage() {
  return {
    id: createId("welcome"),
    role: "assistant",
    content:
      "Hola. Crea o selecciona una conversacion. Todos los mensajes de esta conversacion iran al mismo hilo real de Codex.",
    references: [],
    tokenUsage: null,
    isIntro: true,
  };
}

function normalizeMessage(message, index = 0) {
  return {
    id: message.id || createId(`message-${index}`),
    role: message.role || "assistant",
    content: message.content || "",
    references: Array.isArray(message.references) ? message.references : [],
    tokenUsage: message.token_usage || message.tokenUsage || null,
    createdAt: message.created_at || message.createdAt || null,
    isIntro: Boolean(message.isIntro),
    isStreaming: Boolean(message.isStreaming),
  };
}

function ensureMessages(messages) {
  if (!Array.isArray(messages) || messages.length === 0) {
    return [createWelcomeMessage()];
  }

  return messages.map(normalizeMessage);
}

function getErrorMessage(error) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Se produjo un error no controlado.";
}

function formatTraceDetail(event) {
  if (event.type === "mode_update") {
    return `[mode_update] ${MODE_LABELS[event.mode] || event.mode}`;
  }

  if (event.type === "conversation_bound") {
    return `[conversation_bound] ${event.codex_session_id}`;
  }

  if (event.type === "prompt_submitted") {
    return `[prompt_submitted] ${event.conversation_id}`;
  }

  if (event.type === "error") {
    return `[error] ${event.message || "Error desconocido."}`;
  }

  return event.detail || event.message || event.type;
}

function createTrace(event) {
  return {
    id: createId("trace"),
    createdAt: new Date().toISOString(),
    type: event.type,
    detail: formatTraceDetail(event),
  };
}

function deriveConversationTitle(conversation, fallbackIndex) {
  const title = (conversation?.title || "").trim();
  if (title) {
    return title;
  }

  return `Conversacion ${fallbackIndex}`;
}

function getConversationPreview(messages) {
  const lastMessage = [...messages]
    .reverse()
    .find((message) => !message.isIntro);

  return lastMessage?.content || "Sin actividad todavia";
}

export function useChat() {
  const [userId, setUserId] = useState(DEFAULT_USER_ID);
  const [userToken, setUserToken] = useState(DEFAULT_USER_TOKEN);
  const [conversations, setConversations] = useState([]);
  const [messagesByConversation, setMessagesByConversation] = useState({});
  const [chatModeByConversation, setChatModeByConversation] = useState({});
  const [tracesByConversation, setTracesByConversation] = useState({});
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [backendStatus, setBackendStatus] = useState("checking");
  const [agentStatus, setAgentStatus] = useState(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [isLoadingConversations, setIsLoadingConversations] = useState(true);
  const [healthError, setHealthError] = useState("");
  const [uiError, setUiError] = useState("");

  const syncConversationState = (detail) => {
    const conversationId = detail.conversation_id;
    const normalizedMessages = ensureMessages(detail.messages);

    setMessagesByConversation((current) => ({
      ...current,
      [conversationId]: normalizedMessages,
    }));

    if (detail.codex_session_id) {
      setConversations((current) =>
        current.map((conversation) =>
          conversation.conversation_id === conversationId
            ? { ...conversation, codex_session_id: detail.codex_session_id }
            : conversation,
        ),
      );
    }
  };

  const refreshHealth = async () => {
    setIsCheckingHealth(true);
    setHealthError("");

    try {
      await getBackendHealth();
      setBackendStatus("online");
    } catch (error) {
      setBackendStatus("offline");
      setHealthError(getErrorMessage(error));
    } finally {
      setIsCheckingHealth(false);
    }
  };

  const refreshAgent = async (currentUserId = userId, currentUserToken = userToken) => {
    try {
      const status = await getAgentStatus({
        userId: currentUserId,
        userToken: currentUserToken,
      });
      setAgentStatus(status);
    } catch (error) {
      setAgentStatus(null);
      setUiError(getErrorMessage(error));
    }
  };

  const refreshConversations = async ({
    currentUserId = userId,
    currentUserToken = userToken,
    preserveActive = true,
  } = {}) => {
    setIsLoadingConversations(true);
    setUiError("");

    try {
      const payload = await listConversations({
        userId: currentUserId,
        userToken: currentUserToken,
      });
      const items = Array.isArray(payload.conversations) ? payload.conversations : [];
      setConversations(items);

      if (!items.length) {
        const created = await createConversation({
          userId: currentUserId,
          userToken: currentUserToken,
          title: "Nueva conversacion",
        });
        const seedMessages = [createWelcomeMessage()];
        setConversations([created]);
        setMessagesByConversation((current) => ({
          ...current,
          [created.conversation_id]: seedMessages,
        }));
        setActiveConversationId(created.conversation_id);
        return created.conversation_id;
      }

      const nextActiveConversationId =
        preserveActive &&
        items.some((conversation) => conversation.conversation_id === activeConversationId)
          ? activeConversationId
          : items[0].conversation_id;

      setActiveConversationId(nextActiveConversationId);
      return nextActiveConversationId;
    } catch (error) {
      setConversations([]);
      setUiError(getErrorMessage(error));
      return null;
    } finally {
      setIsLoadingConversations(false);
    }
  };

  const loadConversationDetail = async (
    conversationRef,
    currentUserId = userId,
    currentUserToken = userToken,
  ) => {
    try {
      const detail = await getConversation({
        conversationRef,
        userId: currentUserId,
        userToken: currentUserToken,
      });
      syncConversationState(detail);
      setActiveConversationId(detail.conversation_id);
      return detail;
    } catch (error) {
      setUiError(getErrorMessage(error));
      return null;
    }
  };

  useEffect(() => {
    let active = true;

    const bootstrap = async () => {
      setUiError("");
      await refreshHealth();
      if (!active) {
        return;
      }

      await refreshAgent(userId, userToken);
      if (!active) {
        return;
      }

      const conversationId = await refreshConversations({
        currentUserId: userId,
        currentUserToken: userToken,
        preserveActive: false,
      });

      if (!active || !conversationId) {
        return;
      }

      await loadConversationDetail(conversationId, userId, userToken);
    };

    bootstrap();

    const interval = window.setInterval(() => {
      refreshHealth();
      refreshAgent(userId, userToken);
    }, 15000);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [userId, userToken]);

  const activeConversation = useMemo(
    () =>
      conversations.find(
        (conversation) => conversation.conversation_id === activeConversationId,
      ) || conversations[0] || null,
    [conversations, activeConversationId],
  );

  const messages = useMemo(() => {
    if (!activeConversation) {
      return [createWelcomeMessage()];
    }

    return ensureMessages(messagesByConversation[activeConversation.conversation_id]);
  }, [activeConversation, messagesByConversation]);

  const currentMode =
    (activeConversation &&
      chatModeByConversation[activeConversation.conversation_id]) ||
    "chat_generico";

  const traces =
    (activeConversation &&
      tracesByConversation[activeConversation.conversation_id]) ||
    [];

  const latestReferences = [...messages]
    .reverse()
    .find((message) => Array.isArray(message.references) && message.references.length > 0)
    ?.references || [];

  const createNewConversation = async () => {
    setUiError("");

    try {
      const created = await createConversation({
        userId,
        userToken,
        title: "Nueva conversacion",
      });

      setConversations((current) => [created, ...current]);
      setMessagesByConversation((current) => ({
        ...current,
        [created.conversation_id]: [createWelcomeMessage()],
      }));
      setActiveConversationId(created.conversation_id);
    } catch (error) {
      setUiError(getErrorMessage(error));
    }
  };

  const selectConversation = async (conversationId) => {
    setActiveConversationId(conversationId);

    if (!messagesByConversation[conversationId]) {
      await loadConversationDetail(conversationId);
    }
  };

  const appendTrace = (conversationId, event) => {
    setTracesByConversation((current) => ({
      ...current,
      [conversationId]: [...(current[conversationId] || []), createTrace(event)].slice(-50),
    }));
  };

  const sendMessage = async (content) => {
    if (!activeConversation || isSending) {
      return;
    }

    const conversationId = activeConversation.conversation_id;
    const existingMessages = ensureMessages(messagesByConversation[conversationId]);
    const userMessage = normalizeMessage({
      id: createId("user"),
      role: "user",
      content,
      references: [],
      tokenUsage: null,
    });
    const assistantMessageId = createId("assistant");
    const assistantPlaceholder = normalizeMessage({
      id: assistantMessageId,
      role: "assistant",
      content: "",
      references: [],
      tokenUsage: null,
      isStreaming: true,
    });
    const optimisticMessages = [...existingMessages, userMessage, assistantPlaceholder];

    setUiError("");
    setIsSending(true);
    setMessagesByConversation((current) => ({
      ...current,
      [conversationId]: optimisticMessages,
    }));
    setConversations((current) =>
      current.map((conversation, index) =>
        conversation.conversation_id === conversationId
          ? {
              ...conversation,
              title: deriveConversationTitle(conversation, index + 1),
              last_message_at: new Date().toISOString(),
            }
          : conversation,
      ),
    );

    try {
      await streamPrompt({
        userId,
        userToken,
        payload: {
          conversation_id: conversationId,
          codex_session_id: activeConversation.codex_session_id || null,
          session_id: conversationId,
          prompt: content,
          history: [...existingMessages, userMessage].map((message) => ({
            role: message.role,
            content: message.content,
          })),
        },
        onEvent: (event) => {
          if (event.type === "token_delta") {
            setMessagesByConversation((current) => ({
              ...current,
              [conversationId]: (current[conversationId] || []).map((message) =>
                message.id === assistantMessageId
                  ? {
                      ...message,
                      content: `${message.content || ""}${event.delta || ""}`,
                    }
                  : message,
              ),
            }));
            return;
          }

          if (event.type === "tool_trace" || event.type === "prompt_submitted") {
            appendTrace(conversationId, event);
            return;
          }

          if (event.type === "mode_update") {
            setChatModeByConversation((current) => ({
              ...current,
              [conversationId]: event.mode || "chat_generico",
            }));
            appendTrace(conversationId, event);
            return;
          }

          if (event.type === "conversation_bound") {
            setConversations((current) =>
              current.map((conversation) =>
                conversation.conversation_id === conversationId
                  ? {
                      ...conversation,
                      codex_session_id:
                        event.codex_session_id || conversation.codex_session_id,
                      status: "active",
                    }
                  : conversation,
              ),
            );
            appendTrace(conversationId, event);
            return;
          }

          if (event.type === "final_answer") {
            setMessagesByConversation((current) => ({
              ...current,
              [conversationId]: (current[conversationId] || []).map((message) =>
                message.id === assistantMessageId
                  ? {
                      ...message,
                      content: event.answer || message.content || "No se recibio contenido de Codex.",
                      references: Array.isArray(event.references) ? event.references : [],
                      tokenUsage: event.token_usage || null,
                      isStreaming: false,
                    }
                  : message,
              ),
            }));

            if (event.codex_session_id) {
              setConversations((current) =>
                current.map((conversation) =>
                  conversation.conversation_id === conversationId
                    ? {
                        ...conversation,
                        codex_session_id: event.codex_session_id,
                        status: "active",
                      }
                    : conversation,
                ),
              );
            }
            return;
          }

          if (event.type === "error") {
            appendTrace(conversationId, event);
            throw new Error(event.message || "Error desconocido del gateway.");
          }
        },
      });

      await refreshConversations();
    } catch (error) {
      const message = getErrorMessage(error);
      setUiError(message);
      setMessagesByConversation((current) => ({
        ...current,
        [conversationId]: (current[conversationId] || []).map((item) =>
          item.id === assistantMessageId
            ? {
                ...item,
                content: item.content || `No se pudo procesar la solicitud: ${message}`,
                isStreaming: false,
              }
            : item,
        ),
      }));
    } finally {
      setIsSending(false);
    }
  };

  return {
    userId,
    setUserId,
    userToken,
    setUserToken,
    conversations: conversations.map((conversation, index) => ({
      ...conversation,
      title: deriveConversationTitle(conversation, index + 1),
      preview: getConversationPreview(
        ensureMessages(messagesByConversation[conversation.conversation_id]),
      ),
    })),
    activeConversation,
    activeConversationId,
    messages,
    traces,
    latestReferences,
    currentMode,
    modeLabel: MODE_LABELS[currentMode] || currentMode,
    backendStatus,
    agentStatus,
    isCheckingHealth,
    isSending,
    isLoadingConversations,
    sendMessage,
    refreshHealth,
    refreshAgent,
    refreshConversations,
    healthError,
    uiError,
    createNewConversation,
    selectConversation,
  };
}
