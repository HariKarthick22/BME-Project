import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useNavigation } from '../../context/NavigationAgent';
import ChatPanel from './ChatPanel';

/**
 * ChatWidget Component
 * 
 * Floating chat bubble that opens a chat panel for interacting with
 * the MediOrbit AI medical assistant. Integrates with the backend API
 * to send messages and receive responses with hospital recommendations
 * and navigation actions.
 */
const ChatWidget = () => {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [typing, setTyping] = useState(false);
  const [sessionId] = useState(() => `session-${Date.now()}`);
  const { navigateToResults, navigateToHome, highlightHospital, clearHighlight } = useNavigation();

  /**
   * Send message to backend and get AI response
   */
  const handleSendMessage = async () => {
    if (!message.trim()) return;

    const userMessage = message;
    setMessage('');

    // Add user message to chat
    setMessages(prev => [...prev, { 
      type: 'user', 
      text: userMessage, 
      timestamp: new Date() 
    }]);
    setTyping(true);

    try {
      // Send to backend API
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: userMessage,
          prescription_data: null
        })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Add bot response to chat
      setMessages(prev => [...prev, {
        type: 'bot',
        text: data.text,
        timestamp: new Date()
      }]);

      // Process UI actions from response
      if (data.actions && Array.isArray(data.actions)) {
        processActions(data.actions);
      }

      // If hospitals were matched, might want to navigate
      if (data.hospitals && data.hospitals.length > 0) {
        // Store hospitals in session/context for results page
        sessionStorage.setItem('lastSearchResults', JSON.stringify(data.hospitals));
      }

    } catch (error) {
      console.error('Chat API error:', error);
      setMessages(prev => [...prev, {
        type: 'bot',
        text: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      }]);
    } finally {
      setTyping(false);
    }
  };

  /**
   * Process UI actions returned from the backend
   */
  const processActions = (actions) => {
    actions.forEach(action => {
      switch (action.action_type) {
        case 'navigate_to_results':
          // Small delay to show message before navigation
          setTimeout(() => navigateToResults(action.data?.query || ''), 500);
          break;
        case 'navigate_to_hospital_detail':
          if (action.data?.hospital_id) {
            setTimeout(() => navigate(`/hospital/${action.data.hospital_id}`), 500);
          }
          break;
        case 'highlight_hospital':
          if (action.data?.hospital) {
            highlightHospital(action.data.hospital);
          }
          break;
        case 'clear_highlight':
          clearHighlight();
          break;
        default:
          console.log('Unknown action:', action.action_type);
      }
    });
  };

  // Handle keyboard enter key
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Handle navigation actions from chat panel
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
      default:
        console.log('Unknown action:', action);
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* Chat widget button */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className="bg-blue-600 text-white p-3 rounded-full shadow-lg cursor-pointer hover:bg-blue-700 transition-colors"
      >
        {typing ? (
          <div className="flex items-center space-x-2">
            <div className="animate-pulse h-3 w-3 bg-white rounded-full"></div>
            <span>Typing...</span>
          </div>
        ) : (
          <div className="flex items-center space-x-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.502 8-10 8S2 16.418 2 12c0-4.418 4.493-8 10-8s10 3.582 10 8z" />
            </svg>
            <span>Chat</span>
          </div>
        )}
      </div>

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
          typing={typing}
        />
      )}
    </div>
  );
};

export default ChatWidget;
