# SwarmMind Architecture

## Overview

SwarmMind is a **multi-agent AI orchestration platform** where specialized AI agents collaborate autonomously to solve complex tasks. The architecture follows enterprise-grade patterns with clear separation of concerns, async processing, and horizontal scalability.

## System Architecture

```
                    +-------------------+
                    |   React Frontend  |
                    |  (Dashboard, UI)  |
                    +--------+----------+
                             |
                    +--------v----------+
                    |   Nginx / CDN     |
                    +--------+----------+
                             |
              +--------------v---------------+
              |      FastAPI Backend         |
              |  (REST API + WebSocket)      |
              +------+------------+----------+
                     |            |
          +----------v+  +--------v---------+
          |  PostgreSQL |  |     Redis       |
          |  (Metadata) |  |  (Cache/Queue)  |
          +----------+--+  +--------+--------+
                     |              |
          +----------v--+  +--------v---------+
          |   Qdrant     |  |  Celery Workers  |
          | (Vector DB)  |  |  (Background)    |
          +--------------+  +------------------+
                     |
          +----------v----------+
          |   LLM Providers     |
          | OpenAI / Anthropic  |
          +---------------------+
```

## Core Components

### 1. Agent Swarm Layer

The heart of SwarmMind. Each agent is a specialized entity with:
- **Dedicated LLM configuration** (model, temperature, system prompt)
- **Tool access** (code execution, APIs, file operations)
- **Memory access** (shared context via Qdrant + PostgreSQL)
- **Messaging capability** (Redis pub/sub for A2A communication)

**Agent Types:**
| Agent | Role |
|-------|------|
| Planner | Decomposes objectives into executable tasks |
| Research | Gathers and synthesizes information |
| Coding | Writes, reviews, and debugs code |
| Reviewer | Quality assurance and validation |
| Testing | Creates and runs test suites |
| Memory | Manages information retrieval and storage |
| Tool | Executes external APIs and tools |

### 2. Orchestration Engine

The `SwarmOrchestrator` manages:
- **Dynamic task decomposition** (Planner agent analyzes objectives)
- **Leader election** (selects coordinator agent based on capability + load)
- **Parallel execution** (respects task dependencies, maximizes parallelism)
- **Failure recovery** (retry with exponential backoff, agent reassignment)
- **Human approval gating** (configurable approval checkpoints)

### 3. Memory System

Two-tier memory architecture:
- **Short-term memory** (Redis): Fast access, TTL-based expiration
- **Long-term memory** (Qdrant + PostgreSQL): Vector embeddings for semantic search

### 4. Communication Layer

- **REST API**: Standard CRUD operations
- **WebSocket**: Real-time execution updates and live logs
- **Redis Pub/Sub**: Agent-to-agent messaging and broadcasts
- **Celery**: Asynchronous background task processing

## Data Flow

### Workflow Execution Flow

```
1. User creates workflow via API/Frontend
2. On execution trigger:
   a. Orchestrator receives workflow + execution request
   b. Planner agent decomposes objective into subtasks
   c. Leader agent is elected
   d. Tasks are assigned to specialized agents
   e. Agents execute in parallel (respecting dependencies)
   f. Real-time logs streamed via WebSocket
   g. Results collected and compiled
   h. Execution record updated
3. User views results via Dashboard
```

### Agent Communication Flow

```
Agent A (Research)          Redis Message Bus          Agent B (Coding)
     |                             |                           |
     |-- send_message(B, data) -->|                           |
     |                            |-- LPUSH B_queue --------->|
     |                            |-- PUBLISH B_channel ----->|
     |                            |                           |-- receive()
     |                            |<-- acknowledge() ---------|
```

## Database Schema

### Core Entities

```
users
  id (UUID PK)
  email, hashed_password, full_name
  role (super_admin/admin/member/viewer)
  is_active, last_login

teams
  id (UUID PK)
  name, slug, description
  max_agents, max_workflows

team_members
  id (UUID PK)
  team_id (FK), user_id (FK)
  role (owner/admin/member/viewer)

agents
  id (UUID PK)
  name, description, agent_type, status
  team_id (FK), owner_id (FK)
  llm_provider, llm_model, temperature, max_tokens
  system_prompt, tools, capabilities, config
  total_tasks_completed, total_tasks_failed

tasks
  id (UUID PK)
  title, description, status, priority
  assigned_agent_id (FK), workflow_id (FK)
  task_type, input_data, output_data
  retry_count, max_retries, execution_time_ms
  requires_approval, approved_by, approved_at

workflows
  id (UUID PK)
  name, description, status, version
  owner_id (FK), team_id (FK)
  input_data, output_data, config, schedule
  max_parallel_agents, enable_dynamic_agents
  enable_failure_recovery, require_human_approval

executions
  id (UUID PK)
  workflow_id (FK), status
  triggered_by, trigger_user_id
  started_at, completed_at, total_duration_ms
  input_snapshot, output_snapshot, metrics
  agent_ids, leader_agent_id

execution_logs
  id (UUID PK)
  execution_id (FK), agent_id, task_id
  timestamp, level, event_type, message, details

memory_entries
  id (UUID PK)
  content, memory_type
  agent_id, team_id, task_id, execution_id
  embedding_id, embedding_model
  importance, access_count, tags, metadata, expires_at
```

## Scalability Design

### Horizontal Scaling
- **Stateless API servers** behind load balancer
- **Celery workers** scale independently based on queue depth
- **PostgreSQL** read replicas for query scaling
- **Redis Cluster** for cache/session scaling
- **Qdrant** distributed mode for vector search scaling

### Performance Optimizations
- Async database queries via SQLAlchemy asyncio
- Connection pooling (PostgreSQL: 20, Redis: 50)
- Response caching for frequently accessed data
- Streaming responses for large payloads
- Batch processing for bulk operations

## Security Architecture

- **JWT-based authentication** with refresh token rotation
- **Role-based access control** (RBAC) at team level
- **API key management** for service-to-service auth
- **Input validation** via Pydantic schemas
- **SQL injection prevention** via parameterized queries (ORM)
- **CORS** configured for frontend origin only
- **Request logging** for audit trails
