# Frontend (Port 3000)

## Run

```bash
cd frontend
npm install
npm run dev
```

The app exposes two pages only:
- `Crime Action`
- `Model Lab`

If backend is not on `http://localhost:8000`, set proxy target before start:

```bash
VITE_API_PROXY_TARGET=http://backend:8000 npm run dev
```
