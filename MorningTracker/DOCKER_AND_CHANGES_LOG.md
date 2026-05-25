## Goal
Get scraping + logs working reliably by running Celery + asyncio under Linux via Docker, and keep a clear audit trail of edits.

---

## Changes already made (in this session)

### 1) Fix: Redis rate limiter could permanently deadlock Discovery
- **File**: `backend/scraper/network.py`
- **Problem**: `nexus:ratelimit:google_rss` could exist **without TTL**, grow unbounded, and block all discovery workers in the rate-limiter loop forever.
- **Change**:
  - Always enforce a TTL even when the key already exists and has no expiry.
  - Add timeouts around Redis async calls and **fail open** (continue scraping) if Redis async is stalled.

### 2) Fix: RSS fetching should not hard-depend on Redis async health
- **File**: `backend/scraper/network.py`
- **Problem**: `get_google_rss()` performed Redis async cache/throttle operations that could hang on Windows event loop setups, preventing any HTTP fetch.
- **Change**:
  - Wrap Redis async operations with timeouts.
  - If Redis async is unavailable, disable cache/throttle for that call and proceed.

### 3) Improvement: Direct (no-proxy) fallback for Google RSS
- **File**: `backend/scraper/network.py`
- **Problem**: If proxy fleet is blocked, discovery can go to zero forever.
- **Change**:
  - After a small number of proxy attempts, try a final **direct** request (no proxy).

### 4) Runtime unstick performed (operational, not code)
- Deleted Redis key: `nexus:ratelimit:google_rss`
- Restarted a `solo` priority worker on Windows and re-dispatched the job to re-run Discovery.

---

## Docker changes (done)

### 1) Fix backend Docker build context mismatch
- **File**: `backend/Dockerfile`
- **Problem**: Docker Compose uses build context `./backend`, but Dockerfile was doing:
  - `COPY backend/requirements.txt .`
  - `COPY backend/ .`
  This fails because `backend/` doesn’t exist *inside* the `./backend` build context.
- **Change**:
  - `COPY requirements.txt .`
  - `COPY . .`

### 2) Split Celery workers by queue in docker-compose
- **File**: `docker-compose.yml`
- **Problem**: single worker + unknown routing/queues makes troubleshooting harder; also Windows `gevent` issues disappear in Linux Docker.
- **Change**:
  - Added `worker_priority` (queue `priority`, concurrency 1)
  - Added `worker_celery` (queue `celery`, concurrency 4)
  - Keep `beat`
  - Backend runs: `uvicorn main:app --host 0.0.0.0 --port 8000`

### 3) Make Docker builds resilient by skipping Playwright browser downloads
- **File**: `backend/Dockerfile`
- **Problem**: `playwright install chromium` downloads from `cdn.playwright.dev` and can fail with DNS errors (e.g. `EAI_AGAIN`), blocking `docker compose up --build`.
- **Change**: removed Playwright install steps from the image build.
- **Note**: If you later enable browser-based scraping, we can add a dedicated “browser-worker” image/profile that installs Playwright.

### 4) Fix Docker runtime env precedence over local `.env.local`
- **Files**:
  - `backend/celery_app.py`
  - `backend/config.py`
  - `backend/db/database.py`
- **Problem**: these files loaded `.env.local` with `override=True`, which replaced Docker-provided env vars. In containers this caused services to use host-style values like `redis://127.0.0.1:6379/0` instead of `redis://redis:6379/0`.
- **Change**: switched to `override=False` so container/OS env values keep priority.
- **Impact**: Celery workers and DB layer now respect Docker networking values (`db`, `redis` service names).

### 5) Increase Celery task time limits for Docker runtime
- **File**: `backend/config.py`
- **Problem**: `run_scrape_task` and downstream scrape tasks were getting killed by soft/hard limits (`240s/300s`) before orchestration finished, causing jobs to remain `pending/preflight`.
- **Change (64GB profile)**:
  - `TASK_SOFT_TIME_LIMIT`: `240` -> `1500`
  - `TASK_TIME_LIMIT`: `300` -> `1800`
