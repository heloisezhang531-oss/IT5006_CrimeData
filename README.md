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

### Cache Tuning

You can tune API/frontend cache behavior via environment variables:

- `API_CACHE_TTL_SECONDS` (default `300`): in-memory TTL cache in FastAPI provider
- `API_CACHE_MAX_ENTRIES` (default `512`): max in-memory cache key count in provider
- `API_RESPONSE_CACHE_MAX_AGE` (default `60`): HTTP `Cache-Control` max-age for GET API responses
- `API_SERVER_REVALIDATE_SECONDS` (default `60`): Next.js server-side `fetch` revalidate window
- `NEXT_PUBLIC_API_CLIENT_CACHE_TTL_MS` (default `15000`): browser-side GET response TTL for `frontend/lib/api.ts`

## Worklog Protocol

Every completed API module and page module must append one entry into `WORKLOG.md`:

- Time (Asia/Shanghai)
- Module
- Changes
- Validation
- Risk/TODO

This protocol is mandatory for acceptance.

## Outcomes
<img width="777" height="326" alt="image" src="https://github.com/user-attachments/assets/69b0a2c4-a51b-4a3b-ad4b-c95ce2d0766b" />
<img width="778" height="412" alt="image" src="https://github.com/user-attachments/assets/21fb9cdd-81bd-4495-91cd-a51fd73314c6" />
<img width="1933" height="653" alt="image" src="https://github.com/user-attachments/assets/8e4fd919-2f32-4e35-8f56-c7cec0eb5963" />



