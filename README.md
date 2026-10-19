# Pacific Crest Estates — Backend API (Python / Flask)

Pure-Python backend for the **Pacific Crest Estates** luxury California real-estate
website. Built for **Render.com** — no Docker, no containers. Flask +
Flask-SQLAlchemy + Gunicorn.

## What it does
- `POST /api/contact` — saves "Book a Private Viewing" form submissions.
- `POST /api/enquiry` — saves per-property enquiries from the listing modal.
- `POST /api/newsletter` — saves newsletter signups (deduplicated by email).
- `POST /api/paypal/create-order` + `POST /api/paypal/capture-order` — **PayPal
  mock / simulation** of the real PayPal Orders v2 flow for the refundable
  holding deposit. No real money moves. Every order is stored in the database.
- `GET /api/properties` — the 12 featured California listings as JSON.
- `GET /api/admin/submissions?secret=ADMIN_SECRET` — dump of all submissions.

## Database
- **SQLite** (Python's built-in database) by default — zero setup. On Render,
  if you attach a persistent Disk at `/var/data` (see `render.yaml`), the DB
  file lives there and survives deploys.
- **PostgreSQL** (recommended for production): create a Render Postgres
  instance and link it to this service — Render sets `DATABASE_URL`
  automatically and the app uses it (the `postgres://` scheme is rewritten to
  `postgresql://` for SQLAlchemy).

## Run locally
```bash
pip install -r requirements.txt
python app.py            # http://127.0.0.1:5000
# health check: curl http://127.0.0.1:5000/api/health
```

## Deploy to Render.com (no Docker)
1. Push this `backend/` folder to a Git repo (or upload it).
2. Render Dashboard → **New → Web Service** → connect the repo / folder.
3. Settings:
   - **Runtime / Language**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. Environment variables:
   - `PYTHON_VERSION` = `3.11.9`
   - `SECRET_KEY` = (generate a random string)
   - `ADMIN_SECRET` = (generate a random string)
   - `CORS_ORIGINS` = your frontend URL (e.g. `https://your-site.netlify.app`) — use `*` only for dev.
   - `FRONTEND_URL` = your deployed frontend URL (auto-added to allowed CORS origins and shown on `GET /`).
   - `HOLDING_DEPOSIT_USD` = `1000.00` (optional)
5. (Optional, recommended) **New → PostgreSQL**, then from the Postgres page
   choose **Connect** → your web service. `DATABASE_URL` is injected
   automatically.
6. Click **Deploy**. Your API is live at `https://<service-name>.onrender.com`.

Alternatively, use the included `render.yaml` (Render Blueprint) — it encodes
all of the above, including an optional 1 GB persistent Disk for SQLite.

## Going live with real PayPal
The mock endpoints mirror PayPal's Orders v2 shape. To switch to real
payments:
1. `pip install paypalrestsdk` (or use direct REST calls).
2. In `app.py`, replace the bodies of `paypal_create_order` and
   `paypal_capture_order` with real SDK calls using `PAYPAL_CLIENT_ID` /
   `PAYPAL_CLIENT_SECRET` env vars (sandbox first, then live).
3. The frontend modal already calls these two endpoints in the same order
   PayPal's Smart Buttons do — only the approval step is simulated.

## Project structure
```
backend/
├── app.py            # Flask app + all routes + property catalogue
├── config.py         # config (DATABASE_URL / SQLite fallback, CORS, secrets)
├── models.py         # SQLAlchemy models (Contact, Enquiry, Newsletter, PayPalOrder)
├── requirements.txt  # pip dependencies (Render build command reads this)
├── render.yaml       # optional Render Blueprint (native, no Docker)
├── .env.example      # local env vars template
├── .gitignore
└── README.md
```
