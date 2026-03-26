import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useNavigation } from '../../context/NavigationAgent';
import ChatPanel from './ChatPanel';
import { streamChat } from '../../services/chatService';

/**
 * ChatWidget
 *
 * Floating chat bubble that opens the CarePath AI chat panel.
 * Streams responses token-by-token from POST /api/chat/stream so the
 * user sees words appearing in real time instead of waiting for the
 * full response.
 */
const ChatWidget = () => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId] = useState(() => `session-${Date.now()}`);

  const { navigateToResults, navigateToHome, highlightHospital, clearHighlight } = useNavigation();

  // ---------------------------------------------------------------------------
  // Send message — uses SSE streaming
  // ---------------------------------------------------------------------------
  const handleSendMessage = async () => {
    const text = message.trim();
    if (!text || isStreaming) return;

    setMessage('');

    // Append user bubble immediately
    setMessages(prev => [...prev, { type: 'user', text, timestamp: new Date() }]);
    setIsStreaming(true);

    // Insert a blank bot bubble that we'll fill token-by-token
    const botId = `bot-${Date.now()}`;
    setMessages(prev => [
      ...prev,
      { id: botId, type: 'bot', text: '', streaming: true, timestamp: new Date() },
    ]);

    try {
      await streamChat({
        sessionId,
        message: text,
        onToken: (token) => {
          setMessages(prev =>
            prev.map(m =>
              m.id === botId ? { ...m, text: m.text + token } : m,
            ),
          );
        },
        onDone: () => {
          // Mark streaming finished so cursor disappears
          setMessages(prev =>
            prev.map(m => (m.id === botId ? { ...m, streaming: false } : m)),
          );
          setIsStreaming(false);
        },
        onError: (err) => {
          console.error('Chat stream error:', err);
          setMessages(prev =>
            prev.map(m =>
              m.id === botId
                ? {
                    ...m,
                    text: 'Sorry, I encountered an issue. Please try again.',
                    streaming: false,
                  }
                : m,
            ),
          );
          setIsStreaming(false);
        },
      });
    } catch (err) {
      console.error('Unexpected chat error:', err);
      setIsStreaming(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Navigation actions dispatched from the chat panel
  // ---------------------------------------------------------------------------
  const handleNavigationAction = (action, data) => {
    switch (action) {
      case 'navigate_to_results':
        navigateToResults(data);
        break;
      case 'navigate_to_home':
        navigateToHome();
        break;
      case 'highlight_hospital':
        highlightHospital(data);
        break;
      case 'clear_highlight':
        clearHighlight();
        break;
      case 'navigate_to_hospital_detail':
        if (data?.hospital_id) navigate(`/hospital/${data.hospital_id}`);
        break;
      default:
        break;
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* Floating action button */}
      <button
        onClick={() => setIsOpen(prev => !prev)}
        aria-label={isOpen ? 'Close chat' : 'Open CarePath AI chat'}
        className="bg-blue-600 text-white px-4 py-3 rounded-full shadow-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
      >
        {isStreaming ? (
          <>
            <span className="flex space-x-1">
              <span className="h-2 w-2 bg-white rounded-full animate-bounce [animation-delay:0ms]" />
              <span className="h-2 w-2 bg-white rounded-full animate-bounce [animation-delay:150ms]" />
              <span className="h-2 w-2 bg-white rounded-full animate-bounce [animation-delay:300ms]" />
            </span>
            <span className="text-sm font-medium">Thinking…</span>
          </>
        ) : (
          <>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.502 8-10 8S2 16.418 2 12c0-4.418 4.493-8 10-8s10 3.582 10 8z"
              />
            </svg>
            <span className="text-sm font-medium">CarePath AI</span>
          </>
        )}
      </button>

      {/* Chat panel */}
      {isOpen && (
        <ChatPanel
          messages={messages}
          onSendMessage={handleSendMessage}
          onMessageChange={setMessage}
          message={message}
          onKeyPress={handleKeyPress}
          onNavigationAction={handleNavigationAction}
          onClose={() => setIsOpen(false)}
          isStreaming={isStreaming}
        />
      )}
    </div>
  );
};

export default ChatWidget;
