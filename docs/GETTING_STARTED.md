# Getting Started

## Prerequisites
- Python 3.11+
- Node.js 18+
- Docker Desktop
- Poetry

## Setup

### 1. Start Infrastructure
```bash
cd infrastructure/docker
docker-compose up -d
```

### 2. Start Backend
```bash
cd backend
poetry install
poetry run python -m app.main
```

### 3. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

## Access
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/docs
- RabbitMQ Management: http://localhost:15672 (admin/admin)