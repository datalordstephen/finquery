import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import Sidebar from '../components/Sidebar';
import ChatArea from '../components/ChatArea';
import InputBar from '../components/InputBar';
import { uploadDocument, listDocuments, queryDocumentsStream, deleteDocument } from '../api';
import { useAuth } from '../context/AuthContext';
import '../App.css';

function Dashboard() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const { user, logout } = useAuth();

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
      toast.error('Failed to load documents');
    }
  };

  const handleUpload = async (file) => {
    if (!file.name.endsWith('.pdf')) {
      toast.error('Please upload a PDF file');
      return;
    }

    setIsUploading(true);
    const uploadToast = toast.loading(`Uploading ${file.name}...`);
    
    try {
      await uploadDocument(file);
      await fetchDocuments();
      toast.success(`Successfully uploaded ${file.name}`, { id: uploadToast });
    } catch (error) {
      console.error('Error uploading document:', error);
      toast.error(`Failed to upload ${file.name}`, { id: uploadToast });
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docName) => {
    try {
      await deleteDocument(docName);
      setSelectedDocs(selectedDocs.filter(name => name !== docName));
      await fetchDocuments();
      toast.success(`Deleted ${docName}`);
    } catch (error) {
      console.error('Error deleting document:', error);
      toast.error(`Failed to delete ${docName}`);
    }
  };

  const handleSelectDoc = (docName) => {
    if (selectedDocs.includes(docName)) {
      setSelectedDocs(selectedDocs.filter((name) => name !== docName));
    } else {
      if (selectedDocs.length >= MAX_SELECTED_DOCS) {
        toast.error(`You can only select up to ${MAX_SELECTED_DOCS} documents at a time`);
        return;
      }
      setSelectedDocs([...selectedDocs, docName]);
      toast.success(`Selected ${docName}`);
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

    // Add empty assistant message that will be streamed into
    const assistantMessage = {
      role: 'assistant',
      content: '',
      sources: [],
    };
    setMessages((prev) => [...prev, assistantMessage]);
    setIsLoading(true);

    try {
      const documentNames = selectedDocs.length > 0 ? selectedDocs : null;

      await queryDocumentsStream(
        question,
        documentNames,
        // onToken - append each token to the message
        (token) => {
          setMessages((prev) => {
            const lastMsg = prev[prev.length - 1];
            return [
              ...prev.slice(0, -1),
              { ...lastMsg, content: lastMsg.content + token }
            ];
          });
        },
        // onDone - add sources when complete
        (sources) => {
          setMessages((prev) => {
            const lastMsg = prev[prev.length - 1];
            return [
              ...prev.slice(0, -1),
              { ...lastMsg, sources }
            ];
          });
        }
      );
    } catch (error) {
      console.error('Error querying documents:', error);
      setMessages((prev) => {
        const updated = [...prev];
        const lastMsg = updated[updated.length - 1];
        if (!lastMsg.content) {
          lastMsg.content = 'Sorry, an error occurred while processing your question. Please try again.';
        }
        return [...updated];
      });
      toast.error('Failed to get response');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    toast.success('Logged out successfully');
  };

  return (
    <div className="app-container">
      <Sidebar
        documents={documents}
        selectedDocs={selectedDocs}
        onSelectDoc={handleSelectDoc}
        onUpload={handleUpload}
        onDelete={handleDelete}
        isUploading={isUploading}
        user={user}
        onLogout={handleLogout}
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
  );
}

export default Dashboard;