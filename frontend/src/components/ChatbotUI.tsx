import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  IconButton,
  CircularProgress,
  Alert,
  Divider,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Stepper,
  Step,
  StepLabel,
  Chip,
} from '@mui/material';
import { Send, Close, Delete, AutoAwesome } from '@mui/icons-material';
import { ChatMessage } from '../types';
import { interestTopicsAPI } from '../services/api';

interface ChatbotUIProps {
  topicId: string;
  topicText: string;
  onDescriptionSaved: (description: string) => void;
  onCancel: () => void;
}

// The 4 areas the chatbot covers in strict order
const CONVERSATION_STEPS = [
  { label: 'Aspects', description: 'Specific sub-topics or areas of focus' },
  { label: 'Methods', description: 'Research techniques or approaches used' },
  { label: 'Applications', description: 'Domains or use cases of interest' },
  { label: 'Scope', description: 'Boundaries or topics to exclude' },
];

/**
 * Detect completed steps by counting numbered lists the assistant has presented.
 * The conversation follows a strict linear order, so the Nth list = step N.
 * A step is "complete" only when the NEXT step's list has appeared, meaning
 * the bot has moved on. The current (latest) step is always "in progress".
 */
function getCompletedSteps(messages: ChatMessage[]): boolean[] {
  // Find message indices where the assistant presented a numbered list (3+ items)
  const listMsgIndices: number[] = [];
  for (let i = 0; i < messages.length; i++) {
    if (messages[i].role === 'assistant') {
      const numberedItems = messages[i].content.match(/^\s*\d+[\.\)]/gm);
      if (numberedItems && numberedItems.length >= 3) {
        listMsgIndices.push(i);
      }
    }
  }

  // Step N is complete only if list N+1 exists (the bot moved to the next step)
  return CONVERSATION_STEPS.map((_, stepIdx) => {
    if (stepIdx >= listMsgIndices.length) return false;
    // This step is done only if the next step's list has been presented
    return stepIdx + 1 < listMsgIndices.length;
  });
}

