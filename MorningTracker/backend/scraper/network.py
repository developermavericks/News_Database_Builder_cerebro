import asyncio
import time
import random
import logging
import httpx
import hashlib
import os
from typing import Optional, List, Dict, Any
from gevent.lock import BoundedSemaphore
from scraper.llm import get_redis_sync
from scraper.config import USER_AGENTS

try:
    from crawlbase import CrawlingAPI
except ImportError:
    CrawlingAPI = None

logger = logging.getLogger(__name__)

def track_stormproxy(status_code: str, url: str, error: str = ""):
    try:
        import os, datetime
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stormproxy_tracker.log")
        with open(log_file, "a", encoding="utf-8") as f:
            t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{t}] STATUS: {status_code} | URL: {url} | ERR: {error}\n")
    except Exception:
        pass

# --- Proxy Management ---
class ProxyGuard:
    """
    Global Proxy Guard using Redis for distributed state consistency.
    Ensures all worker processes share the same proxy blacklist.
    """
    REDIS_KEY = "nexus:proxy_blacklist"
    
    @classmethod
    def mark_unhealthy(cls, proxy_url: str, duration: int = 300):
        if not proxy_url: return
        
        # Don't long-blacklist rotating gateways as they internally rotate IPs
        di_proxy = os.environ.get("STORMPROXY")
        if di_proxy and di_proxy in proxy_url:
            duration = 5 # Extremely short cool-down for rotating gateways
            
        try:
            r = get_redis_sync()
            r.setex(f"{cls.REDIS_KEY}:{proxy_url}", duration, "unhealthy")
            logger.warning(f"PROXY-GUARD: Blacklisted {proxy_url[:30]}... for {duration}s across cluster.")
        except Exception as e:
            logger.error(f"ProxyGuard Redis error: {e}")
        
    @classmethod
    def is_healthy(cls, proxy_url: str) -> bool:
        if not proxy_url: return True
        try:
            r = get_redis_sync()
            return not r.exists(f"{cls.REDIS_KEY}:{proxy_url}")
        except:
            return True

    @classmethod
    def get_healthy_proxy(cls, pool: List[str]) -> Optional[str]:
        """Strictly returns a healthy proxy from the pool or None. No fallbacks."""
        if not pool: return None
        
        healthy = [p for p in pool if cls.is_healthy(p)]
        if not healthy:
            logger.error("PROXY-GUARD: All available proxies are blacklisted. Hard-blocking request.")
            return None
            
        # Add selection jitter for high-concurrency requests hitting the same endpoint
        # We sort by a hash to keep it stable but randomized
        random.shuffle(healthy)
        selected = healthy[0]
        return selected

def load_proxies():
    import os
    raw = os.environ.get("PROXY_LIST", "")
    proxies = [p.strip() for p in raw.split(",") if p.strip()]
    
    # Inject DataImpulse rotating proxy if configured
    di_proxy = os.environ.get("STORMPROXY")
    if di_proxy and di_proxy not in proxies:
        proxies.insert(0, di_proxy) # Prioritize high-quality rotating proxy
        
    return proxies


class RedisRateLimiter:
    """
    Global Rate Limiter using Redis INCR for multi-process coordination.
    Replaces the local asyncio.Semaphore.
    """
    def __init__(self, key: str, limit: int = 3, window: int = 2):
        self.key = f"nexus:ratelimit:{key}"
        self.limit = limit
        self.window = window

    async def __aenter__(self):
        from scraper.llm import get_redis
        # Redis rate limiting must never deadlock the pipeline.
        # If Redis async client hangs (rare on some Windows event loop setups),
        # we fall back to a permissive mode rather than blocking all discovery.
        try:
            r = await asyncio.wait_for(get_redis(), timeout=2)
        except Exception:
            await asyncio.sleep(random.uniform(0.05, 0.15))
            return self
        while True:
            # Atomic increment
            try:
                count = await asyncio.wait_for(r.incr(self.key), timeout=2)
            except Exception:
                await asyncio.sleep(random.uniform(0.05, 0.15))
                return self
            # Ensure the key always has an expiry.
            # If Redis restarts/restores without TTLs (or an earlier bug wrote the key without expiry),
            # the counter can grow unbounded and permanently block the pipeline.
            if count == 1:
                try:
                    await asyncio.wait_for(r.expire(self.key, self.window), timeout=2)
                except Exception:
                    pass
            else:
                try:
                    ttl = await asyncio.wait_for(r.ttl(self.key), timeout=2)
                except Exception:
                    ttl = None
                if ttl is None or ttl < 0:
                    try:
                        await asyncio.wait_for(r.expire(self.key, self.window), timeout=2)
                    except Exception:
                        pass
            
            if count <= self.limit:
                # Slot acquired, add small jitter to prevent thundering herd
                await asyncio.sleep(random.uniform(0.1, 0.4))
                return self
            
            # Limit reached, backoff slightly and retry
            await asyncio.sleep(0.5)

    async def __aexit__(self, *args):
        pass

