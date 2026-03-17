import React, { useState, useEffect } from 'react';
import { Journal } from '../types';
import { journalsAPI } from '../services/api';
import {
  Container,
  Typography,
  Box,
  Paper,
  TextField,
  Button,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  Alert,
  CircularProgress
} from '@mui/material';
import { Delete, Add } from '@mui/icons-material';

const JournalManagementPage: React.FC = () => {
  const [journals, setJournals] = useState<Journal[]>([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [newJournalName, setNewJournalName] = useState('');
  const [newJournalUrl, setNewJournalUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load journals on mount
  useEffect(() => {
    loadJournals();
  }, []);

  const loadJournals = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await journalsAPI.getAll();
      setJournals(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load journals');
      console.error('Error loading journals:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddJournal = async () => {
    if (newJournalName && newJournalUrl) {
      try {
        setError(null);
        const newJournal = await journalsAPI.create({
          name: newJournalName,
          platform: 'IEEE', // Auto-detect in real app
          url: newJournalUrl
        });
        setJournals([...journals, newJournal]);
        setNewJournalName('');
        setNewJournalUrl('');
        setOpenDialog(false);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to add journal');
        console.error('Error adding journal:', err);
      }
    }
  };

  const handleRemoveJournal = async (id: string) => {
    try {
      setError(null);
      await journalsAPI.delete(id);
      setJournals(journals.filter(j => j.id !== id));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete journal');
      console.error('Error deleting journal:', err);
    }
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4">
            Monitored Journals
          </Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setOpenDialog(true)}
          >
            Add Journal
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Paper elevation={2}>
            <List>
              {journals.map((journal, index) => (
                <ListItem
                  key={journal.id}
                  divider={index < journals.length - 1}
                  secondaryAction={
                    <IconButton edge="end" onClick={() => handleRemoveJournal(journal.id)}>
                      <Delete />
                    </IconButton>
                  }
                >
                  <ListItemText
                    primary={journal.name}
                    secondary={
                      <Box sx={{ mt: 1 }}>
                        <Chip label={journal.platform} size="small" sx={{ mr: 1 }} />
                        <Typography variant="caption" color="text.secondary">
                          Added: {new Date(journal.addedAt).toLocaleDateString()}
                        </Typography>
                      </Box>
                    }
                  />
                </ListItem>
              ))}
              {journals.length === 0 && (
                <ListItem>
                  <ListItemText
                    primary="No journals added yet"
                    secondary="Click 'Add Journal' to start monitoring"
                  />
                </ListItem>
              )}
            </List>
          </Paper>
        )}
      </Box>

      {/* Add Journal Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add New Journal</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Journal Name"
            value={newJournalName}
            onChange={(e) => setNewJournalName(e.target.value)}
            margin="normal"
            placeholder="e.g., IEEE Transactions on Electromagnetic Compatibility"
          />
          <TextField
            fullWidth
            label="Journal URL"
            value={newJournalUrl}
            onChange={(e) => setNewJournalUrl(e.target.value)}
            margin="normal"
            placeholder="https://ieeexplore.ieee.org/..."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleAddJournal} variant="contained">
            Add
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default JournalManagementPage;
