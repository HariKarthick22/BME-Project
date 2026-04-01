// API Configuration
// Change this if deploying to a different backend URL
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
    HOSPITALS: `${API_BASE_URL}/api/hospitals`,
    CHAT_STREAM: `${API_BASE_URL}/api/chat/stream`,
    MEDICAL_ANALYSIS: `${API_BASE_URL}/api/analysis/symptoms`,
    UPLOAD: `${API_BASE_URL}/api/analysis/prescription`,
    INTENT: `${API_BASE_URL}/api/intent`,
    HEALTH_CHECK: `${API_BASE_URL}/health`,
    ANALYZE_XRAY: `${API_BASE_URL}/api/analyze-xray`,
    PARSE_PRESCRIPTION: `${API_BASE_URL}/api/parse-prescription`,
};
