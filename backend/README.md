# Backend API

## Local run

```bash
# from repo root
cp .env.example .env

cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# or from repo root:
# uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## Docker run

From repository root:

```bash
docker compose up --build backend
```

APIs used by frontend:
- `/api/crime/current-month-community`
- `/api/crime/predicted-next-month-risk`
- `/api/crime/ten-year-trend`
- `/api/crime/current-month-top10-primary-type`
- `/api/crime/raw-data`
- `/api/model/metrics`
- `/api/model/feature-importance`

Notes:
- `/api/crime/raw-data` reads from TiDB table `chicago_processed_data` and returns:
  `community_area, month, count_t1, arrest_rate, hardship_index, spatial_lag_crime_lag1`.
