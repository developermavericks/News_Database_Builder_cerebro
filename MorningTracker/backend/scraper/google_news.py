import httpx
import os
import logging
import base64
import re
import json
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger("GOOGLE_NEWS")


def _extract_source_from_google_html(html: str) -> Optional[str]:
    """Extract outbound publisher URL from Google News intermediate HTML."""
    if not html:
        return None
    patterns = [
        r'data-n-au=[\"\']([^\"\']+)',
        r'\"url\"\\s*:\\s*\"(https?:\\\\/\\\\/[^\"\\\\]+)\"',
        r'rel=[\"\']canonical[\"\'][^>]*href=[\"\']([^\"\']+)',
        r'href=[\"\'](https?://[^\"\']+)[\"\'][^>]*>\\s*(?:Read|View|Open)',
    ]
    for pattern in patterns:
        try:
            match = re.search(pattern, html, re.I)
            if not match:
                continue
            candidate = match.group(1)
            candidate = candidate.replace("\\/", "/")
            if is_probable_article_url(candidate):
                return candidate
        except Exception:
            continue
    return None


def _extract_google_decode_params(html: str) -> tuple[Optional[str], Optional[str]]:
    """Extract signature/timestamp pair required by Google's batchexecute resolver."""
    if not html:
        return None, None
    sig_match = re.search(r'data-n-a-sg=[\"\']([^\"\']+)', html, re.I)
    ts_match = re.search(r'data-n-a-ts=[\"\']([^\"\']+)', html, re.I)
    sig = sig_match.group(1) if sig_match else None
    ts = ts_match.group(1) if ts_match else None
    return sig, ts


def _resolve_google_news_via_batchexecute(url: str, headers: dict) -> Optional[str]:
    """
    Resolve modern Google News RSS article tokens using internal batchexecute API.
    Works for many CBMi/CBM... tokens that fail direct base64 decoding.
    """
    if "/articles/" not in url:
        return None
    try:
        token = url.split("/articles/")[1].split("?")[0]
        with httpx.Client(follow_redirects=True, timeout=20) as client:
            page = client.get(url, headers=headers)
            if page.status_code != 200:
                return None
            sig, ts = _extract_google_decode_params(page.text)
            if not sig or not ts:
                # Some pages expose outbound URL directly; leverage that first.
                html_candidate = _extract_source_from_google_html(page.text)
                return html_candidate if is_probable_article_url(html_candidate) else None

            # Payload shape based on garturlreq RPC expected by Google News webapp.
            rpc_payload = [[
                "Fbv4je",
                (
                    "[\"garturlreq\",[[\"en-US\",\"US\",[\"FINANCE_TOP_INDICES\",\"WEB_TEST_1_0_0\"],"
                    "null,null,1,1,\"US:en\",null,180,null,null,null,null,null,0,null,null,"
                    "[1608992183,723341000]],\"en-US\",\"US\",1,[2,3,4,8],1,0,\"655000234\",0,0,null,0],"
                    f"\"{token}\",{ts},\"{sig}\"]"
                ),
                None,
                "generic",
            ]]
            body = {"f.req": json.dumps([rpc_payload], separators=(",", ":"))}
            batched = client.post(
                "https://news.google.com/_/DotsSplashUi/data/batchexecute?rpcids=Fbv4je",
                data=body,
                headers={
                    **headers,
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "Referer": "https://news.google.com/",
                },
            )
            txt = (batched.text or "").replace("\\/", "/")
            # Pull first strong URL candidate from batchexecute envelope.
            for candidate in re.findall(r"https?://[^\s\\\"'<>]+", txt):
                if is_probable_article_url(candidate):
                    return candidate
    except Exception as e:
        logger.debug(f"Batchexecute resolver failed for {url}: {e}")
    return None


def is_probable_article_url(candidate: Optional[str]) -> bool:
    """Reject image/CDN/google redirect URLs to keep article extraction stable."""
    if not candidate:
        return False
    try:
        parsed = urlparse(candidate)
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()
    except Exception:
        return False

    if not host:
        return False
    blocked_hosts = (
        "news.google.com",
        "google.com",
        "googleusercontent.com",
        "gstatic.com",
        "google-analytics.com",
        "googletagmanager.com",
        "doubleclick.net",
        "ytimg.com",
    )
    if any(host == blocked or host.endswith("." + blocked) for blocked in blocked_hosts):
        return False

    media_exts = (
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico", ".avif",
        ".mp4", ".webm", ".mp3", ".wav", ".pdf", ".js", ".css", ".json", ".xml",
    )
    if path.endswith(media_exts):
        return False

    return True


def decode_google_news_url(url: str) -> Optional[str]:
    """
    Advanced offline decoder for Google News URLs.
    Handles the new complex binary-encoded base64 formats.
    """
    try:
        if "/articles/" not in url:
            return None
        
        # 1. Clean the URL
        encoded = url.split("/articles/")[1].split("?")[0]
        
        # 2. Add padding for base64
        padding = len(encoded) % 4
        if padding > 0:
            encoded += "=" * (4 - padding)
            
        # 3. Base64 decode
        decoded_bytes = base64.urlsafe_b64decode(encoded)
        
        # 4. Search for the URL pattern in the binary stream
        # Google packs metadata before the URL, so we look for http or https
        url_match = re.search(rb"(https?://[a-zA-Z0-9\-\.\/\_\?\&\=\%\#\+]+)", decoded_bytes)
        if url_match:
            candidate = url_match.group(1).decode('utf-8', errors='ignore')
            if is_probable_article_url(candidate):
                return candidate
                
        # 5. Backup: Try finding common patterns if regex fails
        try:
            # Sometimes the URL is preceded by a length byte or other tag
            for i in range(len(decoded_bytes) - 8):
                if decoded_bytes[i:i+4] in [b'http', b'https']:
                    # Extract until we hit a non-printable or control char
                    end = i
                    while end < len(decoded_bytes) and decoded_bytes[end] > 31 and decoded_bytes[end] < 127:
                        end += 1
                    candidate = decoded_bytes[i:end].decode('utf-8', errors='ignore')
                    if is_probable_article_url(candidate):
                        return candidate
        except: pass

    except Exception as e:
        logger.debug(f"Decoder failed for {url}: {e}")
    return None

