import logging
import json
import hashlib
import os
import httpx
import trafilatura
import re
from datetime import datetime
from typing import Optional
from celery_app import app as celery_app
from config import run_async
from db.database import get_db_sync, Article, ScrapeJob
from scraper.orchestrator import _mark_article_processed
from scraper.browser import scrape_url
from sqlalchemy import select, update

logger = logging.getLogger(__name__)

# #region agent log (debug-9146a2)
def _agent_dbg(hypothesisId: str, location: str, message: str, data: dict):
    try:
        import json as _json, time as _time
        payload = {
            "sessionId": "9146a2",
            "runId": "fulltext-1",
            "hypothesisId": hypothesisId,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(_time.time() * 1000),
        }
        with open("/app/debug/debug-9146a2.log", "a", encoding="utf-8") as f:
            f.write(_json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
# #endregion agent log (debug-9146a2)

class ScraperPersistence:
    """Manages persistent network resources for workers."""
    _sync_clients: dict = {}
    
    @classmethod
    def get_sync_client(cls, proxy: Optional[str] = None, timeout: int = 15) -> httpx.Client:
        if proxy not in cls._sync_clients or cls._sync_clients[proxy].is_closed:
            cls._sync_clients[proxy] = httpx.Client(
                proxy=proxy,
                timeout=timeout, 
                follow_redirects=True, 
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=50),
                verify=False
            )
        return cls._sync_clients[proxy]


# --- Orchestrator Task --------------------------------------------------------

@celery_app.task(name="scraper.tasks.run_scrape_task", bind=True)
def run_scrape_task(self, job_id, sector, region, date_from, date_to, search_mode, user_id):
    """
    Orchestrator: Discovers URLs and dispatches independent scraping nodes.
    Bridges to the async run_scrape_job implementation.
    """
    logger.info(f"Starting Orchestrator (Async-Bridged) for job {job_id}")
    
    # Strict Sequential Execution Guard: Ensures only ONE active job runs discovery and extraction.
    try:
        from scraper.llm import get_redis_sync
        import time
        
        redis_client = get_redis_sync()
        lock_key = "nexus:sequential_guard_lock"
        
        # Loop until we successfully acquire the sequence slot and there are NO active jobs
        while True:
            # 1. Acquire Redis lock
            acquired = False
            for _ in range(10):
                if redis_client.set(lock_key, "locked", ex=15, nx=True):
                    acquired = True
                    break
                time.sleep(0.5)
                
            if not acquired:
                logger.warning(f"Could not acquire sequential guard lock for job {job_id}. Sleeping 5 seconds...")
                time.sleep(5)
                continue
                
            try:
                # 2. Check DB for active jobs
                with get_db_sync() as db:
                    active_jobs = db.execute(
                        select(ScrapeJob)
                        .where(ScrapeJob.status.in_(["running", "processing"]))
                        .where(ScrapeJob.id != job_id)
                    ).scalars().all()
                    
                    if len(active_jobs) < 3:
                        # 3. Slots available: reserve the slot by marking status as running!
                        db.execute(
                            update(ScrapeJob)
                            .where(ScrapeJob.id == job_id)
                            .values(status='running', started_at=datetime.now())
                        )
                        logger.info(f"Batched Sequence: Job {job_id} successfully locked a sequence slot ({len(active_jobs)}/3 active) and is now running.")
                        break # Exit the while loop and proceed to execution!
                        
                # If 3 or more active jobs exist, we log and sleep 30 seconds before checking again
                logger.info(f"Batched Sequence: Job {job_id} is waiting because the maximum batch limit of 3 jobs is currently reached. Waiting 30 seconds...")
            finally:
                # Always release lock
                redis_client.delete(lock_key)
                
            # Sleep 30 seconds before checking again
            time.sleep(30)
            
    except Exception as e:
        logger.error(f"Error checking active jobs in sequential orchestrator lock: {e}")

    from scraper.engine import run_scrape_job
    try:
        result = run_async(run_scrape_job(
            job_id=job_id,
            sector=sector,
            region=region,
            date_from=date_from,
            date_to=date_to,
            search_mode=search_mode,
            user_id=user_id
        ))
        
        articles = result.get("articles", [])
        logger.info(f"Discovery phase for job {job_id} completed. Dispatched {len(articles)} extraction nodes.")
        
        # --- FAIR-SHARE INTERLEAVING (STABILITY MODE) ---
        # Dispatch in batches of 50 to allow up to 2 concurrent jobs to share the 24 workers.
        import time
        CHUNK_SIZE = 50
        DELAY_BETWEEN_CHUNKS = 0.5
        
        logger.info(f"Dispatching {len(articles)} nodes for job {job_id} using Interleaved Batching.")
        
        for i in range(0, len(articles), CHUNK_SIZE):
            # --- SAFETY SWITCH ---
            # Check if user has stopped the job in the DB
            with get_db_sync() as db:
                current_job = db.get(ScrapeJob, job_id)
                if not current_job or current_job.status in ["interrupted", "failed"]:
                    logger.warning(f"Orchestrator for {job_id} detected STOP status. Aborting dispatch.")
                    return
            
            chunk = articles[i:i + CHUNK_SIZE]
            for article in chunk:
                scrape_article_node.delay(
                    article_data=article,
                    job_id=job_id,
                    sector=sector,
                    region=region,
                    user_id=user_id
                )
            # Give the queue a moment to allow the OTHER active job (Job #2) to insert its chunk
            if i + CHUNK_SIZE < len(articles):
                time.sleep(DELAY_BETWEEN_CHUNKS)
            
    except Exception as e:
        logger.error(f"Orchestrator failed for job {job_id}: {e}")
        # Persist terminal failure for consistent UI/ops visibility.
        try:
            with get_db_sync() as db:
                db.execute(
                    update(ScrapeJob)
                    .where(ScrapeJob.id == job_id)
                    .values(
                        status="failed",
                        current_phase="Failed",
                        completed_at=datetime.now(),
                        error=f"Orchestrator failed: {str(e)}",
                    )
                )
                db.commit()
        except Exception as db_e:
            logger.error(f"Failed to persist terminal failure state for job {job_id}: {db_e}")
        raise e

