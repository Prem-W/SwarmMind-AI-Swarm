# SwarmMind

**Enterprise Multi-Agent AI Orchestration Platform**

SwarmMind is a scalable platform where specialized AI agents collaborate autonomously to solve complex tasks. Built with enterprise-grade architecture, it features dynamic task decomposition, parallel agent execution, real-time monitoring, and human-in-the-loop approval.

## Features

- **Agent Swarm Orchestration** - Deploy multiple specialized agents that work together
- **Dynamic Task Decomposition** - AI-powered breakdown of complex objectives
- **Parallel Agent Execution** - Maximize throughput with dependency-aware parallelization
- **7 Agent Types** - Planner, Research, Coding, Reviewer, Testing, Memory, Tool
- **Real-Time Monitoring** - Live execution logs via WebSocket
- **Human Approval Mode** - Configurable checkpoints for critical decisions
- **Failure Recovery** - Automatic retry with exponential backoff
- **Team Workspaces** - Multi-tenant support with RBAC
- **Vector Memory** - Semantic search via Qdrant embeddings
- **REST API + WebSocket** - Full programmatic access

## Tech Stack

**Backend**
- Python 3.12 + FastAPI
- SQLAlchemy 2.0 + PostgreSQL 16
- Redis (Cache, Sessions, Message Broker)
- Qdrant (Vector Database)
- Celery (Background Tasks)
- OpenAI / Anthropic LLM Integration

**Frontend**
- React 19 + TypeScript
- Tailwind CSS + shadcn/ui
- Zustand (State Management)
- React Flow (Workflow Visualization)

**Infrastructure**
- Docker + Docker Compose
- GitHub Actions CI/CD
- Nginx Reverse Proxy

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.12+ (for local backend dev)

### Using Docker Compose

```bash
# Clone the repository
git clone <repository-url>
cd swarmmind

# Copy environment file
cp .env.example .env

# Edit .env with your API keys
# - OPENAI_API_KEY (required for LLM functionality)
# - ANTHROPIC_API_KEY (optional)

# Start all services
docker-compose up -d

# Initialize database
docker-compose exec backend alembic upgrade head

# Access the platform
# Frontend: http://localhost:5173
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Local Development

```bash
# --- Backend ---
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start services (PostgreSQL, Redis, Qdrant)
docker-compose up -d postgres redis qdrant

# Run database migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload

# Start Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# --- Frontend ---
cd frontend
npm install
npm run dev
```

## API Documentation

### Authentication
```bash
# Register
POST /api/v1/auth/register
{"email": "user@example.com", "password": "secure123", "full_name": "John Doe"}

# Login
POST /api/v1/auth/login
{"email": "user@example.com", "password": "secure123"}
```

### Agents
```bash
# List agents
GET /api/v1/agents?team_id=xxx&agent_type=coding

# Create agent
POST /api/v1/agents
{
  "name": "Code Assistant",
  "agent_type": "coding",
  "team_id": "xxx",
  "llm_model": "gpt-4o"
}

# Get agent
GET /api/v1/agents/{agent_id}
```

### Workflows
```bash
# List workflows
GET /api/v1/workflows

# Create workflow
POST /api/v1/workflows
{
  "name": "Code Review Pipeline",
  "team_id": "xxx",
  "max_parallel_agents": 5
}

# Execute workflow
POST /api/v1/workflows/{id}/execute
{"objective": "Review pull request #123"}
```

### Real-Time Logs (WebSocket)
```javascript
const ws = new WebSocket(
  'ws://localhost:8000/api/v1/ws/execution/{execution_id}?token={jwt}'
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data.event);
};
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed system design, data flow diagrams, and scalability patterns.

## Project Structure

```
swarmmind/
├── backend/                # Python FastAPI backend
│   ├── app/
│   │   ├── agents/        # Agent definitions (base + 7 types)
│   │   ├── api/           # REST API + WebSocket routes
│   │   ├── core/          # Config, security, logging, exceptions
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── services/      # LLM, memory, messaging, orchestrator
│   │   ├── tasks/         # Celery background tasks
│   │   └── main.py        # FastAPI application entry
│   ├── tests/             # Unit & integration tests
│   ├── alembic/           # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/              # React TypeScript frontend
│   ├── src/
│   │   ├── components/    # Layout, UI components
│   │   ├── pages/         # Dashboard, Agents, Workflows, etc.
│   │   ├── store/         # Zustand state management
│   │   └── App.tsx
│   └── Dockerfile
├── infra/                 # Infrastructure configs
│   ├── docker/           # Docker configurations
│   ├── nginx/            # Nginx reverse proxy
│   └── github/           # CI/CD workflows
├── docs/                  # Documentation
├── docker-compose.yml
└── README.md
```

## Testing

```bash
# Backend tests
cd backend
pytest tests/unit -v
pytest tests/integration -v

# Frontend tests
cd frontend
npm run test

# With coverage
pytest --cov=app tests/
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key | Required |
| `DATABASE_URL` | PostgreSQL connection | Required |
| `REDIS_URL` | Redis connection | Required |
| `OPENAI_API_KEY` | OpenAI API access | Required |
| `ANTHROPIC_API_KEY` | Anthropic API access | Optional |
| `QDRANT_HOST` | Vector DB host | localhost |
| `HUMAN_APPROVAL_MODE` | Enable approval gates | true |
| `MAX_RETRY_ATTEMPTS` | Task retry limit | 3 |

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests to the `develop` branch.
