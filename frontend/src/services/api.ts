import axios from 'axios';
import { User, Journal, Credential, Digest, InterestTopic, InterestTopicCreate, InterestTopicUpdate, ImportResult } from '../types';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth API
export const authAPI = {
  register: async (email: string, name: string, password: string) => {
    const response = await api.post('/auth/register', { email, name, password });
    return response.data;
  },
  
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  },
  
  logout: async () => {
    const response = await api.post('/auth/logout');
    return response.data;
  },
};

// Journals API
export const journalsAPI = {
  getAll: async (): Promise<Journal[]> => {
    const response = await api.get('/journals');
    return response.data;
  },
  
  create: async (journal: { name: string; platform: string; url: string }): Promise<Journal> => {
    const response = await api.post('/journals', journal);
    return response.data;
  },
  
  delete: async (id: string) => {
    const response = await api.delete(`/journals/${id}`);
    return response.data;
  },
};

// Digests API
export const digestsAPI = {
  generate: async (): Promise<Digest> => {
    const response = await api.post('/digests/generate');
    return response.data;
  },
  
  getLatest: async (): Promise<Digest> => {
    const response = await api.get('/digests/latest');
    return response.data;
  },
  
  getAll: async (): Promise<Digest[]> => {
    const response = await api.get('/digests');
    return response.data;
  },
  
  getById: async (id: string): Promise<Digest> => {
    const response = await api.get(`/digests/${id}`);
    return response.data;
  },
};

// Credentials API
export const credentialsAPI = {
  getAll: async (): Promise<Credential[]> => {
    const response = await api.get('/credentials');
    return response.data;
  },

  create: async (data: { journalId: string; journalName: string; username: string; password: string; credentialType: string }): Promise<Credential> => {
    const response = await api.post('/credentials', data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    const response = await api.delete(`/credentials/${id}`);
    return response.data;
  },
};

// Interest Topics API
export const interestTopicsAPI = {
  getAll: async (): Promise<InterestTopic[]> => {
    const response = await api.get('/user/interests');
    return response.data.topics || response.data;
  },
  
  create: async (data: InterestTopicCreate): Promise<InterestTopic> => {
    const response = await api.post('/user/interests', data);
    return response.data;
  },
  
  update: async (id: string, data: InterestTopicUpdate): Promise<InterestTopic> => {
    const response = await api.put(`/user/interests/${id}`, data);
    return response.data;
  },
  
  delete: async (id: string): Promise<void> => {
    const response = await api.delete(`/user/interests/${id}`);
    return response.data;
  },
  
  export: async (): Promise<Blob> => {
    const response = await api.post('/user/interests/export', {}, {
      responseType: 'blob',
    });
    return response.data;
  },
  
  import: async (file: File): Promise<ImportResult> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/user/interests/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
  
  // Chatbot API
  sendChatMessage: async (topicId: string, message: string) => {
    const response = await api.post(`/user/interests/${topicId}/chat`, { message });
    return response.data;
  },
  
  getConversation: async (topicId: string) => {
    const response = await api.get(`/user/interests/${topicId}/conversation`);
    return response.data;
  },
  
  resetConversation: async (topicId: string) => {
    const response = await api.post(`/user/interests/${topicId}/conversation/reset`);
    return response.data;
  },
  
  saveDescription: async (topicId: string, description: string): Promise<InterestTopic> => {
    const response = await api.post(`/user/interests/${topicId}/description/save`, { description });
    return response.data;
  },

  generateDescription: async (topicId: string): Promise<{ description: string }> => {
    const response = await api.post(`/user/interests/${topicId}/description/generate`);
    return response.data;
  },
};
