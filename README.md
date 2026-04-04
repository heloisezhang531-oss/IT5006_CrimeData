# Crime Intelligence Platform (FastAPI + Next.js)

This repository has been restructured from Streamlit into a two-tier architecture:

- `backend/`: FastAPI service for EDA, risk forecasting, anomaly, hardship context, performance, and model-lab APIs
- `frontend/`: Next.js (React + TypeScript) Apple-style storytelling dashboard and command center

## Modules

- Strategic trend monitoring
- Operational deployment
- Crime-type specific action
- Early warning / anomaly detection
- Socioeconomic-context monitoring
- Performance and accountability
- Command center dashboard
- Model lab (ablation + generalization + reliability)

## Run with Docker Compose

1. Copy environment template:

```bash
cp .env.example .env
```

2. Fill in `TIDB_*` if available.

3. Start services:

```bash
docker compose up --build
```

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend: [http://localhost:8000/api/health](http://localhost:8000/api/health)

Map rendering uses **Leaflet + OpenStreetMap** and does **not** require any token.

## Local Run (without Docker)

### Backend

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Data Source Mode

Backend supports `DATA_SOURCE_MODE`:

- `hybrid` (default): query TiDB first, fallback to cache
- `tidb`: query TiDB only
- `cache`: serve cached/fallback JSON only

Cache files are stored under `data_cache/`.

## Worklog Protocol

Every completed API module and page module must append one entry into `WORKLOG.md`:

- Time (Asia/Shanghai)
- Module
- Changes
- Validation
- Risk/TODO

This protocol is mandatory for acceptance.
