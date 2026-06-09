# AI Kubernetes Agent

On-demand Kubernetes troubleshooting system powered by AI.

## Architecture

```text
Frontend → FastAPI Backend → Kubernetes Investigation → AI Reasoning → Diagnosis
```

## Project Structure

```text
ai-kubernetes-agent/
├── backend/          # FastAPI orchestrator
├── frontend/         # Next.js UI
├── docs/             # Documentation
├── prompts/          # AI prompt templates
├── docker-compose.yml
└── README.md
```

## Quick Start

### Prerequisites

- Docker and Docker Compose

### Run with Docker (local UI only — no GKE)

```bash
docker compose up --build
```

Access:

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/health

### Run with GKE (pipeline-demo VM)

The kubeconfig and `gke-gcloud-auth-plugin` credentials live on the GCP VM, not on Windows.

```bash
docker compose -f docker-compose.yml -f docker-compose.gke.yml up --build
```

See [docs/gke-deployment.md](docs/gke-deployment.md) for full setup and troubleshooting.

### Local Development (without Docker)

**Backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | OpenRouter API key (future) |
| `OPENROUTER_MODEL` | LLM model name (future) |
| `KUBECONFIG_PATH` | Path to kubeconfig (future) |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend API URL (default: `http://localhost:8000`) |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |

## Status

Foundation setup complete. Kubernetes investigation and AI reasoning are not yet implemented.
