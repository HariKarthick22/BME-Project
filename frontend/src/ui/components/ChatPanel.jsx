import React, { useState, useEffect, useRef } from 'react';

/**
 * ChatPanel Component
 * 
 * Displays a chat interface for the MediOrbit medical assistant.
 * Shows conversation history, handles message input, and displays
 * bot typing indicators.
 * 
 * Props:
 *   - messages: Array of message objects {type, text, timestamp}
 *   - onSendMessage: Callback when user sends a message
 *   - onMessageChange: Callback when message input changes
 *   - message: Current message input value
 *   - onKeyPress: Callback for keyboard events
 *   - onNavigationAction: Callback for navigation actions
 *   - onClose: Callback when panel is closed
 *   - typing: Boolean indicating if bot is typing
 */
const ChatPanel = ({ messages, onSendMessage, onMessageChange, message, onKeyPress, onNavigationAction, onClose, typing }) => {
  const messagesEndRef = useRef(null);
  const [isTyping, setIsTyping] = useState(false);

  // Scroll to bottom when messages update
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Handle bot typing indicator
  useEffect(() => {
    if (typing) {
      setIsTyping(true);
      const timer = setTimeout(() => {
        setIsTyping(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [typing]);

  // Handle navigation actions from bot messages
  const handleBotAction = (action, data) => {
    onNavigationAction(action, data);
  };

  // Render message bubbles
  const renderMessage = (msg, index) => {
    const isUser = msg.type === 'user';
    const isBot = msg.type === 'bot';

    return (
      <div
        key={index}
        className={`mb-3 flex ${isUser ? 'justify-end' : 'justify-start'}`}
      >
        <div
          className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
            isUser 
              ? 'bg-blue-600 text-white rounded-br-none' 
              : 'bg-gray-200 text-gray-800 rounded-bl-none'
          }`}
        >
          <p className="text-sm">{msg.text}</p>
          <span className={`text-xs ${isUser ? 'text-blue-100' : 'text-gray-600'} mt-1 block`}>
            {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="fixed bottom-20 right-4 z-50 w-96 max-w-sm lg:max-w-md">
      <div className="bg-white rounded-t-lg border border-gray-200 shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-white">
          <h3 className="font-semibold text-gray-900">MediOrbit Assistant</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Messages */}
        <div className="p-4 max-h-96 overflow-y-auto bg-gray-50 flex flex-col">
          <div className="flex flex-col space-y-2">
            {/* Initial greeting */}
            {!messages.length && (
              <div className="self-start">
                <div className="flex flex-col space-y-1">
                  <span className="text-xs text-gray-500">Just now</span>
                  <div className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg">
                    Hi! I'm MediOrbit, your medical travel assistant. How can I help you today?
                  </div>
                </div>
              </div>
            )}

            {/* User and bot messages */}
            {messages.map((msg, index) => renderMessage(msg, index))}

            {/* Typing indicator */}
            {isTyping && (
              <div className="self-start">
                <div className="flex flex-col space-y-1">
                  <span className="text-xs text-gray-500">Typing...</span>
                  <div className="flex space-x-1">
                    <div className="h-3 w-3 bg-gray-200 rounded-full animate-bounce"></div>
                    <div className="h-3 w-3 bg-gray-200 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="h-3 w-3 bg-gray-200 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            )}

            {/* Scroll to bottom reference */}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex space-x-2">
            <input
              type="text"
              value={message}
              onChange={(e) => onMessageChange(e.target.value)}
              onKeyPress={onKeyPress}
              placeholder="Type a message..."
              className="flex-1 px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={onSendMessage}
              disabled={!message.trim()}
              className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;
