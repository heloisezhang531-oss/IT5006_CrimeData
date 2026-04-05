# 🎫 Chicago data analysis

A simple Streamlit app showing an internal tool that lets you manage, and visualize crime data. 

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```

## Frontend/Backend split dashboard (Milestone 3)

This repository now also contains:
- `backend/`: FastAPI service for TiDB queries and model-report endpoints.
- `frontend/`: Vite + React dashboard (runs on port `3000`) with only two pages:
  1. Crime Action
  2. Model Lab

See `backend/README.md` and `frontend/README.md` for start commands.



### Run split frontend/backend with Docker

```bash
docker compose up --build
```

### Environment variables

```bash
cp .env.example .env
# then fill TiDB credentials in .env
```



### Run backend API quickly

```bash
pip install -r backend/requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
