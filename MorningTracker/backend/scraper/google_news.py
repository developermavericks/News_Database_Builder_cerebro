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


def _resolve_google_news_via_batchexecute(url: str, headers: dict, proxy_url: Optional[str] = None) -> Optional[str]:
    """
    Resolve modern Google News RSS article tokens using internal batchexecute API.
    Works for many CBMi/CBM... tokens that fail direct base64 decoding.
    """
    if "/articles/" not in url:
        return None
        
    try:
        import time
        import random
        import requests
        token = url.split("/articles/")[1].split("?")[0]
        proxies_dict = {"http": proxy_url, "https": proxy_url} if proxy_url else None
        
        # Google RPC Resolution with Proxy Retries
        for attempt in range(5):
            try:
                page = requests.get(url, headers=headers, proxies=proxies_dict, timeout=15)
                if page.status_code == 429:
                    logger.warning(f"Google RPC Rate Limited (429). Backing off. Attempt {attempt+1}")
                    time.sleep(random.uniform(1, 4) * (attempt + 1))
                    continue
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
                batched = requests.post(
                    "https://news.google.com/_/DotsSplashUi/data/batchexecute?rpcids=Fbv4je",
                    data=body,
                    headers={
                        **headers,
                        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                        "Referer": "https://news.google.com/",
                    },
                    proxies=proxies_dict,
                    timeout=15
                )
                if batched.status_code == 429:
                    logger.warning(f"Google Batchexecute Rate Limited (429). Backing off. Attempt {attempt+1}")
                    time.sleep(random.uniform(1, 4) * (attempt + 1))
                    continue
                    
                txt = (batched.text or "").replace("\\/", "/")
                # Pull first strong URL candidate from batchexecute envelope.
                for candidate in re.findall(r"https?://[^\s\\\"'<>]+", txt):
                    if is_probable_article_url(candidate):
                        return candidate
                        
                # If we get here with a 200 but no URL, don't retry, just return None.
                return None
            except Exception as loop_e:
                logger.debug(f"RPC fetch error on attempt {attempt+1}: {loop_e}")
                time.sleep(1)
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
        import os, random
        
        # Use the global healthy proxy pool (StormProxies) instead of Webshare
        proxies = load_proxies()
        proxy = ProxyGuard.get_healthy_proxy(proxies)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": "CONSENT=YES+cb.20230501-14-p0.en+FX+438" # Bypasses EU Consent loops on rotating proxies
        }

        # 1.5. RPC token resolver for modern encoded RSS article URLs.
        if "news.google.com" in url and "/articles/" in url:
            rpc_resolved = _resolve_google_news_via_batchexecute(url, headers=headers, proxy_url=proxy)
            if rpc_resolved and is_probable_article_url(rpc_resolved):
                return rpc_resolved
        
        # --- LAYER 1: Proxy HTTP (Best for Redirections) ---
        # Using Storm Proxies with requests (robust against timeouts)
        try:
            import time
            import random
            import requests
            proxies_dict = {"http": proxy, "https": proxy} if proxy else None
            
            for attempt in range(5):
                try:
                    resp = requests.get(url, headers=headers, proxies=proxies_dict, timeout=15)
                    if resp.status_code == 429:
                        logger.warning(f"Layer 1 Rate Limited (429). Backing off. Attempt {attempt+1}")
                        time.sleep(random.uniform(1, 4) * (attempt + 1))
                        continue
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
                        logger.info(f"Layer 1 resolution blocked by robot page for {url}. Escalating...")
                        break
                    
                    # If we reached here without returning and not 429, don't retry.
                    break
                except Exception as loop_e:
                    logger.debug(f"Layer 1 fetch error on attempt {attempt+1}: {loop_e}")
                    time.sleep(1)
        except Exception as e:
            logger.warning(f"Layer 1 (Proxy HTTP) failed for {url}: {e}. Trying Layer 2...")

        # --- LAYER 2: Crawlbase API Fallback ---
        try:
            import os, requests
            cb_token = os.environ.get("CRAWLBASE_TOKEN")
            if cb_token:
                cb_url = f"https://api.crawlbase.com/?token={cb_token}&url={url}"
                cb_resp = requests.get(cb_url, timeout=15)
                if cb_resp.status_code == 200:
                    canonical_match = re.search(r'rel=[\"\']canonical[\"\'][^>]*href=[\"\']([^\"\']+)', cb_resp.text, re.I)
                    if canonical_match:
                        candidate = canonical_match.group(1)
                        if is_probable_article_url(candidate):
                            return candidate
                    html_candidate = _extract_source_from_google_html(cb_resp.text)
                    if html_candidate:
                        return html_candidate
        except Exception as e:
            logger.warning(f"Layer 2 (Crawlbase) failed for {url}: {e}")
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
