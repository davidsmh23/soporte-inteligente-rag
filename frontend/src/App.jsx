import { useState } from "react";

import { ChatShell } from "./features/chat/components/ChatShell";
import { ConversationSidebar } from "./features/chat/components/ConversationSidebar";
import { LoginPage } from "./features/chat/components/LoginPage";
import { ValidationResponseModal } from "./features/chat/components/ValidationResponseModal";
import { ValidationTicketModal } from "./features/chat/components/ValidationTicketModal";
import { useChat } from "./features/chat/hooks/useChat";
import { useTheme } from "./hooks/useTheme";

function App() {
  const { theme, toggleTheme } = useTheme();
  const [isValidationModalOpen, setIsValidationModalOpen] = useState(false);
  const [isValidationResponseModalOpen, setIsValidationResponseModalOpen] = useState(false);
  const [validationConversationId, setValidationConversationId] = useState(null);
  const [validationMessages, setValidationMessages] = useState([]);
  const {
    loginUserId,
    setLoginUserId,
    loginUserToken,
    setLoginUserToken,
    login,
    isAuthenticated,
    isAuthenticating,
    userId,
    conversations,
    activeConversation,
    activeConversationId,
    messages,
    traces,
    latestReferences,
    currentMode,
    modeLabel,
    isSending,
    isLoadingConversations,
    sendMessage,
    uiError,
    createNewConversation,
    selectConversation,
    getConversationMessages,
  } = useChat();

  const validationConversation =
    conversations.find((conversation) => conversation.conversation_id === validationConversationId) ||
    null;

  const handleValidationConversationSelect = async (conversationId) => {
    const selectedMessages = await selectConversation(conversationId);
    const conversationMessages =
      selectedMessages?.length ? selectedMessages : await getConversationMessages(conversationId);
    setValidationConversationId(conversationId);
    setValidationMessages(conversationMessages);
    setIsValidationModalOpen(false);
    setIsValidationResponseModalOpen(true);
  };

  const handleCloseValidationFlow = () => {
    setIsValidationModalOpen(false);
    setIsValidationResponseModalOpen(false);
    setValidationConversationId(null);
    setValidationMessages([]);
  };

  const handleBackToConversationSelector = () => {
    setIsValidationResponseModalOpen(false);
    setIsValidationModalOpen(true);
  };

  if (!isAuthenticated) {
    return (
      <LoginPage
        userId={loginUserId}
        userToken={loginUserToken}
        onUserIdChange={setLoginUserId}
        onUserTokenChange={setLoginUserToken}
        onSubmit={login}
        isSubmitting={isAuthenticating}
        errorMessage={uiError}
        theme={theme}
        onToggleTheme={toggleTheme}
      />
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <ConversationSidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          activeConversation={activeConversation}
          userId={userId}
          onSelectConversation={selectConversation}
          onOpenValidationSelector={() => setIsValidationModalOpen(true)}
          onCreateConversation={createNewConversation}
          isLoadingConversations={isLoadingConversations}
          errorMessage={uiError}
          theme={theme}
          onToggleTheme={toggleTheme}
        />
      </aside>

      <main className="main-panel">
        <ChatShell
          messages={messages}
          traces={traces}
          references={latestReferences}
          activeConversation={activeConversation}
          currentMode={currentMode}
          modeLabel={modeLabel}
          isSending={isSending}
          uiError={uiError}
          onSendMessage={sendMessage}
        />
      </main>

      <ValidationTicketModal
        conversations={conversations}
        activeConversationId={activeConversationId}
        isOpen={isValidationModalOpen}
        onClose={handleCloseValidationFlow}
        onSelectConversation={handleValidationConversationSelect}
      />

      <ValidationResponseModal
        isOpen={isValidationResponseModalOpen}
        conversation={validationConversation}
        messages={validationMessages}
        onClose={handleCloseValidationFlow}
        onBack={handleBackToConversationSelector}
      />
    </div>
  );
}

export default App;