def resolve_google_news_url_sync(url: str) -> str:
    """
    Hybrid resolution:
    1. Fast Base64 decode (fails on some modern CBM tokens)
    2. Stealth HTTP resolution with httpx
    3. Browser-based resolution (fallback for the 'Google Jail')
    """
    if not url:
        return ""
        
    # 1. Try decoding (Instant, Google specific)
    if "news.google.com" in url:
        decoded = decode_google_news_url(url)
        if decoded:
            return decoded
    
    # 2. Selective Resilience Resolution System (Split-Tunnel)
    try:
        from scraper.network import load_proxies, ProxyGuard
        from config import run_async
        from scraper.browser import resolve_url_via_browser
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # 1.5. RPC token resolver for modern encoded RSS article URLs.
        if "news.google.com" in url and "/articles/" in url:
            rpc_resolved = _resolve_google_news_via_batchexecute(url, headers=headers)
            if rpc_resolved and is_probable_article_url(rpc_resolved):
                return rpc_resolved
        
        # --- LAYER 1: Direct HTTP (Best for Redirections) ---
        # Goal: Escape the proxy's TLS sniffing to get a clean handshake with Google
        try:
            with httpx.Client(follow_redirects=True, timeout=15) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200 and is_probable_article_url(str(resp.url)):
                    return str(resp.url)
                if resp.status_code == 200:
                    # Sometimes Google serves an intermediate HTML with canonical source URL.
                    canonical_match = re.search(r'rel=[\"\']canonical[\"\'][^>]*href=[\"\']([^\"\']+)', resp.text, re.I)
                    if canonical_match:
                        candidate = canonical_match.group(1)
                        if is_probable_article_url(candidate):
                            return candidate
                    html_candidate = _extract_source_from_google_html(resp.text)
                    if html_candidate:
                        return html_candidate
                if "google.com/images/errors/robot.png" in resp.text:
                    logger.info(f"Direct resolution blocked by robot page for {url}. Escalating...")
        except Exception as e:
            logger.warning(f"Layer 1 (Direct HTTP) failed for {url}: {e}. Trying Layer 2...")

        # --- LAYER 2: Direct Browser resolution (Handles JS-based redirects) ---
        # Prefer this layer by default for Google RSS article links.
        # If Playwright is unavailable or fails, we continue to deeper fallbacks.
        try:
            # use_proxy=False bypasses SSL interference for Google redirect chains.
            # Hard cap the bridge wait to avoid Celery worker deadlocks.
            browser_resolved = run_async(resolve_url_via_browser(url, use_proxy=False, timeout=45000), timeout=60)
            if browser_resolved and is_probable_article_url(browser_resolved):
                return browser_resolved
            if browser_resolved and "news.google.com" in browser_resolved:
                # If browser remains on Google, try a cheap HTML extraction pass from that page.
                try:
                    with httpx.Client(follow_redirects=True, timeout=15) as client:
                        final_resp = client.get(browser_resolved, headers=headers)
                        html_candidate = _extract_source_from_google_html(final_resp.text)
                        if html_candidate:
                            return html_candidate
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Layer 2 (Direct Browser) failed for {url}: {e}. Trying Layer 3...")

        # --- LAYER 3: Crawlbase Resolution (Heavy Duty) ---
        # Crawlbase is excellent at following redirects that block standard HTTP clients.
        try:
            from scraper.network import NetworkHandler
            # We use the raw fetch but look at the final URL Crawlbase reached
            # This requires a small helper or using the CrawlingAPI's ability to return the final URL
            token = os.environ.get("CRAWLBASE_TOKEN")
            if token:
                from crawlbase import CrawlingAPI
                api = CrawlingAPI({'token': token})
                # No scraper needed, just a normal fetch to resolve the redirect
                # We use 'format': 'json' but Crawlbase Python SDK returns a dict already
                cb_resp = api.get(url)
                if cb_resp.get('status_code') == 200:
                    # Check Crawlbase headers for the final URL reached
                    headers = cb_resp.get('headers', {})
                    # Crawlbase usually puts the final URL in 'url' or 'original_url'
                    resolved = headers.get('url') or cb_resp.get('url')
                    if resolved and is_probable_article_url(resolved):
                        return resolved
        except Exception as e:
            logger.warning(f"Layer 3 (Crawlbase Resolution) failed for {url}: {e}")

        # --- LAYER 4: Proxy Fallback (Final choice if Direct is blocked) ---
        try:
            proxies = load_proxies()
            proxy = ProxyGuard.get_healthy_proxy(proxies)
            with httpx.Client(proxy=proxy, follow_redirects=True, timeout=15) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200 and is_probable_article_url(str(resp.url)):
                    return str(resp.url)
        except Exception as e:
            logger.error(f"Layer 4 (Proxy) failed for {url}: {e}")

        # For Google News links, unresolved outputs should be treated as a failure
        # so callers can avoid saving placeholder content as "scraped".
        if "news.google.com" in url:
            return ""
        return url
            
    except Exception as e:
        logger.error(f"Resolution system-level failure for {url}: {e}")
        if "news.google.com" in (url or ""):
            return ""
        return url
