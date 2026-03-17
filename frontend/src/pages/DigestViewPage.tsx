import React, { useState, useEffect } from 'react';
import { Container, Typography, Paper, Box, Chip, Link, Divider, CircularProgress, Alert, Accordion, AccordionSummary, AccordionDetails, Button } from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import InfoIcon from '@mui/icons-material/Info';
import SettingsIcon from '@mui/icons-material/Settings';
import { digestsAPI } from '../services/api';
import { Digest, Paper as PaperType } from '../types';

const DigestViewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [digest, setDigest] = useState<Digest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDigest();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const loadDigest = async () => {
    if (!id) return;
    
    try {
      setLoading(true);
      setError(null);
      const data = await digestsAPI.getById(id);
      setDigest(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load digest');
      console.error('Error loading digest:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error || !digest) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error">
          {error || 'Digest not found'}
        </Alert>
      </Container>
    );
  }

  // Reorganize papers by matching interest topics when available
  const papersByInterestTopic: { [topic: string]: PaperType[] } = {};
  
  if (digest.paperMatches && digest.paperMatches.length > 0) {
    // Group papers by their matching interest topics
    digest.paperMatches.forEach(match => {
      const paper = digest.papers.find(p => p.id === match.paperId);
      if (paper) {
        match.matchingTopics.forEach(topic => {
          if (!papersByInterestTopic[topic]) {
            papersByInterestTopic[topic] = [];
          }
          // Avoid duplicates
          if (!papersByInterestTopic[topic].find(p => p.id === paper.id)) {
            papersByInterestTopic[topic].push(paper);
          }
        });
      }
    });
  }

  const hasInterestTopicGroups = Object.keys(papersByInterestTopic).length > 0;

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Weekly Digest
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" gutterBottom>
          {new Date(digest.startDate).toLocaleDateString()} - {new Date(digest.endDate).toLocaleDateString()}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Generated on {new Date(digest.generatedAt).toLocaleDateString()}
        </Typography>

        {/* Alert when user has no interest topics defined */}
        {digest.evaluationMetadata && digest.evaluationMetadata.hadInterestTopics === false && (
          <Alert 
            severity="info" 
            sx={{ mb: 3 }}
            action={
              <Button 
                color="inherit" 
                size="small" 
                startIcon={<SettingsIcon />}
                onClick={() => navigate('/settings')}
              >
                Set up interest topics
              </Button>
            }
          >
            Set up interest topics to receive personalized digests with only papers relevant to your research
          </Alert>
        )}

        {/* Evaluation metadata section */}
        {digest.evaluationMetadata && (
          <Accordion sx={{ mb: 3 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <InfoIcon color="action" />
                <Typography variant="h6">Evaluation Statistics</Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Box>
                <Typography variant="body1" sx={{ mb: 1 }}>
                  <strong>Total papers evaluated:</strong> {digest.evaluationMetadata.totalPapersEvaluated}
                </Typography>
                <Typography variant="body1" sx={{ mb: 1 }}>
                  <strong>Relevant papers included:</strong> {digest.evaluationMetadata.relevantPapersIncluded}
                </Typography>
                {digest.evaluationMetadata.evaluationErrors > 0 && (
                  <Typography variant="body1" color="warning.main" sx={{ mb: 1 }}>
                    <strong>Evaluation errors:</strong> {digest.evaluationMetadata.evaluationErrors}
                  </Typography>
                )}
                {digest.evaluationMetadata.relevantPapersIncluded === 0 && digest.evaluationMetadata.hadInterestTopics && (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    No papers matched your interest topics this week
                  </Alert>
                )}
              </Box>
            </AccordionDetails>
          </Accordion>
        )}

        {/* Display papers grouped by interest topics if available */}
        {hasInterestTopicGroups ? (
          Object.entries(papersByInterestTopic).map(([topic, papers]) => (
            <Paper key={topic} elevation={2} sx={{ p: 3, mb: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Typography variant="h5" sx={{ mr: 2, textTransform: 'capitalize' }}>
                  {topic}
                </Typography>
                <Chip label={`${papers.length} paper${papers.length !== 1 ? 's' : ''}`} color="secondary" />
              </Box>

              <Divider sx={{ mb: 2 }} />

              {papers.map((paper, index) => (
                <Box key={paper.id} sx={{ mb: 3 }}>
                  <Link
                    href={paper.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    underline="hover"
                    sx={{ fontSize: '1.1rem', fontWeight: 500 }}
                  >
                    {paper.title}
                  </Link>

                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {paper.authors.join(', ')} • {new Date(paper.publishedDate).toLocaleDateString()}
                  </Typography>
                  <Typography variant="body1" sx={{ mt: 1, whiteSpace: 'pre-line' }}>
                    {paper.aiSummary || paper.abstract}
                  </Typography>
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
                      Topics:
                    </Typography>
                    {paper.topics.map((t: string) => (
                      <Chip key={t} label={t} size="small" variant="outlined" sx={{ mr: 0.5 }} />
                    ))}
                  </Box>
                  {index < papers.length - 1 && <Divider sx={{ mt: 2 }} />}
                </Box>
              ))}
            </Paper>
          ))
        ) : (
          /* Fallback to AI-extracted topic groups when no interest topics */
          digest.topicGroups.map((group) => (
            <Paper key={group.topic} elevation={2} sx={{ p: 3, mb: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Typography variant="h5" sx={{ mr: 2 }}>
                  {group.topic}
                </Typography>
                <Chip label={`${group.paperCount} papers`} color="primary" />
              </Box>

              <Divider sx={{ mb: 2 }} />

              {group.papers.map((paper, index) => (
                <Box key={paper.id} sx={{ mb: 3 }}>
                  <Link
                    href={paper.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    underline="hover"
                    sx={{ fontSize: '1.1rem', fontWeight: 500 }}
                  >
                    {paper.title}
                  </Link>

                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {paper.authors.join(', ')} • {new Date(paper.publishedDate).toLocaleDateString()}
                  </Typography>
                  <Typography variant="body1" sx={{ mt: 1, whiteSpace: 'pre-line' }}>
                    {paper.aiSummary || paper.abstract}
                  </Typography>
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
                      Topics:
                    </Typography>
                    {paper.topics.map((topic: string) => (
                      <Chip key={topic} label={topic} size="small" variant="outlined" sx={{ mr: 0.5 }} />
                    ))}
                  </Box>
                  {index < group.papers.length - 1 && <Divider sx={{ mt: 2 }} />}
                </Box>
              ))}
            </Paper>
          ))
        )}
      </Box>
    </Container>
  );
};

export default DigestViewPage;
