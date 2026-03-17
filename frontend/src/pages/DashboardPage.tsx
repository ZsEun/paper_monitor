import React, { useState, useEffect } from 'react';
import { Container, Typography, Paper, Box, Stack, CircularProgress, Button, Alert } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../services/AuthContext';
import { digestsAPI, journalsAPI } from '../services/api';
import { Digest, Journal } from '../types';

const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [latestDigest, setLatestDigest] = useState<Digest | null>(null);
  const [digestHistory, setDigestHistory] = useState<Digest[]>([]);
  const [journals, setJournals] = useState<Journal[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const fetchData = async () => {
    try {
      const [digest, digests, journalsList] = await Promise.all([
        digestsAPI.getLatest().catch(() => null),
        digestsAPI.getAll().catch(() => []),
        journalsAPI.getAll().catch(() => []),
      ]);
      
      setLatestDigest(digest);
      setDigestHistory(digests);
      setJournals(journalsList);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleGenerateDigest = async () => {
    setGenerating(true);
    setMessage(null);
    
    try {
      const newDigest = await digestsAPI.generate();
      setMessage({ type: 'success', text: 'Digest generated successfully!' });
      
      // Refresh data
      await fetchData();
    } catch (error: any) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Failed to generate digest. Please add journals first.' 
      });
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  const subscribedJournals = journals.filter(j => j.isSubscribed);

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          Welcome back, {user?.name}!
        </Typography>
        <Button
          variant="contained"
          startIcon={generating ? <CircularProgress size={20} color="inherit" /> : <RefreshIcon />}
          onClick={handleGenerateDigest}
          disabled={generating}
        >
          {generating ? 'Generating...' : 'Generate New Digest'}
        </Button>
      </Box>

      {message && (
        <Alert severity={message.type} sx={{ mb: 3 }} onClose={() => setMessage(null)}>
          {message.text}
        </Alert>
      )}

      <Stack spacing={3}>
        {/* Statistics Cards */}
        <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
          <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 200px' }}>
            <Typography variant="h3" color="primary">
              {subscribedJournals.length}
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Subscribed Journals
            </Typography>
          </Paper>

          <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 200px' }}>
            <Typography variant="h3" color="primary">
              {latestDigest?.papers.length || 0}
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Papers This Week
            </Typography>
          </Paper>

          <Paper sx={{ p: 3, textAlign: 'center', flex: '1 1 200px' }}>
            <Typography variant="h3" color="primary">
              {digestHistory.length}
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Total Digests
            </Typography>
          </Paper>
        </Box>

        {/* Latest Digest Preview */}
        {latestDigest && (
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Box>
                <Typography variant="h5" gutterBottom>
                  Latest Digest
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {new Date(latestDigest.generatedAt).toLocaleDateString()}
                </Typography>
              </Box>
              <Button 
                variant="outlined" 
                onClick={() => navigate(`/digest/${latestDigest.id}`)}
              >
                View Full Digest
              </Button>
            </Box>
            
            <Box sx={{ mt: 2 }}>
              {(() => {
                // Reorganize by interest topics if available
                if (latestDigest.paperMatches && latestDigest.paperMatches.length > 0) {
                  const papersByInterestTopic: { [topic: string]: any[] } = {};
                  
                  latestDigest.paperMatches.forEach(match => {
                    const paper = latestDigest.papers.find(p => p.id === match.paperId);
                    if (paper) {
                      match.matchingTopics.forEach(topic => {
                        if (!papersByInterestTopic[topic]) {
                          papersByInterestTopic[topic] = [];
                        }
                        if (!papersByInterestTopic[topic].find(p => p.id === paper.id)) {
                          papersByInterestTopic[topic].push(paper);
                        }
                      });
                    }
                  });
                  
                  return Object.entries(papersByInterestTopic).map(([topic, papers]) => (
                    <Box key={topic} sx={{ mb: 2 }}>
                      <Typography variant="h6" color="secondary" sx={{ textTransform: 'capitalize' }}>
                        {topic} ({papers.length} papers)
                      </Typography>
                      <ul>
                        {papers.slice(0, 3).map(paper => (
                          <li key={paper.id}>
                            <Typography variant="body2">{paper.title}</Typography>
                          </li>
                        ))}
                        {papers.length > 3 && (
                          <li>
                            <Typography variant="body2" color="text.secondary">
                              ...and {papers.length - 3} more
                            </Typography>
                          </li>
                        )}
                      </ul>
                    </Box>
                  ));
                } else {
                  // Fallback to AI-extracted topics
                  return Object.entries(latestDigest.papersByTopic).map(([topic, papers]) => (
                    <Box key={topic} sx={{ mb: 2 }}>
                      <Typography variant="h6" color="primary">
                        {topic} ({papers.length} papers)
                      </Typography>
                      <ul>
                        {papers.slice(0, 3).map(paper => (
                          <li key={paper.id}>
                            <Typography variant="body2">{paper.title}</Typography>
                          </li>
                        ))}
                      </ul>
                    </Box>
                  ));
                }
              })()}
            </Box>
          </Paper>
        )}

        {/* Subscribed Journals */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>
            Your Subscribed Journals
          </Typography>
          {subscribedJournals.length === 0 ? (
            <Typography color="text.secondary">No journals subscribed yet.</Typography>
          ) : (
            <Box sx={{ mt: 2 }}>
              {subscribedJournals.map(journal => (
                <Box key={journal.id} sx={{ mb: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  <Typography variant="h6">{journal.name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {journal.platform}
                  </Typography>
                </Box>
              ))}
            </Box>
          )}
        </Paper>
      </Stack>
    </Container>
  );
};

export default DashboardPage;
