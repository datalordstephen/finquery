import React, { useState, useEffect } from 'react';
import toast, { Toaster } from 'react-hot-toast';  // ← Add this
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputBar from './components/InputBar';
import { uploadDocument, listDocuments, queryDocuments, deleteDocument } from './api';
import './App.css';

function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const MAX_SELECTED_DOCS = 2;

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const data = await listDocuments();
      setDocuments(data.documents);
    } catch (error) {
      console.error('Error fetching documents:', error);
      toast.error('Failed to load documents');  // ← Replace alert
    }
  };

  const handleUpload = async (file) => {
    if (!file.name.endsWith('.pdf')) {
      toast.error('Please upload a PDF file');  // ← Replace alert
      return;
    }

    setIsUploading(true);
    const uploadToast = toast.loading(`Uploading ${file.name}...`);  // ← Loading toast
    
    try {
      await uploadDocument(file);
      await fetchDocuments();
      toast.success(`Successfully uploaded ${file.name}`, { id: uploadToast });  // ← Success
    } catch (error) {
      console.error('Error uploading document:', error);
      toast.error(`Failed to upload ${file.name}`, { id: uploadToast });  // ← Error
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docName) => {
    try {
      await deleteDocument(docName);
      setSelectedDocs(selectedDocs.filter(name => name !== docName));
      await fetchDocuments();
      toast.success(`Deleted ${docName}`);  // ← Replace alert
    } catch (error) {
      console.error('Error deleting document:', error);
      toast.error(`Failed to delete ${docName}`);  // ← Replace alert
    }
  };

  const handleSelectDoc = (docName) => {
    if (selectedDocs.includes(docName)) {
      setSelectedDocs(selectedDocs.filter((name) => name !== docName));
    } else {
      if (selectedDocs.length >= MAX_SELECTED_DOCS) {
        toast.error(`You can only select up to ${MAX_SELECTED_DOCS} documents at a time`);  // ← Replace alert
        return;
      }
      setSelectedDocs([...selectedDocs, docName]);
      toast.success(`Selected ${docName}`);  // ← Add feedback
    }
  };

  const handleRemoveDoc = (docName) => {
    setSelectedDocs(selectedDocs.filter((name) => name !== docName));
  };

  const handleSendMessage = async (question) => {
    const userMessage = {
      role: 'user',
      content: question,
    };
    setMessages((prev) => [...prev, userMessage]);

    setIsLoading(true);
    try {
      const documentNames = selectedDocs.length > 0 ? selectedDocs : null;
      const response = await queryDocuments(question, documentNames);

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
        content: 'Sorry, an error occurred while processing your question. Please try again.',
      };
      setMessages((prev) => [...prev, errorMessage]);
      toast.error('Failed to get response');  // ← Add toast
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <Toaster 
        position="top-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: '#1f2937',
            color: '#fff',
            fontFamily: 'Poppins, sans-serif',
          },
          success: {
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
      <div className="app-container">
        <Sidebar
          documents={documents}
          selectedDocs={selectedDocs}
          onSelectDoc={handleSelectDoc}
          onUpload={handleUpload}
          onDelete={handleDelete}
          isUploading={isUploading}
        />
        <div className="main-content">
          <ChatArea
            messages={messages} 
            isLoading={isLoading}
            onExampleClick={handleSendMessage}
          />
          <InputBar
            selectedDocs={selectedDocs}
            onRemoveDoc={handleRemoveDoc}
            onSendMessage={handleSendMessage}
            disabled={isLoading}
          />
        </div>
      </div>
    </>
  );
}

export default App;