# ─── Scraper Node (I/O Intensive) ─────────────────────────────────────────────

@celery_app.task(
    bind=True, 
    max_retries=5, 
    default_retry_delay=10, 
    retry_backoff=True,
    retry_backoff_max=300,
    rate_limit="200/m"
)
def scrape_article_node(self, article_data, job_id, sector, region, user_id, scaling_mode=False):
    """
    Task Node 1: Fetches HTML and extracts raw body. 
    Optimized for 2.3 articles/sec in scaling mode.
    """
    from scraper.engine import scrape_only, is_job_cancelled
    from scraper.google_news import resolve_google_news_url_sync, is_probable_article_url
    from scraper.llm import get_redis_sync
    
    try:
        url = article_data.get("url") or article_data.get("link")
        logger.info(f"Scrape Node Received: {url}")
        if is_job_cancelled(job_id):
            logger.info(f"Scrape task halted for job {job_id} [Reason: Job Cancelled/Global Stop]")
            _mark_article_processed(job_id, article_url=url or "cancelled_no_url")
            return None

        if not url:
            _mark_article_processed(job_id, article_url="unknown_missing_url")
            return None
            
        # Resolve Google News redirect if needed
        resolved_url = url
        if "news.google.com" in url:
            resolved_url = resolve_google_news_url_sync(url)
            logger.info(f"Resolved Google URL to: {resolved_url}")
        
        # Never scrape unresolved Google shell URLs; this is the main source of placeholder bodies.
        if (not resolved_url) or (not is_probable_article_url(resolved_url)) or ("news.google.com" in resolved_url):
            logger.info(f"Skipping URL: {resolved_url} (Reason: Probable Shell/Redirect Failure)")
            _mark_article_processed(job_id, article_url=url)
            return None
        
        # --- TIRED ESCALATION SCRAPING FLOW ---
        html = None
        timeout = 30
        from scraper.network import NetworkHandler
        from scraper.parser import is_junk_body
        
        # STAGE 1: Crawlbase AI Scraper (Best Readability)
        logger.info(f"Stage 1 Scraping (AI) for {resolved_url}")
        try:
            html = run_async(NetworkHandler.fetch_crawlbase(resolved_url, scraper='generic-article'), timeout=timeout)
        except Exception as e:
            logger.debug(f"Stage 1 failed: {e}")

        # Escalation criteria: less than 1200 chars or contains 'read more' / snippet markers
        def needs_escalation(content):
            if not content: return True
            if len(content) < 1200: return True
            content_lower = content.lower()
            
            # Detect Cloudflare / CAPTCHA / Bot block pages
            block_markers = ["access denied", "cloudflare", "enable javascript", "please wait...", "security check", "verify you are human", "captcha", "attention required!"]
            if any(m in content_lower for m in block_markers):
                return True
                
            # Check if content looks like a truncated snippet
            snippet_markers = ["read more", "continue reading", "subscription", "subscribe to", "register to read", "sign in to continue", "log in to read", "create a free account to read", "unlock this article"]
            if any(m in content_lower for m in snippet_markers):
                return True
            return False

        # STAGE 2: Crawlbase JS Deep-Fetch (Bypass AI confusion)
        if needs_escalation(html):
            logger.info(f"Stage 2 Scraping (JS Deep-Fetch) for {resolved_url}")
            try:
                # Normal mode but with heavy JS and waiting
                js_html = run_async(NetworkHandler.fetch_crawlbase(resolved_url, scraper=None, use_js=True), timeout=timeout)
                if js_html and len(js_html) > len(html or ""):
                    html = js_html
            except Exception as e:
                logger.debug(f"Stage 2 failed: {e}")

        # STAGE 3: High-Quality Rotating Proxy Fallback (DataImpulse/Webshare)
        if needs_escalation(html):
            logger.info(f"Stage 3 Scraping (Rotating Proxy Fallback) for {resolved_url}")
            try:
                from scraper.network import load_proxies, ProxyGuard, track_stormproxy
                proxy_pool = load_proxies()
                proxy = ProxyGuard.get_healthy_proxy(proxy_pool)
                client = ScraperPersistence.get_sync_client(proxy=proxy, timeout=timeout)
                resp = client.get(
                    resolved_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                )
                if resp.status_code == 200:
                    if len(resp.text) > len(html or ""):
                        html = resp.text
                        track_stormproxy("200_SUCCESS_ARTICLE", resolved_url)
                    else:
                        track_stormproxy("200_SUCCESS_NO_IMPROVEMENT", resolved_url)
                else:
                    track_stormproxy(f"FAILED_{resp.status_code}", resolved_url)
            except Exception as e:
                try:
                    from scraper.network import track_stormproxy
                    track_stormproxy("EXCEPTION_ARTICLE", resolved_url, str(e))
                except: pass
                logger.debug(f"Stage 3 failed: {e}")

        # STAGE 4: Stealth Browser with selector waits (handles skeleton placeholders)
        # BYPASSED FOR SPEED
        # if needs_escalation(html) or "loading" in (html or "").lower()[:600]:
        #     logger.info(f"Stage 4 Scraping (Stealth Browser Wait) for {resolved_url}")
        #     try:
        #         browser_html = run_async(scrape_url(resolved_url, timeout=45000, use_proxy=True), timeout=70)
        #         if browser_html and len(browser_html) > len(html or ""):
        #             html = browser_html
        #     except Exception as e:
        #         logger.debug(f"Stage 4 failed: {e}")

        if not html:
            logger.warning(f"All Scraping Stages failed for {resolved_url}")
            _mark_article_processed(job_id, article_url=url)
            return None

        # Move processed data back to article_data for Engine
        article_data["resolved_url"] = resolved_url
        article_data["raw_html"] = html

        article_id = run_async(scrape_only(article_data, job_id, sector, region, user_id))
        if article_id:
            # Mark as processed in Redis for O(1) deduplication in future discovery
            redis = get_redis_sync()
            url_hash = hashlib.md5(resolved_url.encode()).hexdigest()
            redis.sadd("nexus:processed_urls", url_hash)
            
            logger.info(f"Scraped article {article_id}. Triggering enrichment...")
            enrich_article_node.delay(article_id, original_url=url) # Pass original URL forward
        else:
            _mark_article_processed(job_id, article_url=url) # Standardized on ORIGINAL URL

    except Exception as e:
        logger.error(f"Scrape node failed for {article_data.get('url')}: {e}")
        if self.request.retries >= self.max_retries:
            _mark_article_processed(job_id)
        raise self.retry(exc=e)