const ChatbotUI: React.FC<ChatbotUIProps> = ({
  topicId,
  topicText,
  onDescriptionSaved,
  onCancel,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationStatus, setConversationStatus] = useState<'not_started' | 'in_progress' | 'completed'>('not_started');
  const [generatedDescription, setGeneratedDescription] = useState<string | null>(null);
  const [editedDescription, setEditedDescription] = useState('');
  const [shouldConclude, setShouldConclude] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const initializingRef = useRef(false);

  const completedSteps = getCompletedSteps(messages);
  const completedCount = completedSteps.filter(Boolean).length;
  // Show "Generate Summary" after at least 2 user messages (4 total messages including assistant)
  const userMessageCount = messages.filter(m => m.role === 'user').length;
  const canGenerate = userMessageCount >= 2;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!isLoading && !generatedDescription) {
      inputRef.current?.focus();
    }
  }, [isLoading, generatedDescription]);

  // Load conversation history
  useEffect(() => {
    if (initializingRef.current) return;
    initializingRef.current = true;

    const loadConversation = async () => {
      try {
        const data = await interestTopicsAPI.getConversation(topicId);
        if (data.conversationHistory && data.conversationHistory.length > 0) {
          setMessages(data.conversationHistory);
          setConversationStatus(data.conversationStatus);
        } else {
          setIsLoading(true);
          const response = await interestTopicsAPI.sendChatMessage(topicId, '');
          const assistantMessage: ChatMessage = {
            role: 'assistant',
            content: response.message,
            timestamp: new Date().toISOString(),
          };
          setMessages([assistantMessage]);
          setConversationStatus(response.conversationStatus);
          setShouldConclude(response.shouldConclude);
        }
      } catch (err: any) {
        console.error('Error loading conversation:', err);
        setError('Failed to load conversation. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };
    loadConversation();
  }, [topicId]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await interestTopicsAPI.sendChatMessage(topicId, userMessage.content);
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.message,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMessage]);
      setConversationStatus(response.conversationStatus);
      setShouldConclude(response.shouldConclude);
    } catch (err: any) {
      setMessages(prev => prev.slice(0, -1));
      if (err.response?.status === 408) {
        setError('The chatbot is taking longer than expected. Please try again.');
      } else if (err.response?.status === 404) {
        setError('Interest topic not found.');
      } else if (err.response?.status === 500) {
        setError('Unable to connect to AI service. Please try again.');
      } else {
        setError('Failed to get chatbot response. Please try again.');
      }
      console.error('Error sending message:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateDescription = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const result = await interestTopicsAPI.generateDescription(topicId);
      setGeneratedDescription(result.description);
      setEditedDescription(result.description);
      setConversationStatus('completed');
    } catch (err: any) {
      setError('Failed to generate description. Please try again.');
      console.error('Error generating description:', err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onCancel();
    }
  };

  const handleRetry = () => {
    setError(null);
    handleSendMessage();
  };

  const handleSaveDescription = async () => {
    if (!editedDescription.trim()) { setError('Description cannot be empty'); return; }
    if (editedDescription.length > 5000) { setError('Description must be at most 5000 characters'); return; }
    setIsLoading(true);
    setError(null);
    try {
      await interestTopicsAPI.saveDescription(topicId, editedDescription.trim());
      onDescriptionSaved(editedDescription.trim());
    } catch (err: any) {
      if (err.response?.status === 422) setError(err.response.data.detail || 'Invalid description');
      else if (err.response?.status === 404) setError('Interest topic not found');
      else setError('Failed to save description. Please try again.');
      console.error('Error saving description:', err);
    } finally { setIsLoading(false); }
  };

  const handleCancelDescription = () => {
    setGeneratedDescription(null);
    setEditedDescription('');
  };

  const handleDeleteConversation = async () => {
    setDeleteDialogOpen(false);
    setIsLoading(true);
    setError(null);
    try {
      await interestTopicsAPI.resetConversation(topicId);
      setMessages([]);
      setConversationStatus('not_started');
      setGeneratedDescription(null);
      setEditedDescription('');
      setShouldConclude(false);
      const response = await interestTopicsAPI.sendChatMessage(topicId, '');
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.message,
        timestamp: new Date().toISOString(),
      };
      setMessages([assistantMessage]);
      setConversationStatus(response.conversationStatus);
    } catch (err: any) {
      setError('Failed to delete conversation. Please try again.');
      console.error('Error deleting conversation:', err);
    } finally { setIsLoading(false); }
  };

  return (
    <Paper elevation={3} sx={{ height: '600px', display: 'flex', flexDirection: 'column', position: 'relative' }}>
      {/* Header */}
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h6" id="chatbot-dialog-title">
          Define Research Interest: {topicText}
        </Typography>
        <Box>
          {messages.length > 0 && !generatedDescription && (
            <IconButton onClick={() => setDeleteDialogOpen(true)} size="small" aria-label="Delete conversation history" sx={{ mr: 1 }}>
              <Delete />
            </IconButton>
          )}
          <IconButton onClick={onCancel} size="small" aria-label="Close chatbot">
            <Close />
          </IconButton>
        </Box>
      </Box>

      {/* Progress stepper — only show during conversation */}
      {!generatedDescription && messages.length > 0 && (
        <Box sx={{ px: 2, pt: 1.5, pb: 1 }}>
          <Stepper activeStep={completedCount} alternativeLabel sx={{ '& .MuiStepLabel-label': { fontSize: '0.75rem' } }}>
            {CONVERSATION_STEPS.map((step, idx) => (
              <Step key={step.label} completed={completedSteps[idx]}>
                <StepLabel
                  optional={
                    <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
                      {step.description}
                    </Typography>
                  }
                >
                  {step.label}
                </StepLabel>
              </Step>
            ))}
          </Stepper>
          {shouldConclude && (
            <Box sx={{ textAlign: 'center', mt: 0.5 }}>
              <Chip label="Ready to generate summary" color="success" size="small" variant="outlined" />
            </Box>
          )}
        </Box>
      )}

      {/* Error display */}
      {error && (
        <Alert severity="error" sx={{ m: 2 }} onClose={() => setError(null)}
          action={<Button color="inherit" size="small" onClick={handleRetry} aria-label="Retry sending message">Retry</Button>}
          role="alert" aria-live="assertive">
          {error}
        </Alert>
      )}

      {/* Messages display */}
      {!generatedDescription && (
        <Box role="log" aria-label="Conversation messages" aria-live="polite" aria-relevant="additions"
          sx={{ flex: 1, overflowY: 'auto', p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          {messages.map((message, index) => (
            <Box key={index} sx={{ display: 'flex', justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start' }}>
              <Paper elevation={1} sx={{ p: 2, maxWidth: '75%', bgcolor: message.role === 'user' ? 'primary.light' : 'grey.100', color: message.role === 'user' ? 'primary.contrastText' : 'text.primary' }}
                role="article" aria-label={`${message.role === 'user' ? 'Your message' : 'Chatbot message'} at ${new Date(message.timestamp).toLocaleTimeString()}`}>
                <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>{message.content}</Typography>
                <Typography variant="caption" sx={{ display: 'block', mt: 1, opacity: 0.7 }}>
                  {new Date(message.timestamp).toLocaleTimeString()}
                </Typography>
              </Paper>
            </Box>
          ))}
          {(isLoading || isGenerating) && (
            <Box sx={{ display: 'flex', justifyContent: 'flex-start' }} role="status" aria-live="polite" aria-label="Chatbot is thinking">
              <Paper elevation={1} sx={{ p: 2, bgcolor: 'grey.100' }}>
                <CircularProgress size={20} aria-hidden="true" />
                <Typography variant="body2" sx={{ ml: 1, display: 'inline' }}>
                  {isGenerating ? 'Generating summary...' : 'Thinking...'}
                </Typography>
              </Paper>
            </Box>
          )}
          <div ref={messagesEndRef} />
        </Box>
      )}

      {/* Description review and editing */}
      {generatedDescription && (
        <Box sx={{ flex: 1, overflowY: 'auto', p: 2 }} role="region" aria-label="Description review">
          <Typography variant="h6" gutterBottom id="description-heading">Comprehensive Description</Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Review and edit the generated description below. This will be used to match papers to your research interests.
          </Typography>
          <TextField fullWidth multiline rows={12} value={editedDescription}
            onChange={(e) => setEditedDescription(e.target.value)}
            placeholder="Enter comprehensive description..." sx={{ mt: 2, mb: 2 }}
            helperText={`${editedDescription.length}/5000 characters`}
            error={editedDescription.length > 5000}
            aria-label="Comprehensive research interest description"
            aria-describedby="description-heading"
            inputProps={{ 'aria-invalid': editedDescription.length > 5000 }}
          />
          {editedDescription.length > 5000 && (
            <Typography variant="caption" color="error" id="description-error" role="alert">
              Description exceeds maximum length of 5000 characters
            </Typography>
          )}
          <Stack direction="row" spacing={2} justifyContent="flex-end">
            <Button variant="outlined" onClick={handleCancelDescription} aria-label="Cancel and return to conversation">Back to Chat</Button>
            <Button variant="contained" onClick={handleSaveDescription}
              disabled={!editedDescription.trim() || editedDescription.length > 5000}
              aria-label="Save comprehensive description">
              Save Description
            </Button>
          </Stack>
        </Box>
      )}

      {/* Input area + Generate Summary button */}
      {!generatedDescription && (
        <>
          <Divider />
          {/* Generate Summary button — shown after enough conversation */}
          {canGenerate && !isGenerating && (
            <Box sx={{ px: 2, pt: 1.5, pb: 0 }}>
              <Button
                fullWidth
                variant={shouldConclude ? 'contained' : 'outlined'}
                color={shouldConclude ? 'success' : 'primary'}
                startIcon={<AutoAwesome />}
                onClick={handleGenerateDescription}
                disabled={isLoading || isGenerating}
                aria-label="Generate research interest summary"
                sx={{ mb: 1 }}
              >
                {shouldConclude
                  ? 'Generate Summary (Recommended)'
                  : `Generate Summary (${completedCount}/4 areas covered)`}
              </Button>
              {!shouldConclude && completedCount < 3 && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center', mb: 0.5 }}>
                  Keep chatting to cover more areas, or generate now with what you have
                </Typography>
              )}
            </Box>
          )}
          <Box sx={{ p: 2, pt: canGenerate ? 1 : 2 }} role="region" aria-label="Message input">
            <Stack direction="row" spacing={1}>
              <TextField
                fullWidth
                placeholder="Type your response..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isLoading || isGenerating}
                size="small"
                multiline
                maxRows={3}
                inputRef={inputRef}
                aria-label="Type your message to the chatbot"
                inputProps={{ 'aria-describedby': 'input-help-text' }}
              />
              <Button
                variant="contained"
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isLoading || isGenerating}
                endIcon={<Send />}
                sx={{ minWidth: '100px' }}
                aria-label="Send message to chatbot"
              >
                Send
              </Button>
            </Stack>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }} id="input-help-text">
              Press Enter to send, Shift+Enter for new line, Esc to close
            </Typography>
          </Box>
        </>
      )}

      {/* Delete confirmation dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}
        aria-labelledby="delete-dialog-title" aria-describedby="delete-dialog-description">
        <DialogTitle id="delete-dialog-title">Delete Conversation History?</DialogTitle>
        <DialogContent>
          <DialogContentText id="delete-dialog-description">
            This will permanently delete your conversation history and start a new conversation. This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} aria-label="Cancel deletion">Cancel</Button>
          <Button onClick={handleDeleteConversation} color="error" variant="contained" aria-label="Confirm deletion">Delete</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default ChatbotUI;
