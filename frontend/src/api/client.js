import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL !== undefined ? import.meta.env.VITE_API_URL : '';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 45000,
});

export const api = {
  checkHealth: async () => {
    const res = await client.get('/health');
    return res.data;
  },

  uploadFile: async (file, sheetName = null) => {
    const formData = new FormData();
    formData.append('file', file);
    if (sheetName) {
      formData.append('sheet_name', sheetName);
    }

    const res = await client.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  askQuestion: async (tableId, question, chatHistory = []) => {
    const res = await client.post('/ask', {
      table_id: tableId,
      question,
      chat_history: chatHistory,
    });
    return res.data;
  },

  getReportUrl: (tableId, format = 'xlsx') => {
    return `${API_BASE_URL}/report/${tableId}?format=${format}`;
  },
};
