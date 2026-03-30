import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Paper,
  Box,
  Button,
  CircularProgress,
  Alert,
  List,
  ListItem,
  ListItemText,
  IconButton,
  TextField,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Chip,
} from '@mui/material';
import { ArrowBack, Delete, Edit, Add, FileDownload, FileUpload, Chat, CheckCircle, RadioButtonUnchecked, HourglassEmpty, Visibility } from '@mui/icons-material';
import Tooltip from '@mui/material/Tooltip';
import { useNavigate } from 'react-router-dom';
import { interestTopicsAPI } from '../services/api';
import { InterestTopic } from '../types';
import ChatbotUI from '../components/ChatbotUI';

const SettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const [topics, setTopics] = useState<InterestTopic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newTopicText, setNewTopicText] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  
  // Edit state
  const [editingTopicId, setEditingTopicId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState('');
  const [editValidationError, setEditValidationError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  
  // Delete confirmation dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [topicToDelete, setTopicToDelete] = useState<InterestTopic | null>(null);
  const [deleting, setDeleting] = useState(false);
  
  // Import/Export state
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);
  
  // Chatbot state
  const [chatbotOpen, setChatbotOpen] = useState(false);
  const [activeChatbotTopicId, setActiveChatbotTopicId] = useState<string | null>(null);
  const [activeChatbotTopicText, setActiveChatbotTopicText] = useState<string>('');

  // View details state
  const [viewDetailsTopic, setViewDetailsTopic] = useState<InterestTopic | null>(null);

  // Chatbot handlers
  const handleOpenChatbot = (topic: InterestTopic) => {
    setActiveChatbotTopicId(topic.id);
    setActiveChatbotTopicText(topic.topicText);
    setChatbotOpen(true);
  };

  const handleCloseChatbot = () => {
    setChatbotOpen(false);
    setActiveChatbotTopicId(null);
    setActiveChatbotTopicText('');
  };

  const handleDescriptionSaved = async (description: string) => {
    if (!activeChatbotTopicId) return;

    try {
      // Reload topics from backend to get updated data
      const updatedTopics = await interestTopicsAPI.getAll();
      setTopics(updatedTopics);
      
      handleCloseChatbot();
    } catch (err: any) {
      setError('Failed to reload topics after saving description');
      console.error('Error reloading topics:', err);
    }
  };

  // Get button text based on conversation status
  const getChatbotButtonText = (topic: InterestTopic): string => {
    if (!topic.conversationStatus || topic.conversationStatus === 'not_started') {
      return 'Start';
    } else if (topic.conversationStatus === 'in_progress') {
      return 'Continue';
    } else {
      return 'Edit';
    }
  };

  // Get status icon based on conversation status
  const getStatusIcon = (topic: InterestTopic) => {
    if (topic.comprehensiveDescription && topic.conversationStatus === 'completed') {
      return <CheckCircle sx={{ color: 'success.main', fontSize: 20 }} aria-label="Completed" />;
    } else if (topic.conversationStatus === 'in_progress') {
      return <HourglassEmpty sx={{ color: 'warning.main', fontSize: 20 }} aria-label="In progress" />;
    } else {
      return <RadioButtonUnchecked sx={{ color: 'action.disabled', fontSize: 20 }} aria-label="Not started" />;
    }
  };

  // Load topics from backend API
  useEffect(() => {
    const loadTopics = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const data = await interestTopicsAPI.getAll();
        setTopics(data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load interest topics');
        console.error('Error loading topics:', err);
      } finally {
        setLoading(false);
      }
    };

    loadTopics();
  }, []);

  const validateTopicText = (text: string): string | null => {
    const trimmed = text.trim();
    if (trimmed.length === 0) {
      return 'Topic cannot be empty or whitespace only';
    }
    if (trimmed.length < 2) {
      return 'Topic must be at least 2 characters';
    }
    if (trimmed.length > 200) {
      return 'Topic must be at most 200 characters';
    }
    return null;
  };

  const handleAddTopic = async () => {
    setValidationError(null);
    
    const error = validateTopicText(newTopicText);
    if (error) {
      setValidationError(error);
      return;
    }

    try {
      setAdding(true);
      
      const newTopic = await interestTopicsAPI.create({ topicText: newTopicText.trim() });
      setTopics([...topics, newTopic]);
      setNewTopicText('');
      setValidationError(null);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to add topic';
      setError(errorMsg);
      console.error('Error adding topic:', err);
    } finally {
      setAdding(false);
    }
  };

  const handleTopicTextChange = (text: string) => {
    setNewTopicText(text);
    setValidationError(null);
  };

  // Edit handlers
  const handleStartEdit = (topic: InterestTopic) => {
    setEditingTopicId(topic.id);
    setEditingText(topic.topicText);
    setEditValidationError(null);
  };

  const handleCancelEdit = () => {
    setEditingTopicId(null);
    setEditingText('');
    setEditValidationError(null);
  };

  const handleSaveEdit = async (topicId: string) => {
    setEditValidationError(null);
    
    const error = validateTopicText(editingText);
    if (error) {
      setEditValidationError(error);
      return;
    }

    try {
      setSaving(true);
      
      const updatedTopic = await interestTopicsAPI.update(topicId, { topicText: editingText.trim() });
      
      setTopics(topics.map(topic => 
        topic.id === topicId ? updatedTopic : topic
      ));
      
      setEditingTopicId(null);
      setEditingText('');
      setEditValidationError(null);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to update topic';
      setError(errorMsg);
      console.error('Error updating topic:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleEditKeyDown = (e: React.KeyboardEvent, topicId: string) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSaveEdit(topicId);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleCancelEdit();
    }
  };

  const handleEditBlur = (topicId: string) => {
    // Save on blur if there's valid text
    if (editingText.trim() && !editValidationError) {
      handleSaveEdit(topicId);
    } else {
      handleCancelEdit();
    }
  };

  // Delete handlers
  const handleDeleteClick = (topic: InterestTopic) => {
    setTopicToDelete(topic);
    setDeleteDialogOpen(true);
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setTopicToDelete(null);
  };

  const handleDeleteConfirm = async () => {
    if (!topicToDelete) return;

    try {
      setDeleting(true);
      
      await interestTopicsAPI.delete(topicToDelete.id);
      
      setTopics(topics.filter(topic => topic.id !== topicToDelete.id));
      setDeleteDialogOpen(false);
      setTopicToDelete(null);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to delete topic';
      setError(errorMsg);
      console.error('Error deleting topic:', err);
    } finally {
      setDeleting(false);
    }
  };

  // Export handler
  const handleExportTopics = async () => {
    try {
      setExporting(true);
      setError(null);
      
      const blob = await interestTopicsAPI.export();
      
      // Create download link
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `interest-topics-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      // Show success notification
      setImportResult(`Successfully exported ${topics.length} topic${topics.length !== 1 ? 's' : ''}`);
      setTimeout(() => setImportResult(null), 5000);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to export topics';
      setError(errorMsg);
      console.error('Error exporting topics:', err);
    } finally {
      setExporting(false);
    }
  };

  // Import handler
  const handleImportTopics = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setImporting(true);
      setError(null);
      setImportResult(null);
      
      const result = await interestTopicsAPI.import(file);
      
      // Reload topics to get the updated list
      const updatedTopics = await interestTopicsAPI.getAll();
      setTopics(updatedTopics);
      
      // Show import results
      let resultMessage = `Added ${result.topicsAdded} topic${result.topicsAdded !== 1 ? 's' : ''}`;
      if (result.topicsSkipped > 0) {
        resultMessage += `, skipped ${result.topicsSkipped} duplicate${result.topicsSkipped !== 1 ? 's' : ''}`;
        if (result.duplicates && result.duplicates.length <= 5) {
          resultMessage += `: ${result.duplicates.join(', ')}`;
        }
      }
      setImportResult(resultMessage);
      setTimeout(() => setImportResult(null), 8000);
      
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Failed to import topics';
      setError(errorMsg);
      console.error('Error importing topics:', err);
    } finally {
      setImporting(false);
      // Reset file input
      event.target.value = '';
    }
  };

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      {/* Header with back navigation */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <IconButton onClick={() => navigate('/dashboard')} sx={{ mr: 2 }}>
          <ArrowBack />
        </IconButton>
        <Typography variant="h4">
          Research Interest Topics
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Add topic form */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Add New Interest Topic
        </Typography>
        <Stack spacing={2}>
          <TextField
            fullWidth
            label="Interest Topic"
            value={newTopicText}
            onChange={(e) => handleTopicTextChange(e.target.value)}
            placeholder="e.g., Signal Integrity, Power Integrity, EMC"
            error={!!validationError}
            helperText={validationError || `${newTopicText.length}/200 characters`}
            disabled={adding}
          />
          <Button
            variant="contained"
            startIcon={adding ? <CircularProgress size={20} color="inherit" /> : <Add />}
            onClick={handleAddTopic}
            disabled={adding || newTopicText.trim().length === 0}
          >
            {adding ? 'Adding...' : 'Add Topic'}
          </Button>
        </Stack>
      </Paper>

      {/* Empty state message */}
      {topics.length === 0 && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            No interest topics yet. Add your first topic above to get started.
          </Typography>
        </Paper>
      )}

      {/* Topic list with chatbot integration */}
      {topics.length > 0 && (
        <Paper sx={{ mb: 3 }}>
          <List>
            {topics.map((topic, index) => (
              <ListItem
                key={topic.id}
                divider={index < topics.length - 1}
                secondaryAction={
                  editingTopicId === topic.id ? (
                    <Box>
                      {saving && <CircularProgress size={20} sx={{ mr: 1 }} />}
                    </Box>
                  ) : (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      {topic.comprehensiveDescription && (
                        <Tooltip title="View details">
                          <IconButton
                            onClick={() => setViewDetailsTopic(topic)}
                            disabled={editingTopicId !== null}
                            aria-label={`View details for ${topic.topicText}`}
                          >
                            <Visibility />
                          </IconButton>
                        </Tooltip>
                      )}
                      <Tooltip title={`${getChatbotButtonText(topic)} AI conversation`}>
                        <IconButton
                          onClick={() => handleOpenChatbot(topic)}
                          disabled={editingTopicId !== null}
                          aria-label={`${getChatbotButtonText(topic)} AI conversation for ${topic.topicText}`}
                        >
                          <Chat />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Edit topic">
                        <IconButton
                          onClick={() => handleStartEdit(topic)}
                          disabled={editingTopicId !== null}
                          aria-label={`Edit topic ${topic.topicText}`}
                        >
                          <Edit />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete topic">
                        <IconButton
                          onClick={() => handleDeleteClick(topic)}
                          disabled={editingTopicId !== null}
                          aria-label={`Delete topic ${topic.topicText}`}
                        >
                          <Delete />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  )
                }
              >
                {editingTopicId === topic.id ? (
                  <Box sx={{ width: '100%', pr: 8 }}>
                    <TextField
                      fullWidth
                      value={editingText}
                      onChange={(e) => setEditingText(e.target.value)}
                      onKeyDown={(e) => handleEditKeyDown(e, topic.id)}
                      onBlur={() => handleEditBlur(topic.id)}
                      error={!!editValidationError}
                      helperText={editValidationError || `${editingText.length}/200 characters`}
                      disabled={saving}
                      autoFocus
                      size="small"
                    />
                  </Box>
                ) : (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%', pr: 20 }}>
                    {getStatusIcon(topic)}
                    <Box sx={{ flex: 1 }}>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body1">
                              {topic.topicText}
                            </Typography>
                            {topic.comprehensiveDescription && (
                              <Chip 
                                label="AI Defined" 
                                size="small" 
                                color="primary" 
                                variant="outlined"
                                aria-label="This topic has a comprehensive AI-generated description"
                              />
                            )}
                          </Box>
                        }
                        secondary={`Added: ${new Date(topic.createdAt).toLocaleDateString()}`}
                      />
                    </Box>
                  </Box>
                )}
              </ListItem>
            ))}
          </List>
        </Paper>
      )}

      {/* Import/Export buttons */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Import/Export Topics
        </Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={exporting ? <CircularProgress size={20} color="inherit" /> : <FileDownload />}
            onClick={handleExportTopics}
            disabled={exporting || topics.length === 0}
          >
            {exporting ? 'Exporting...' : 'Export Topics'}
          </Button>
          <Button
            variant="outlined"
            component="label"
            startIcon={importing ? <CircularProgress size={20} color="inherit" /> : <FileUpload />}
            disabled={importing}
          >
            {importing ? 'Importing...' : 'Import Topics'}
            <input
              type="file"
              accept=".json"
              hidden
              onChange={handleImportTopics}
              disabled={importing}
            />
          </Button>
        </Stack>
        {topics.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Export is disabled when there are no topics to export.
          </Typography>
        )}
      </Paper>

      {/* Import result notification */}
      {importResult && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setImportResult(null)}>
          {importResult}
        </Alert>
      )}

      {/* Delete confirmation dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
        aria-labelledby="delete-dialog-title"
        aria-describedby="delete-dialog-description"
      >
        <DialogTitle id="delete-dialog-title">
          Delete Interest Topic
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="delete-dialog-description">
            Are you sure you want to delete '{topicToDelete?.topicText}'? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel} disabled={deleting}>
            Cancel
          </Button>
          <Button 
            onClick={handleDeleteConfirm} 
            color="error" 
            variant="contained"
            disabled={deleting}
            startIcon={deleting ? <CircularProgress size={20} color="inherit" /> : null}
          >
            {deleting ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Chatbot modal */}
      <Dialog
        open={chatbotOpen}
        onClose={handleCloseChatbot}
        maxWidth="md"
        fullWidth
        aria-labelledby="chatbot-dialog-title"
        aria-describedby="chatbot-dialog-description"
      >
        {activeChatbotTopicId && (
          <ChatbotUI
            topicId={activeChatbotTopicId}
            topicText={activeChatbotTopicText}
            onDescriptionSaved={handleDescriptionSaved}
            onCancel={handleCloseChatbot}
          />
        )}
      </Dialog>

      {/* View Details dialog */}
      <Dialog
        open={!!viewDetailsTopic}
        onClose={() => setViewDetailsTopic(null)}
        maxWidth="md"
        fullWidth
        aria-labelledby="view-details-dialog-title"
      >
        {viewDetailsTopic && (
          <>
            <DialogTitle id="view-details-dialog-title">
              {viewDetailsTopic.topicText}
            </DialogTitle>
            <DialogContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Comprehensive Description
              </Typography>
              <Paper variant="outlined" sx={{ p: 2, whiteSpace: 'pre-wrap', bgcolor: 'grey.50' }}>
                <Typography variant="body2">
                  {viewDetailsTopic.comprehensiveDescription}
                </Typography>
              </Paper>
              <Box sx={{ mt: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Created: {new Date(viewDetailsTopic.createdAt).toLocaleString()} · Updated: {new Date(viewDetailsTopic.updatedAt).toLocaleString()}
                </Typography>
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setViewDetailsTopic(null)}>Close</Button>
              <Button
                variant="outlined"
                startIcon={<Chat />}
                onClick={() => {
                  setViewDetailsTopic(null);
                  handleOpenChatbot(viewDetailsTopic);
                }}
              >
                Edit with AI
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Container>
  );
};

export default SettingsPage;