- **Impact**: long-running discovery/scrape orchestration can complete under Docker instead of being force-killed early.

### 6) Run `worker_priority` with `solo` pool in Docker
- **File**: `docker-compose.yml`
- **Problem**: `run_scrape_task` bridges into async (`run_async`) and can hang under prefork due to fork/thread interaction, causing jobs to remain `pending/preflight` after task receipt.
- **Change**: `worker_priority` command now uses `-P solo`.
- **Impact**: orchestration task runs in a single non-forked process, matching the stable behavior observed on Windows during earlier recovery.

### 7) Prevent Celery deadlocks by adding timeouts to `run_async` and disabling browser URL resolution by default
- **Files**:
  - `backend/config.py`
  - `backend/scraper/google_news.py`
- **Problem**:
  - `resolve_google_news_url_sync()` always attempted a browser-based resolution via `run_async(resolve_url_via_browser(...))`.
  - If Playwright/browsers aren’t installed (common in Docker), this can hang indefinitely and block `scrape_article_node` slots, so scraping never progresses.
- **Change**:
  - `run_async(coro, timeout=None)` now supports a timeout and cancels on timeout.
  - `google_news.py` only attempts browser resolution when `ENABLE_BROWSER_SCRAPE=true`, and it is capped with `timeout=60`.

### 8) Fix `/api/brands/scrape/{name}` 500 when duplicate brand nodes exist
- **File**: `backend/routers/brands.py`
- **Problem**: `scalar_one_or_none()` raised `MultipleResultsFound` when a user had duplicate `WatchedBrand` rows with same name.
- **Change**: order by `created_at desc` and use `scalars().first()` to pick the latest row.
- **Impact**: Brand scrape no longer fails with “Internal server error”.

---

## Docker run instructions (local)

### Prereqs
- Docker Desktop running
- Optional (recommended) Webshare credentials in a `.env` file in repo root (next section)

### Bring everything up
From repo root:

```bash
docker compose up --build
```

### If build fails pulling images (restricted networks)
If you see errors like `failed to fetch oauth token` / `i/o timeout` while pulling `python:3.11-slim` or `node:20-slim`, Docker Desktop can’t reach Docker Hub auth.

Try:
- Configure **Docker Desktop proxy/VPN** (if you’re on a corporate network).
- Allow outbound HTTPS to Docker Hub auth endpoints in your firewall.
- Change system DNS (e.g. 1.1.1.1 / 8.8.8.8) and restart Docker Desktop.
- Manual pulls (to get clearer errors):

```bash
docker pull python:3.11-slim
docker pull node:20-slim
```

### Stop

```bash
docker compose down
```

---

## Required environment variables for proxies (recommended)
Create a repo-root `.env` (Docker Compose automatically reads it) with:

```bash
WEBSHARE_PROXY_USER=...
WEBSHARE_PROXY_PASS=...
WEBSHARE_PROXY_HOST=p.webshare.io
WEBSHARE_IP_AUTH=false
GROQ_API_KEY=...
XAI_API_KEY=...
```

If you don’t set Webshare variables, discovery will still try direct fallback, but may be rate-limited/blocked by Google.

---

## Next changes I’m going to do (if needed)

### A) Ensure Discovery produces actionable logs per RSS request
- Add lightweight logging around HTTP status + “RSS vs block page” detection.
- Goal: make it obvious whether the issue is Google blocks, proxy auth, DNS, or timeouts.

### B) Verify end-to-end: job -> discovery -> enqueue article tasks -> scrape
- Confirm `total_found` increases in DB
- Confirm `scrape_article_node` tasks are being consumed by `worker_celery`

### 9) Fix: Article scraping not capturing full content
- **File**: `backend/scraper/parser.py`
- **Problem**: `trafilatura.bare_extraction` was called with `favor_precision=True`, which filters aggressively and omits large parts of article content.
- **Change**: Changed `favor_precision=True` to `favor_precision=False` and added `favor_recall=True` to prioritize capturing the full body content.
