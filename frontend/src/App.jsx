import { ThemeToggle } from "./components/ThemeToggle";
import { ChatShell } from "./features/chat/components/ChatShell";
import { KnowledgePanel } from "./features/knowledge/components/KnowledgePanel";
import { useChat } from "./features/chat/hooks/useChat";
import { useTheme } from "./hooks/useTheme";

function App() {
  const { theme, toggleTheme } = useTheme();
  const {
    messages,
    backendStatus,
    isCheckingHealth,
    isSending,
    sendMessage,
    refreshHealth,
    healthError,
  } = useChat();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <ThemeToggle theme={theme} onToggle={toggleTheme} />
        <KnowledgePanel
          backendStatus={backendStatus}
          healthError={healthError}
          isCheckingHealth={isCheckingHealth}
          onRefreshHealth={refreshHealth}
        />
      </aside>

      <main className="main-panel">
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
