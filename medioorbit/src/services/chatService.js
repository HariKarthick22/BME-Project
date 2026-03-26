/**
 * chatService.js
 * Handles all CarePath AI chat calls — streaming (SSE) and non-streaming fallback.
 */

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

/**
 * Send a chat message and stream the response token-by-token.
 *
 * @param {Object}   opts
 * @param {string}   opts.sessionId          - Unique session identifier
 * @param {string}   opts.message            - User message text
 * @param {Object}   [opts.prescriptionData] - Optional parsed prescription data
 * @param {function} opts.onToken            - Called with each new token string
 * @param {function} [opts.onDone]           - Called when stream finishes
 * @param {function} [opts.onError]          - Called with an Error on failure
 * @returns {Promise<void>}
 */
export async function streamChat({ sessionId, message, prescriptionData = null, onToken, onDone, onError }) {
  try {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId,
      },
      body: JSON.stringify({
        session_id: sessionId,
        message,
        prescription_data: prescriptionData,
      }),
    });

    if (!response.ok) {
      const detail = await response.text().catch(() => response.statusText);
      throw new Error(`Chat API error ${response.status}: ${detail}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE lines are separated by \n\n; process complete lines only
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? ''; // keep the incomplete last line

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;

        const payload = line.slice(6).trim();
        if (payload === '[DONE]') {
          onDone?.();
          return;
        }

        try {
          const parsed = JSON.parse(payload);
          if (parsed.token) {
            onToken(parsed.token);
          } else if (parsed.error) {
            throw new Error(parsed.error);
          }
        } catch (parseErr) {
          // Skip malformed SSE lines silently
        }
      }
    }

    onDone?.();
  } catch (err) {
    if (onError) {
      onError(err);
    } else {
      throw err;
    }
  }
}

/**
 * Non-streaming fallback — returns the full response object.
 * Used when SSE is not available or for programmatic callers.
 *
 * @param {string} sessionId
 * @param {string} message
 * @param {Object} [prescriptionData]
 * @returns {Promise<{response: string, ui_actions: Array, matched_hospitals: Array}>}
 */
export async function sendChat(sessionId, message, prescriptionData = null) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Session-ID': sessionId,
    },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      prescription_data: prescriptionData,
    }),
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => response.statusText);
    throw new Error(`Chat API error ${response.status}: ${detail}`);
  }

  return response.json();
}
