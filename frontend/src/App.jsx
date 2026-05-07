import { ChatShell } from "./features/chat/components/ChatShell";
import { ConversationSidebar } from "./features/chat/components/ConversationSidebar";
import { KnowledgePanel } from "./features/knowledge/components/KnowledgePanel";
import { useChat } from "./features/chat/hooks/useChat";
import { useTheme } from "./hooks/useTheme";

function App() {
  const { theme, toggleTheme } = useTheme();
  const {
    userId,
    setUserId,
    userToken,
    setUserToken,
    conversations,
    activeConversation,
    activeConversationId,
    messages,
    traces,
    latestReferences,
    currentMode,
    modeLabel,
    backendStatus,
    agentStatus,
    isCheckingHealth,
    isSending,
    isLoadingConversations,
    sendMessage,
    refreshHealth,
    refreshAgent,
    healthError,
    uiError,
    createNewConversation,
    selectConversation,
  } = useChat();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <ConversationSidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          activeConversation={activeConversation}
          userId={userId}
          userToken={userToken}
          onUserIdChange={setUserId}
          onUserTokenChange={setUserToken}
          onSelectConversation={selectConversation}
          onCreateConversation={createNewConversation}
          isLoadingConversations={isLoadingConversations}
          agentStatus={agentStatus}
          theme={theme}
          onToggleTheme={toggleTheme}
        />
      </aside>

      <main className="main-panel">
        <KnowledgePanel
          backendStatus={backendStatus}
          agentStatus={agentStatus}
          healthError={healthError}
          uiError={uiError}
          isCheckingHealth={isCheckingHealth}
          onRefreshHealth={refreshHealth}
          onRefreshAgent={() => refreshAgent()}
        />
        <ChatShell
          messages={messages}
          traces={traces}
          references={latestReferences}
          backendStatus={backendStatus}
          activeConversation={activeConversation}
          currentMode={currentMode}
          modeLabel={modeLabel}
          isSending={isSending}
          uiError={uiError}
          onSendMessage={sendMessage}
        />
      </main>
    </div>
  );
}

export default App;
