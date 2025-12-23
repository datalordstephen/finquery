import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Upload document
export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// List all documents
export const listDocuments = async () => {
  const response = await api.get('/documents');
  return response.data;
};

// Query documents
export const queryDocuments = async (question, documentNames = null) => {
  const response = await api.post('/query', {
    question,
    document_names: documentNames,
    n_results: 5,
  });
  return response.data;
};

// Delete document
export const deleteDocument = async (docName) => {
  const response = await api.delete(`/documents/${docName}`);
  return response.data;
};

export default api;