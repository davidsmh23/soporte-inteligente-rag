import { useEffect, useState } from "react";

import { getHealth, sendChatMessages } from "../../../services/api";

const initialMessage = {
  role: "assistant",
  content:
    "Hola. Pega aqui el ticket de soporte y revisare si ya existe una solucion previa en el vault de Obsidian.",
  isIntro: true,
};

function buildConversationTitle(content, fallbackCount) {
  const normalizedContent = content.trim();

  if (!normalizedContent) {
    return `Conversacion ${fallbackCount}`;
  }

  return normalizedContent.length > 42
    ? `${normalizedContent.slice(0, 42).trimEnd()}...`
    : normalizedContent;
}

function createConversation(count = 1) {
  return {
    id: `conversation-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    title: `Conversacion ${count}`,
    updatedAt: Date.now(),
    messages: [initialMessage],
  };
}

function moveConversationToFront(conversations, conversationId, updater) {
  const targetConversation = conversations.find(
    (conversation) => conversation.id === conversationId,
  );

  if (!targetConversation) {
    return conversations;
  }

  const updatedConversation = updater(targetConversation);
  const remainingConversations = conversations.filter(
    (conversation) => conversation.id !== conversationId,
  );

  return [updatedConversation, ...remainingConversations];
}

export function useChat() {
  const [conversations, setConversations] = useState([createConversation()]);
  const [activeConversationId, setActiveConversationId] = useState(
    () => conversations[0].id,
  );
  const [backendStatus, setBackendStatus] = useState("checking");
  const [isCheckingHealth, setIsCheckingHealth] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [healthError, setHealthError] = useState("");

  const refreshHealth = async () => {
    setIsCheckingHealth(true);
    setHealthError("");

    try {
      await getHealth();
      setBackendStatus("online");
    } catch (error) {
      setBackendStatus("offline");
      setHealthError(error.message);
    } finally {
      setIsCheckingHealth(false);
    }
  };

  useEffect(() => {
    refreshHealth();
  }, []);

  const activeConversation =
    conversations.find((conversation) => conversation.id === activeConversationId) ||
    conversations[0];

  const createNewConversation = () => {
    const nextConversation = createConversation(conversations.length + 1);
    setConversations((currentConversations) => [
      nextConversation,
      ...currentConversations,
    ]);
    setActiveConversationId(nextConversation.id);
  };

  const selectConversation = (conversationId) => {
    setActiveConversationId(conversationId);
  };

  const sendMessage = async (content) => {
    const conversationId = activeConversation.id;
    const userMessage = { role: "user", content };
    const optimisticMessages = [...activeConversation.messages, userMessage];

    setConversations((currentConversations) =>
      moveConversationToFront(currentConversations, conversationId, (conversation) => ({
        ...conversation,
        title:
          conversation.messages.filter((message) => !message.isIntro).length === 0
            ? buildConversationTitle(content, currentConversations.length)
            : conversation.title,
        updatedAt: Date.now(),
        messages: optimisticMessages,
      })),
    );
    setIsSending(true);

    try {
      const payload = optimisticMessages
        .filter((message) => !message.isIntro)
        .map(({ role, content: messageContent }) => ({
          role,
          content: messageContent,
        }));

      const response = await sendChatMessages(payload);

      setConversations((currentConversations) =>
        moveConversationToFront(currentConversations, conversationId, (conversation) => ({
          ...conversation,
          updatedAt: Date.now(),
          messages: [
            ...optimisticMessages,
            {
              role: "assistant",
              content: response.response,
              sources: response.sources || [],
            },
          ],
        })),
      );
      setBackendStatus("online");
    } catch (error) {
      setConversations((currentConversations) =>
        moveConversationToFront(currentConversations, conversationId, (conversation) => ({
          ...conversation,
          updatedAt: Date.now(),
          messages: [
            ...optimisticMessages,
            {
              role: "assistant",
              content: `No se pudo procesar la solicitud: ${error.message}`,
            },
          ],
        })),
      );
      setBackendStatus("offline");
    } finally {
      setIsSending(false);
    }
  };

  return {
    conversations,
    activeConversationId,
    messages: activeConversation.messages,
    backendStatus,
    isCheckingHealth,
    isSending,
    sendMessage,
    refreshHealth,
    healthError,
    createNewConversation,
    selectConversation,
  };
}
