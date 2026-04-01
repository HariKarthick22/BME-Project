import React, { useState, useRef, useEffect } from 'react';
import { API_ENDPOINTS } from '../config';

const SESSION_ID = `session-${Date.now()}`;
const SYSTEM_PROMPT = "You are 'CarePath AI,' a compassionate healthcare assistant. Analyze X-rays and documents, provide AI summaries (not diagnosis), retrieve hospitals, and always include: 'Please consult a board-certified professional for a clinical evaluation.'";

export const ChatWidget = () => {
    const [open, setOpen] = useState(false);
    const [messages, setMessages] = useState([
        { role: 'assistant', text: "Hello! I'm CarePath AI. Ask me about hospitals, symptoms, or upload a medical document for analysis." }
    ]);
    const [input, setInput] = useState('');
    const [streaming, setStreaming] = useState(false);
    const bottomRef = useRef(null);
    const inputRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    useEffect(() => {
        if (open) inputRef.current?.focus();
    }, [open]);

    // Listen for Navbar "Consultation" / "Concierge" clicks
    useEffect(() => {
        const handler = () => setOpen(true);
        window.addEventListener('carepath:open-chat', handler);
        return () => window.removeEventListener('carepath:open-chat', handler);
    }, []);

    const sendMessage = async () => {
        const text = input.trim();
        if (!text || streaming) return;

        const userMsg = { role: 'user', text };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setStreaming(true);

        // Placeholder for the streaming assistant reply
        setMessages(prev => [...prev, { role: 'assistant', text: '', streaming: true }]);

        const updateAssistant = (value, isStreaming = true) => {
            setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = { role: 'assistant', text: value, streaming: isStreaming };
                return updated;
            });
        };

        try {
            const streamController = new AbortController();
            const streamTimer = setTimeout(() => streamController.abort(), 90000);
            const res = await fetch(API_ENDPOINTS.CHAT_STREAM, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: SESSION_ID,
                    message: text,
                    model_config: { provider: 'local' },
                }),
                signal: streamController.signal,
            });
            clearTimeout(streamTimer);

            if (!res.ok) throw new Error(`Server error ${res.status}`);
            if (!res.body) throw new Error('Empty streaming response body');

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let accumulated = '';
            let buffer = '';

            const appendText = (piece) => {
                if (!piece) return;
                accumulated += piece;
                updateAssistant(accumulated, true);
            };

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (!line) continue;

                    if (line.startsWith('data:')) {
                        // Keep original spacing from streamed chunks.
                        let data = line.slice(5);
                        if (data.startsWith(' ')) data = data.slice(1);
                        if (data === '[DONE]') continue;
                        appendText(data);
                        continue;
                    }

                    // Support plain-text chunk streams if server skips SSE framing.
                    appendText(line);
                }
            }

            if (buffer) {
                if (buffer.startsWith('data:')) {
                    let data = buffer.slice(5);
                    if (data.startsWith(' ')) data = data.slice(1);
                    if (data && data !== '[DONE]') appendText(data);
                } else {
                    appendText(buffer);
                }
            }

            // Mark streaming complete
            updateAssistant(accumulated || 'No response from model. Please retry.', false);

        } catch (err) {
            // Fallback: try non-streaming /api/chat
            try {
                const fallbackController = new AbortController();
                const fallbackTimer = setTimeout(() => fallbackController.abort(), 60000);
                const res2 = await fetch(`${API_ENDPOINTS.CHAT_STREAM.replace('/stream', '/message')}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: SESSION_ID,
                        message: text,
                        model_config: { provider: 'local' },
                    }),
                    signal: fallbackController.signal,
                });
                clearTimeout(fallbackTimer);
                const data = await res2.json();
                const reply = data.message || data.response || 'No response received.';
                updateAssistant(reply, false);
            } catch {
                updateAssistant(`Error: ${err.message}. Is the backend running?`, false);
            }
        } finally {
            setStreaming(false);
        }
    };

    return (
        <>
            {/* Floating toggle button */}
            <button
                onClick={() => setOpen(o => !o)}
                className="fixed bottom-8 right-8 z-50 w-14 h-14 bg-primary text-on-primary rounded-full shadow-2xl flex items-center justify-center hover:opacity-90 transition-all duration-200 hover:scale-105"
                title="CarePath AI Assistant"
            >
                <span className="material-symbols-outlined text-[28px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                    {open ? 'close' : 'chat'}
                </span>
            </button>

            {/* Chat panel */}
            {open && (
                <div className="fixed bottom-28 right-4 sm:right-8 z-50 w-[calc(100vw-2rem)] sm:w-95 max-h-[80vh] sm:max-h-140 flex flex-col bg-surface-container-lowest rounded-2xl shadow-[0_24px_64px_rgba(26,28,28,0.18)] border border-outline-variant/20 overflow-hidden">

                    {/* Header */}
                    <div className="bg-primary px-5 py-4 flex items-center gap-3 shrink-0">
                        <span className="material-symbols-outlined text-secondary-fixed text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>vital_signs</span>
                        <div>
                            <p className="text-on-primary font-headline italic text-base leading-tight">CarePath AI</p>
                        </div>
                        <div className="ml-auto flex items-center gap-1.5">
                            <span className="w-2 h-2 bg-secondary rounded-full animate-pulse"></span>
                            <span className="text-on-primary-container text-[11px]">Online</span>
                        </div>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-3 no-scrollbar">
                        {messages.map((msg, i) => (
                            <div key={i} className={`flex min-w-0 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[88%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap wrap-break-word overflow-x-hidden ${
                                    msg.role === 'user'
                                        ? 'bg-primary text-on-primary rounded-br-sm'
                                        : 'bg-surface-container-low text-on-surface rounded-bl-sm'
                                }`}>
                                    {msg.text}
                                    {msg.streaming && (
                                        <span className="inline-block w-1.5 h-4 bg-secondary ml-1 animate-pulse rounded-sm align-middle"></span>
                                    )}
                                </div>
                            </div>
                        ))}
                        <div ref={bottomRef} />
                    </div>

                    {/* Disclaimer */}
                    <div className="px-4 py-2 bg-surface-container-low border-t border-outline-variant/10 shrink-0">
                        <p className="text-[10px] text-outline text-center">AI summaries only — not clinical advice. Always consult a doctor.</p>
                    </div>

                    {/* Input bar */}
                    <div className="flex items-center gap-2 px-3 py-3 border-t border-outline-variant/10 bg-surface-container-lowest shrink-0">
                        <input
                            ref={inputRef}
                            type="text"
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && sendMessage()}
                            placeholder="Ask about symptoms, hospitals…"
                            disabled={streaming}
                            className="flex-1 bg-surface-container-low rounded-xl px-4 py-2.5 text-sm outline-none border border-outline-variant/20 placeholder:text-outline-variant disabled:opacity-60"
                        />
                        <button
                            onClick={sendMessage}
                            disabled={!input.trim() || streaming}
                            className="w-10 h-10 bg-primary text-on-primary rounded-xl flex items-center justify-center disabled:opacity-40 hover:opacity-90 transition-opacity shrink-0"
                        >
                            <span className="material-symbols-outlined text-[20px]" style={{ fontVariationSettings: "'FILL' 1" }}>
                                {streaming ? 'progress_activity' : 'send'}
                            </span>
                        </button>
                    </div>
                </div>
            )}
        </>
    );
};
