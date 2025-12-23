import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputBar from './components/InputBar';
import { uploadDocument, listDocuments, queryDocuments } from './api';
import './App.css';

function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const MAX_SELECTED_DOCS = 2;

  // Load documents on mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const data = await listDocuments();
      setDocuments(data.documents);
    } catch (error) {
      console.error('Error fetching documents:', error);
      alert('Failed to load documents');
    }
  };

  const handleUpload = async (file) => {
    if (!file.name.endsWith('.pdf')) {
      alert('Please upload a PDF file');
      return;
    }

    setIsUploading(true);
    try {
      await uploadDocument(file);
      await fetchDocuments(); // Refresh list
      alert(`Successfully uploaded ${file.name}`);
    } catch (error) {
      console.error('Error uploading document:', error);
      alert(`Failed to upload ${file.name}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSelectDoc = (docName) => {
    if (selectedDocs.includes(docName)) {
      // Deselect
      setSelectedDocs(selectedDocs.filter((name) => name !== docName));
    } else {
      // Select (max 2)
      if (selectedDocs.length >= MAX_SELECTED_DOCS) {
        alert(`You can only select up to ${MAX_SELECTED_DOCS} documents at a time`);
        return;
      }
      setSelectedDocs([...selectedDocs, docName]);
    }
  };

  const handleRemoveDoc = (docName) => {
    setSelectedDocs(selectedDocs.filter((name) => name !== docName));
  };

  const handleSendMessage = async (question) => {
    // Add user message
    const userMessage = {
      role: 'user',
      content: question,
    };
    setMessages((prev) => [...prev, userMessage]);

    setIsLoading(true);
    try {
      // Query with selected docs (or null for all)
      const documentNames = selectedDocs.length > 0 ? selectedDocs : null;
      const response = await queryDocuments(question, documentNames);

      // Add assistant message
      const assistantMessage = {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error querying documents:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, an error occurred while processing your question.',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: '#111827' }}>
      <Sidebar
        documents={documents}
        selectedDocs={selectedDocs}
        onSelectDoc={handleSelectDoc}
        onUpload={handleUpload}
        isUploading={isUploading}
      />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <ChatArea messages={messages} isLoading={isLoading} />
        <InputBar
          selectedDocs={selectedDocs}
          onRemoveDoc={handleRemoveDoc}
          onSendMessage={handleSendMessage}
          disabled={isLoading}
        />
      </div>
    </div>
  );
}

export default App;