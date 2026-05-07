import { ChatShell } from "./features/chat/components/ChatShell";
import { ConversationSidebar } from "./features/chat/components/ConversationSidebar";
import { KnowledgePanel } from "./features/knowledge/components/KnowledgePanel";
import { useChat } from "./features/chat/hooks/useChat";
import { useTheme } from "./hooks/useTheme";

function App() {
  const { theme, toggleTheme } = useTheme();
  const {
    conversations,
    activeConversationId,
    messages,
    backendStatus,
    isCheckingHealth,
    isSending,
    sendMessage,
    refreshHealth,
    healthError,
    createNewConversation,
    selectConversation,
  } = useChat();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <ConversationSidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={selectConversation}
          onCreateConversation={createNewConversation}
          theme={theme}
          onToggleTheme={toggleTheme}
        />
      </aside>

      <main className="main-panel">
        <KnowledgePanel
          backendStatus={backendStatus}
          healthError={healthError}
          isCheckingHealth={isCheckingHealth}
          onRefreshHealth={refreshHealth}
        />
        <ChatShell
          messages={messages}
          backendStatus={backendStatus}
          isSending={isSending}
          onSendMessage={sendMessage}
        />
      </main>
    </div>
  );
}

export default App;
