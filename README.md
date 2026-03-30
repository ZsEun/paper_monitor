# Academic Journal Monitor

A web application that monitors academic journals (IEEE Xplore) for new publications, classifies papers by topic using AI, and generates personalized weekly digests filtered by your research interests.

## Features

- **Journal Monitoring** — Track multiple IEEE Xplore journals. Papers are fetched via Selenium headless browser scraping.
- **AI-Powered Topic Classification** — Papers are classified into research topics using AWS Bedrock (Claude).
- **Personalized Digest Filtering** — Define research interest topics and receive digests containing only relevant papers, evaluated by AI semantic matching.
- **Interest Definition Chatbot** — An AI chatbot guides you through articulating your research interests in detail, improving relevance matching accuracy.
- **Weekly Digests** — Auto-generated summaries organized by topic with AI-written paper summaries.
- **Import/Export** — Back up and share your interest topic profiles as JSON.

## Architecture

```
literature_boot/
├── backend/          # FastAPI Python backend
│   ├── app/
│   │   ├── api/          # REST endpoints (auth, journals, digests, interests)
│   │   ├── scrapers/     # IEEE Xplore scrapers (Selenium + HTML fallback)
│   │   ├── services/     # AI service, chatbot, relevance evaluator
│   │   ├── models/       # Pydantic schemas
│   │   └── utils/        # Storage (local JSON), security (JWT)
│   └── data/             # Local JSON file storage
├── frontend/         # React TypeScript frontend (Material UI)
│   └── src/
│       ├── pages/        # Dashboard, Journals, Settings, Digests
│       ├── components/   # ChatbotUI
│       └── services/     # API client, auth context
└── infra/            # AWS CDK (optional cloud deployment)
```

## Prerequisites

- Python 3.9+
- Node.js 16+
- Google Chrome (for Selenium journal scraping)
- AWS account with Bedrock access (for AI features)

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure AWS credentials for Bedrock
cp .env.example .env
# Edit .env with your AWS credentials, or run: aws configure

# Start the server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API runs at http://127.0.0.1:8000.

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

The app opens at http://localhost:3000.

### 3. Usage

1. Register an account and log in
2. Go to **Journals** → Add an IEEE Xplore journal URL (e.g., `https://ieeexplore.ieee.org/xpl/mostRecentIssue.jsp?punumber=22`)
3. Go to **Settings** → Add research interest topics and use the AI chatbot to define them in detail
4. Go to **Dashboard** → Generate a digest to fetch and filter papers

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login |
| GET | `/api/journals` | List monitored journals |
| POST | `/api/journals` | Add journal |
| PUT | `/api/journals/{id}` | Update journal |
| DELETE | `/api/journals/{id}` | Remove journal |
| POST | `/api/digests/generate` | Generate digest |
| GET | `/api/digests/latest` | Get latest digest |
| GET | `/api/digests` | List all digests |
| GET | `/api/user/interests` | List interest topics |
| POST | `/api/user/interests` | Add interest topic |
| PUT | `/api/user/interests/{id}` | Update topic |
| DELETE | `/api/user/interests/{id}` | Delete topic |
| POST | `/api/user/interests/{id}/chat` | Send chatbot message |
| POST | `/api/user/interests/export` | Export topics as JSON |
| POST | `/api/user/interests/import` | Import topics from JSON |

## How Paper Fetching Works

The scraper uses a cascading fallback strategy:

1. **Selenium** (primary) — Headless Chrome renders the JavaScript-heavy IEEE Xplore pages, extracts paper metadata from listing pages with pagination, then fetches abstracts from individual paper detail pages.
2. **HTML scraping** (fallback) — Plain HTTP + BeautifulSoup if Chrome is unavailable. Limited to whatever the server returns without JS rendering.
3. **Mock data** (last resort) — Returns a system message explaining the limitation.

## Data Storage

Local mode uses JSON files in `backend/data/`. The storage layer also supports DynamoDB for cloud deployment (controlled by `STORAGE_BACKEND` env var).

## License

MIT
