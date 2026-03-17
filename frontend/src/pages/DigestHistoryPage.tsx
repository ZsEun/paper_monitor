import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { digestsAPI } from '../services/api';
import { Digest } from '../types';
import {
  Container,
  Typography,
  Box,
  Paper,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Chip,
  CircularProgress,
  Alert
} from '@mui/material';

const DigestHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [digests, setDigests] = useState<Digest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDigests();
  }, []);

  const loadDigests = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await digestsAPI.getAll();
      setDigests(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load digests');
      console.error('Error loading digests:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ mt: 4, mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Digest History
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" sx={{ mb: 3 }}>
          View your past weekly summaries
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : digests.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography color="text.secondary">
              No digests generated yet. Go to the Dashboard to generate your first digest!
            </Typography>
          </Paper>
        ) : (
          <Paper elevation={2}>
            <List>
              {digests.map((digest, index) => {
                const totalPapers = digest.topicGroups.reduce((sum, g) => sum + g.paperCount, 0);
                return (
                  <ListItem key={digest.id} divider={index < digests.length - 1} disablePadding>
                    <ListItemButton onClick={() => navigate(`/digest/${digest.id}`)}>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="h6">
                              {new Date(digest.startDate).toLocaleDateString()} - {new Date(digest.endDate).toLocaleDateString()}
                            </Typography>
                            <Chip label={`${totalPapers} papers`} size="small" color="primary" />
                          </Box>
                        }
                        secondary={
                          <Box sx={{ mt: 1 }}>
                            <Typography variant="body2" color="text.secondary">
                              Generated: {new Date(digest.generatedAt).toLocaleDateString()}
                            </Typography>
                            <Box sx={{ mt: 0.5 }}>
                              {digest.topicGroups.map(group => (
                                <Chip
                                  key={group.topic}
                                  label={`${group.topic}: ${group.paperCount}`}
                                  size="small"
                                  variant="outlined"
                                  sx={{ mr: 0.5, mt: 0.5 }}
                                />
                              ))}
                            </Box>
                          </Box>
                        }
                      />
                    </ListItemButton>
                  </ListItem>
                );
              })}
            </List>
          </Paper>
        )}
      </Box>
    </Container>
  );
};

export default DigestHistoryPage;
