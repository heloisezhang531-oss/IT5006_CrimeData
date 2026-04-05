# Backend API

## Run

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

APIs used by frontend:
- `/api/crime/current-month-community`
- `/api/crime/predicted-next-month-risk`
- `/api/crime/ten-year-trend`
- `/api/crime/current-month-top10-primary-type`
- `/api/crime/raw-data`
- `/api/model/metrics`
- `/api/model/feature-importance`