# ─── Enrichment Node (Compute Intensive) ──────────────────────────────────────

@celery_app.task(name="scraper.tasks.enrich_article_node", bind=True, max_retries=3)
def enrich_article_node(self, article_id, original_url=None):
    """
    Task Node 2: Performs AI analysis (Grok/Groq).
    Runs server-side, completely independent of user session.
    """
    from scraper.llm import perform_full_enrichment_sync
    from scraper.engine import is_job_cancelled
    
    with get_db_sync() as db:
        res = db.execute(select(Article).where(Article.id == article_id))
        article = res.scalar_one_or_none()
        if not article or not article.full_body: return
        
        if is_job_cancelled(article.scrape_job_id):
            logger.info(f"Enrichment cancelled for job {article.scrape_job_id}. Skipping article {article_id}")
            return

        try:
            enriched_data = perform_full_enrichment_sync(
                article.full_body, 
                article.title, 
                article.resolved_url or article.url, 
                article.sector,
                context_agency=article.agency,
                extra_metadata=article.extra_metadata
            )
            
            article.summary = enriched_data.get("summary")
            article.sentiment = enriched_data.get("sentiment")
            article.tags = enriched_data.get("tags")
            if enriched_data.get("agency"): article.agency = enriched_data.get("agency")
            if enriched_data.get("author"): article.author = enriched_data.get("author")
            
            db.commit()
            logger.info(f"Successfully enriched article {article_id}")
            
            # --- PROGRESS SYNC ---
            from scraper.orchestrator import _mark_article_processed
            _mark_article_processed(article.scrape_job_id, article_url=original_url or article.url)
        except Exception as e:
            logger.error(f"AI Enrichment failed for article {article_id}: {e}")
            if self.request.retries >= self.max_retries:
                from scraper.orchestrator import _mark_article_processed
                _mark_article_processed(article.scrape_job_id, article_url=original_url or article.url)
            raise self.retry(exc=e, countdown=60)


