import React, { useEffect, useRef } from 'react';

/**
 * ChatPanel
 *
 * Displays the CarePath AI conversation. Bot messages support a `streaming`
 * flag that shows a blinking cursor while tokens are arriving from the SSE
 * stream, giving the user immediate visual feedback.
 *
 * Props:
 *   messages          {Array}    — [{id, type, text, streaming, timestamp}]
 *   onSendMessage     {Function} — called when the user submits
 *   onMessageChange   {Function} — called with the new input string
 *   message           {string}   — controlled input value
 *   onKeyPress        {Function} — keyboard handler (Enter to send)
 *   onNavigationAction{Function} — (action, data) => void
 *   onClose           {Function} — closes the panel
 *   isStreaming       {boolean}  — true while any SSE stream is open
 */
const ChatPanel = ({
  messages,
  onSendMessage,
  onMessageChange,
  message,
  onKeyPress,
  onNavigationAction,
  onClose,
  isStreaming,
}) => {
  const messagesEndRef = useRef(null);

  // Keep the last message in view as tokens stream in
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ---------------------------------------------------------------------------
  // Message bubble renderer
  // ---------------------------------------------------------------------------
  const renderMessage = (msg, index) => {
    const isUser = msg.type === 'user';

    return (
      <div
        key={msg.id ?? index}
        className={`mb-3 flex ${isUser ? 'justify-end' : 'justify-start'}`}
      >
        <div
          className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg text-sm leading-relaxed ${
            isUser
              ? 'bg-blue-600 text-white rounded-br-none'
              : 'bg-gray-100 text-gray-800 rounded-bl-none'
          }`}
        >
          {/* Message text — whitespace-pre-wrap preserves line breaks from MedGemma */}
          <span style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</span>

          {/* Blinking cursor while this message is still streaming */}
          {msg.streaming && (
            <span
              className="inline-block ml-0.5 w-[2px] h-[1em] bg-blue-400 align-middle animate-pulse"
              aria-hidden="true"
            />
          )}

          <span
            className={`text-xs block mt-1 ${isUser ? 'text-blue-200' : 'text-gray-400'}`}
          >
            {new Date(msg.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>
      </div>
    );
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="fixed bottom-20 right-4 z-50 w-96 max-w-[calc(100vw-2rem)]">
      <div className="bg-white rounded-t-xl border border-gray-200 shadow-2xl flex flex-col max-h-[32rem]">

        {/* ── Header ── */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-white rounded-t-xl shrink-0">
          <div className="flex items-center space-x-2">
            <div className="h-2 w-2 rounded-full bg-green-400" title="CarePath AI online" />
            <h3 className="font-semibold text-gray-900 text-sm">CarePath AI</h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Close chat"
            className="text-gray-400 hover:text-gray-600 transition-colors p-1 rounded"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* ── Message list ── */}
        <div className="flex-1 overflow-y-auto p-4 space-y-1 bg-gray-50">
          {/* Greeting shown before first message */}
          {messages.length === 0 && (
            <div className="flex justify-start mb-3">
              <div className="max-w-xs px-4 py-2 rounded-lg rounded-bl-none bg-gray-100 text-gray-800 text-sm leading-relaxed">
                👋 I'm CarePath AI, your medical tourism guide for Tamil Nadu.
                Ask me about hospitals, procedures, costs, or upload a prescription.
              </div>
            </div>
          )}

          {messages.map((msg, idx) => renderMessage(msg, idx))}

          {/* Scroll anchor */}
          <div ref={messagesEndRef} />
        </div>

        {/* ── Input ── */}
        <div className="px-4 py-3 border-t border-gray-100 bg-white rounded-b-xl shrink-0">
          <div className="flex space-x-2 items-end">
            <textarea
              rows={1}
              value={message}
              onChange={(e) => onMessageChange(e.target.value)}
              onKeyDown={onKeyPress}
              placeholder="Ask about hospitals, costs, symptoms…"
              disabled={isStreaming}
              className="flex-1 resize-none px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              onClick={onSendMessage}
              disabled={!message.trim() || isStreaming}
              aria-label="Send message"
              className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
            >
              {isStreaming ? (
                /* Spinner while waiting */
                <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2 text-center">
            AI-assisted guidance only — always consult a qualified clinician.
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;
