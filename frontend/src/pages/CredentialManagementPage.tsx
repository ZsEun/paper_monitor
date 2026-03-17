import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Paper,
  Box,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Chip,
  CircularProgress,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import { credentialsAPI, journalsAPI } from '../services/api';
import { Credential, Journal } from '../types';

const CredentialManagementPage: React.FC = () => {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [journals, setJournals] = useState<Journal[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedJournal, setSelectedJournal] = useState('');
  const [credentialType, setCredentialType] = useState<'username_password' | 'api_key' | 'token'>('username_password');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [creds, jrnls] = await Promise.all([
          credentialsAPI.getAll(),
          journalsAPI.getAll(),
        ]);
        setCredentials(creds);
        setJournals(jrnls);
      } catch (err) {
        console.error('Failed to load data:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleAddCredential = async () => {
    if (!selectedJournal || !username || !password) {
      alert('Please fill in all fields');
      return;
    }

    const journal = journals.find(j => j.id === selectedJournal);
    if (!journal) return;

    try {
      const newCred = await credentialsAPI.create({
        journalId: selectedJournal,
        journalName: journal.name,
        username,
        password,
        credentialType,
      });
      setCredentials([...credentials, newCred]);
      setSelectedJournal('');
      setUsername('');
      setPassword('');
    } catch (err) {
      console.error('Failed to add credential:', err);
      alert('Failed to add credential');
    }
  };

  const handleDeleteCredential = async (id: string) => {
    try {
      await credentialsAPI.delete(id);
      setCredentials(credentials.filter(cred => cred.id !== id));
    } catch (err) {
      console.error('Failed to delete credential:', err);
      alert('Failed to delete credential');
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
      <Typography variant="h4" gutterBottom>
        Credential Management
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Add New Credential
        </Typography>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <FormControl fullWidth>
            <InputLabel>Journal</InputLabel>
            <Select
              value={selectedJournal}
              label="Journal"
              onChange={(e) => setSelectedJournal(e.target.value)}
            >
              {journals.map(journal => (
                <MenuItem key={journal.id} value={journal.id}>
                  {journal.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth>
            <InputLabel>Credential Type</InputLabel>
            <Select
              value={credentialType}
              label="Credential Type"
              onChange={(e) => setCredentialType(e.target.value as any)}
            >
              <MenuItem value="username_password">Username & Password</MenuItem>
              <MenuItem value="api_key">API Key</MenuItem>
              <MenuItem value="token">Token</MenuItem>
            </Select>
          </FormControl>

          <TextField
            fullWidth
            label="Username / API Key"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

          <TextField
            fullWidth
            type="password"
            label="Password / Token"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <Button variant="contained" onClick={handleAddCredential}>
            Add Credential
          </Button>
        </Box>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Saved Credentials
        </Typography>

        {credentials.length === 0 ? (
          <Typography color="text.secondary">No credentials saved yet.</Typography>
        ) : (
          <List>
            {credentials.map((cred) => (
              <ListItem
                key={cred.id}
                secondaryAction={
                  <IconButton edge="end" onClick={() => handleDeleteCredential(cred.id)}>
                    <DeleteIcon />
                  </IconButton>
                }
              >
                <ListItemText
                  primary={cred.journalName}
                  secondary={
                    <Box sx={{ mt: 1 }}>
                      <Chip label={cred.credentialType.replace('_', ' ')} size="small" sx={{ mr: 1 }} />
                      <Typography variant="caption" color="text.secondary">
                        {cred.maskedValue}
                      </Typography>
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
      </Paper>
    </Container>
  );
};

export default CredentialManagementPage;
