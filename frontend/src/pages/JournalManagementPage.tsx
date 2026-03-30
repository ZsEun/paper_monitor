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
  CircularProgress,
  Tooltip
} from '@mui/material';
import { Delete, Add, Edit, OpenInNew } from '@mui/icons-material';

const JournalManagementPage: React.FC = () => {
  const [journals, setJournals] = useState<Journal[]>([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingJournal, setEditingJournal] = useState<Journal | null>(null);
  const [journalName, setJournalName] = useState('');
  const [journalUrl, setJournalUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    } finally {
      setLoading(false);
    }
  };

  const openAddDialog = () => {
    setEditingJournal(null);
    setJournalName('');
    setJournalUrl('');
    setOpenDialog(true);
  };

  const openEditDialog = (journal: Journal) => {
    setEditingJournal(journal);
    setJournalName(journal.name);
    setJournalUrl(journal.url);
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setEditingJournal(null);
    setJournalName('');
    setJournalUrl('');
  };

  const handleSaveJournal = async () => {
    if (!journalName || !journalUrl) return;
    try {
      setError(null);
      if (editingJournal) {
        const updated = await journalsAPI.update(editingJournal.id, {
          name: journalName,
          platform: editingJournal.platform,
          url: journalUrl,
        });
        setJournals(journals.map(j => j.id === updated.id ? updated : j));
      } else {
        const newJournal = await journalsAPI.create({
          name: journalName,
          platform: 'IEEE',
          url: journalUrl,
        });
        setJournals([...journals, newJournal]);
      }
      handleCloseDialog();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save journal');
    }
  };

  const handleRemoveJournal = async (id: string) => {
    try {
      setError(null);
      await journalsAPI.delete(id);
      setJournals(journals.filter(j => j.id !== id));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete journal');
    }
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4">Monitored Journals</Typography>
          <Button variant="contained" startIcon={<Add />} onClick={openAddDialog}>
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
                    <Box>
                      <Tooltip title="Visit journal">
                        <IconButton
                          edge="end"
                          onClick={() => window.open(journal.url, '_blank', 'noopener,noreferrer')}
                          sx={{ mr: 0.5 }}
                          aria-label={`Visit ${journal.name}`}
                        >
                          <OpenInNew />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Edit journal">
                        <IconButton
                          edge="end"
                          onClick={() => openEditDialog(journal)}
                          sx={{ mr: 0.5 }}
                          aria-label={`Edit ${journal.name}`}
                        >
                          <Edit />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete journal">
                        <IconButton
                          edge="end"
                          onClick={() => handleRemoveJournal(journal.id)}
                          aria-label={`Delete ${journal.name}`}
                        >
                          <Delete />
                        </IconButton>
                      </Tooltip>
                    </Box>
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

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingJournal ? 'Edit Journal' : 'Add New Journal'}</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Journal Name"
            value={journalName}
            onChange={(e) => setJournalName(e.target.value)}
            margin="normal"
            placeholder="e.g., IEEE Transactions on Electromagnetic Compatibility"
          />
          <TextField
            fullWidth
            label="Journal URL"
            value={journalUrl}
            onChange={(e) => setJournalUrl(e.target.value)}
            margin="normal"
            placeholder="https://ieeexplore.ieee.org/..."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSaveJournal} variant="contained">
            {editingJournal ? 'Save' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default JournalManagementPage;
