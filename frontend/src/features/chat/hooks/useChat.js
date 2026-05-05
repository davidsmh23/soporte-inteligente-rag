import { useEffect, useState } from "react";

import { getHealth, sendChatMessages } from "../../../services/api";

const initialMessage = {
  role: "assistant",
  content:
    "Hola. Pega aqui el ticket de soporte y revisare si ya existe una solucion previa en el vault de Obsidian.",
  isIntro: true,
};

export function useChat() {
  const [messages, setMessages] = useState([initialMessage]);
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

  const sendMessage = async (content) => {
    const userMessage = { role: "user", content };
    const optimisticMessages = [...messages, userMessage];
    setMessages(optimisticMessages);
    setIsSending(true);

    try {
      const payload = optimisticMessages
        .filter((message) => !message.isIntro)
        .map(({ role, content: messageContent }) => ({
          role,
          content: messageContent,
        }));

      const response = await sendChatMessages(payload);

      setMessages([
        ...optimisticMessages,
        {
          role: "assistant",
          content: response.response,
          sources: response.sources || [],
        },
      ]);
      setBackendStatus("online");
    } catch (error) {
      setMessages([
        ...optimisticMessages,
        {
          role: "assistant",
          content: `No se pudo procesar la solicitud: ${error.message}`,
        },
      ]);
      setBackendStatus("offline");
    } finally {
      setIsSending(false);
    }
  };

  return {
    messages,
    backendStatus,
    isCheckingHealth,
    isSending,
    sendMessage,
    refreshHealth,
    healthError,
  };
}
