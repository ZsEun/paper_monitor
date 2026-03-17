export interface User {
  id: string;
  email: string;
  name: string;
}

export interface Journal {
  id: string;
  name: string;
  platform: string;
  url: string;
  addedAt: string;
  isSubscribed?: boolean;
}

export interface Credential {
  id: string;
  journalId: string;
  journalName: string;
  username: string;
  addedAt: string;
  credentialType: 'username_password' | 'api_key' | 'token';
  maskedValue: string;
}

export interface Paper {
  id: string;
  title: string;
  authors: string[];
  abstract: string;
  aiSummary?: string;  // AI-generated summary (max 100 words)
  url: string;
  publishedDate: string;
  journalId: string;
  topics: string[];
}

export interface TopicGroup {
  topic: string;
  paperCount: number;
  papers: Paper[];
}

export interface EvaluationMetadata {
  totalPapersEvaluated: number;
  relevantPapersIncluded: number;
  evaluationErrors: number;
  hadInterestTopics: boolean;
  evaluationTimestamp: string;
}

export interface PaperMatch {
  paperId: string;
  matchingTopics: string[];
}

export interface Digest {
  id: string;
  generatedAt: string;
  startDate: string;
  endDate: string;
  papers: Paper[];
  papersByTopic: { [topic: string]: Paper[] };
  topicGroups: TopicGroup[];
  evaluationMetadata?: EvaluationMetadata;
  paperMatches?: PaperMatch[];
}

export interface InterestTopic {
  id: string;
  userId: string;
  topicText: string;
  createdAt: string;
  updatedAt: string;
  comprehensiveDescription?: string;
  conversationStatus?: 'not_started' | 'in_progress' | 'completed';
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatbotResponse {
  message: string;
  shouldConclude: boolean;
  conversationStatus: 'not_started' | 'in_progress' | 'completed';
}

export interface InterestTopicCreate {
  topicText: string;
}

export interface InterestTopicUpdate {
  topicText: string;
}

export interface ImportResult {
  topicsAdded: number;
  topicsSkipped: number;
  duplicates: string[];
}