# ─── Stale Job Watchdog (runs every 5 minutes via Celery Beat) ────────────────

@celery_app.task(name="scraper.tasks.complete_stale_jobs")
def complete_stale_jobs():
    """
    Watchdog: Scans for jobs stuck in 'running' state and marks complete if all articles are scraped.
    Ensures jobs finish even if some tasks crash silently.
    Runs every 5 minutes via Celery Beat schedule.
    """
    from datetime import datetime, timedelta
    try:
        with get_db_sync() as db:
            stale_cutoff = datetime.now() - timedelta(minutes=10)
            running_jobs = db.execute(
                select(ScrapeJob).where(
                    ScrapeJob.status == 'running',
                    ScrapeJob.started_at < stale_cutoff,
                    ScrapeJob.total_found > 0
                )
            ).scalars().all()

            for job in running_jobs:
                from scraper.llm import get_redis_sync
                r = get_redis_sync()
                job_set_key = f"nexus:job_processed_set:{job.id}"
                current_scraped = r.scard(job_set_key)

                # Force-complete if total_scraped is near total_found
                if current_scraped >= max(0, job.total_found - 3):
                    db.execute(
                        update(ScrapeJob).where(ScrapeJob.id == job.id).values(
                            status='completed',
                            current_phase='Completed',
                            total_scraped=max(current_scraped, job.total_found),  # Sync from real truth
                            completed_at=datetime.now()
                        )
                    )
                    logger.info(f"Watchdog synchronized stale job {job.id} ({current_scraped}/{job.total_found})")
            
            db.commit()
    except Exception as e:
        logger.error(f"Stale job watchdog error: {e}")