rate_limiter = RedisRateLimiter("google_rss", limit=100, window=5)

class NetworkHandler:
    """
    Handles network I/O with persistent connection pooling and global throttling.
    """
    _clients: Dict[Optional[str], httpx.AsyncClient] = {}
    _client_lock = asyncio.Lock()

    @classmethod
    async def get_async_client(cls, proxy: Optional[str] = None) -> httpx.AsyncClient:
        """Returns a cached AsyncClient for the given proxy to enable pooling."""
        async with cls._client_lock:
            if proxy not in cls._clients or cls._clients[proxy].is_closed:
                # Optimized for 2000 concurrency across 100 backbone slots
                limits = httpx.Limits(max_connections=500, max_keepalive_connections=100)
                cls._clients[proxy] = httpx.AsyncClient(
                    timeout=30, 
                    follow_redirects=True, 
                    limits=limits,
                    proxy=proxy,
                    verify=False
                )
            return cls._clients[proxy]

    @staticmethod
    async def fetch_crawlbase(url: str, scraper: Optional[str] = None, use_js: bool = True) -> Optional[str]:
        """Fetches a URL using Crawlbase API with dynamic strategy selection."""
        token = os.environ.get("CRAWLBASE_TOKEN")
        if not token or not CrawlingAPI:
            return None
        
        try:
            # Crawlbase is usually synchronous in its SDK, so we run in threadpool
            def sync_fetch():
                api = CrawlingAPI({'token': token})
                options = {}
                
                if "google.com" in url and "/rss" not in url:
                    options['scraper'] = 'google-news'
                elif "/rss" not in url:
                    # Tiered Strategy Logic
                    if scraper:
                        options['scraper'] = scraper
                    
                    # Advanced stealth parameters
                    options['javascript'] = 'true'
                    options['proxy_type'] = 'smart'
                    options['page_wait'] = '5000'
                    # Wait for any common article container to ensure content is loaded
                    options['wait_for'] = 'article, .article, .story, .post, #content, main'
                    
                    # Masquerade as Googlebot to bypass paywalls and cookie walls
                    options['headers'] = "User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)|Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                
                response = api.get(url, options)
                
                # Check for success (Crawlbase uses 'original_status' or 'pc_status' in headers)
                headers = response.get('headers', {})
                pc_status = headers.get('pc_status') or response.get('pc_status')
                
                if str(pc_status) == '200' or response.get('status_code') == 200:
                    body = response.get('body')
                    
                    # If using 'generic-article' scraper, Crawlbase returns JSON
                    if options.get('scraper') == 'generic-article':
                        try:
                            import json
                            data = json.loads(body)
                            # The AI Scraper puts the clean, readable text in the 'content' field
                            if data.get('content'):
                                return data['content']
                        except: pass

                    if isinstance(body, bytes):
                        return body.decode('utf-8', errors='ignore')
                    return body
                
                logger.warning(f"Crawlbase Fetch failed for {url}: Status {pc_status}")
                return None

            return await asyncio.to_thread(sync_fetch)
        except Exception as e:
            logger.error(f"Crawlbase Fetch Error for {url}: {e}")
            return None

    @staticmethod
    async def get_google_rss(url: str, proxy: Optional[str] = None, use_cache: bool = True) -> Optional[str]:
        """
        Refactored Google News RSS fetcher with Discovery-First Resilience.
        If proxy redirects (301/302) or fails, it falls back to a direct connection.
        """
        from scraper.llm import get_redis
        # Never allow Redis async to stall discovery.
        try:
            redis = await asyncio.wait_for(get_redis(), timeout=2)
        except Exception:
            redis = None
            use_cache = False
        cache_key = f"nexus:rss_cache:{hashlib.md5(url.encode()).hexdigest()}"
        
        if use_cache:
            try:
                cached = await asyncio.wait_for(redis.get(cache_key), timeout=2)  # type: ignore[union-attr]
                if cached:
                    return cached if isinstance(cached, str) else cached.decode('utf-8')
            except Exception:
                pass

        # Global Throttle Check
        if redis is not None:
            try:
                throttle_count = int(await asyncio.wait_for(redis.get("nexus:global_503_count"), timeout=2) or 0)
                if throttle_count >= 30:
                    await asyncio.sleep(5)
                    return None
            except Exception:
                pass

        # Discovery Strategy: Crawlbase (Primary) -> Proxy Retries -> Safety Fallback (Direct)
        
        # 1. Try DataImpulse Direct for Discovery if configured (Much faster than Crawlbase for RSS)
        di_proxy = os.environ.get("STORMPROXY")
        if di_proxy:
            try:
                async with rate_limiter:
                    client = await NetworkHandler.get_async_client(proxy=di_proxy)
                    resp = await client.get(url, headers={"User-Agent": random.choice(USER_AGENTS)}, follow_redirects=True, timeout=10)
                    if resp.status_code == 200:
                        content = resp.text
                        if "<rss" in content.lower() or "<feed" in content.lower():
                            track_stormproxy("200_SUCCESS_RSS", url)
                            return content
                        else:
                            track_stormproxy("200_NON_RSS", url)
                    else:
                        track_stormproxy(f"FAILED_{resp.status_code}", url)
            except Exception as e:
                track_stormproxy("EXCEPTION", url, str(e))

        # 2. Try Crawlbase as fallback
        cb_content = await NetworkHandler.fetch_crawlbase(url)

        from scraper.network import load_proxies, ProxyGuard
        pool = load_proxies()
        
        # We try up to 3 different healthy proxies before giving up on this keyword/day
        max_proxy_attempts = 3
        proxy_attempts = 0
        
        current_p = proxy
        while proxy_attempts < max_proxy_attempts:
            async with rate_limiter:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
                
                try:
                    client = await NetworkHandler.get_async_client(proxy=current_p)
                    resp = await client.get(url, headers=headers, follow_redirects=True, timeout=10)
                    
                    if resp.status_code == 200:
                        content = resp.text
                        if "<rss" in content.lower() or "<feed" in content.lower():
                            if redis is not None:
                                try:
                                    await asyncio.wait_for(redis.setex(cache_key, 3600, content), timeout=2)
                                except Exception:
                                    pass
                            return content
                        else:
                            # It's a 200 but not RSS? Likely a CAPTCHA or Block page.
                            logger.warning(f"Google RSS: Received non-RSS response (Blocked/Captcha). Retrying proxy.")
                    
                    if resp.status_code in [403, 429, 503]:
                        if current_p: ProxyGuard.mark_unhealthy(current_p)
                        if redis is not None:
                            try:
                                count = await asyncio.wait_for(redis.incrby("nexus:global_503_count", 1), timeout=2)
                                if count == 1:
                                    await asyncio.wait_for(redis.expire("nexus:global_503_count", 300), timeout=2)
                            except Exception:
                                pass
                
                except Exception as e:
                    if current_p: ProxyGuard.mark_unhealthy(current_p)
                    logger.debug(f"RSS Discovery Proxy Error: {e}")
            
            # Pick a new proxy for the next attempt
            current_p = ProxyGuard.get_healthy_proxy(pool)
            proxy_attempts += 1
            await asyncio.sleep(0.5)

        # Final fallback: Direct (no proxy). This is critical when the proxy fleet is blocked by Google
        # but the machine IP can still access RSS.
        try:
            async with rate_limiter:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
                client = await NetworkHandler.get_async_client(proxy=None)
                resp = await client.get(url, headers=headers, follow_redirects=True, timeout=10)
                if resp.status_code == 200:
                    content = resp.text
                    if "<rss" in content.lower() or "<feed" in content.lower():
                        if redis is not None:
                            try:
                                await asyncio.wait_for(redis.setex(cache_key, 3600, content), timeout=2)
                            except Exception:
                                pass
                        return content
        except Exception as e:
            logger.debug(f"RSS Discovery Direct Fallback Error: {e}")

        return None
