import json
import re
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup
import trafilatura
from w3lib.html import remove_tags_with_content

logger = logging.getLogger("PARSER")

JUNK_PATTERNS = [
    "continue reading in the app", "enable javascript", "consent.google",
    "please enable javascript", "subscribe to read", "you have reached your article limit",
    "this content is for subscribers", "access to this page has been denied", "403 forbidden",
    "404 not found", "page not found",
    "one more step", "please complete the security check", "checking your browser",
    "ray id", "why do i have to complete a captcha", "hcaptcha", "recaptcha",
    "just a moment...", "attention required", "please verify you are a human",
    "unusual traffic from your computer network", "our systems have detected unusual traffic",
    "the block will expire shortly", "webcache.googleusercontent.com",
    "requests coming from your computer network", "archive.ph/newest", "error 429",
    "too many requests", "rate limit exceeded", "detected unusual traffic",
    "robot check", "captcha", "security challenge",
    "javascript is disabled", "please turn on javascript",
    "cookies are disabled", "enable cookies to continue",
]


def is_junk_body(text: str, brand_keywords: List[str] = None) -> bool:
    """Original simple junk check plus keyword blocking."""
    if not text or len(text.strip()) < 100: # Reduced from 200
        return True
    
    text_lower = text.lower()
    # Check for critical block patterns
    if any(pattern in text_lower for pattern in JUNK_PATTERNS):
        return True
        
    return False


def clean_author_text(text: Optional[str]) -> Optional[str]:
    if not text: return None
    text = text.strip()
    if text.startswith('{') or text.startswith('[') or 'function(' in text or 'var ' in text: return None
    if len(text) > 120 or '\n' in text: return None
    if text.lower() in ["admin", "staff", "editor", "contributor", "corporate", "none", "null"]: return None
    return text

def extract_author_v2(html: str) -> Dict[str, Any]:
    candidates = []
    handle = None
    try:
        soup = BeautifulSoup(html, "lxml")
        # 1. JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                if isinstance(data, dict) and "@graph" in data: items.extend(data["@graph"])
                for item in items:
                    if isinstance(item, dict) and item.get("@type") in ["Article", "NewsArticle", "Person"]:
                        auth_data = item.get("author")
                        if isinstance(auth_data, dict):
                            name = clean_author_text(auth_data.get("name"))
                            if name: candidates.append({"name": name, "method": "json-ld", "confidence": 0.95})
                        elif isinstance(auth_data, str):
                            name = clean_author_text(auth_data)
                            if name: candidates.append({"name": name, "method": "json-ld", "confidence": 0.85})
            except: continue
        # 2. Meta Tags
        for attr in ["name", "property"]:
            for val in ["author", "article:author", "og:article:author", "twitter:creator"]:
                tag = soup.find("meta", {attr: val})
                if tag and tag.get("content"):
                    name = clean_author_text(tag["content"])
                    if name: candidates.append({"name": name, "method": "meta", "confidence": 0.8})
    except: pass
    if not candidates: return {"name": None, "handle": None, "method": None, "confidence": 0}
    candidates.sort(key=lambda x: x["confidence"], reverse=True)
    return candidates[0]

def extract_date(html: str) -> Optional[datetime]:
    try:
        soup = BeautifulSoup(html, "lxml")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and item.get("@type") in ["Article", "NewsArticle"]:
                        for key in ["datePublished", "pubDate"]:
                            if item.get(key): return datetime.fromisoformat(item[key].replace('Z', '+00:00'))
            except: continue
    except: pass
    return None

def pre_sanitize_html(html_content: str) -> str:
    """Basic cleanup that won't break extraction tools."""
    if not html_content: return ""
    # Just remove style and noscript tags without being destructive
    return re.sub(r'<(style|noscript)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

def extract_body(html_content: str, url: str = None) -> Optional[str]:
    """
    Enhanced extraction: evaluates multiple strategies and returns the longest 
    valid (non-junk) content to ensure full article capture.
    """
    if not html_content: return None
    
    candidates = []
    
    # Strategy 1: Trafilatura (High Precision)
    try:
        # We try both bare_extraction and the standard extract for maximum coverage
        res = trafilatura.extract(
            html_content, 
            include_comments=False, 
            include_tables=True, 
            favor_recall=True,
            deduplicate=True
        )
        if res:
            if is_junk_body(res):
                return None # INSTANT DROP: It's a paywall/captcha, no need to run 6 other parsers!
            candidates.append(res)
            # ==========================================
            # TURBO MODE EARLY EXIT (CPU OPTIMIZATION)
            # ==========================================
            if len(res) > 800:
                return re.sub(r'\n{3,}', '\n\n', res).strip()
            
        res_bare = trafilatura.bare_extraction(
            html_content, 
            include_comments=False, 
            include_tables=True,
            favor_recall=True
        )
        if res_bare and res_bare.get('text'):
            if is_junk_body(res_bare.get('text')):
                return None # INSTANT DROP
            candidates.append(res_bare.get('text'))
            if len(res_bare.get('text')) > 800:
                return re.sub(r'\n{3,}', '\n\n', res_bare.get('text')).strip()
    except: pass

    # Strategy 2: JSON-LD articleBody (The "Backdoor")
    try:
        soup = BeautifulSoup(html_content, "lxml")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                raw = (script.string or script.get_text() or "").strip()
                if not raw: continue
                data = json.loads(raw)
                items = data if isinstance(data, list) else [data]
                if isinstance(data, dict) and isinstance(data.get("@graph"), list):
                    items.extend(data["@graph"])
                for item in items:
                    if isinstance(item, dict) and item.get("@type") in ["Article", "NewsArticle"]:
                        body = item.get("articleBody") or item.get("description")
                        if body and not is_junk_body(body): candidates.append(body)
            except: continue
    except: pass

    # Strategy 3: newspaper4k (Standard industry tool)
    try:
        from newspaper import Article as NewspaperArticle
        art = NewspaperArticle(url=url or '')
        art.set_html(html_content)
        art.parse()
        if art.text and not is_junk_body(art.text): candidates.append(art.text)
    except: pass

    # Strategy 4: readability-lxml (DOM-based density)
    try:
        from readability import Document
        doc = Document(html_content)
        txt = BeautifulSoup(doc.summary(), "lxml").get_text(separator="\n", strip=True)
        if txt and not is_junk_body(txt): candidates.append(txt)
    except: pass

    # Strategy 5: Advanced Container Scoring (Main Content Discovery)
    try:
        soup = BeautifulSoup(html_content, "lxml")
        # Pre-clean noise
        for noise in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "form", "iframe", "ad"]):
            noise.decompose()
            
        scores = {}
        for tag in soup.find_all(['div', 'article', 'section', 'main']):
            # Filter by class names that usually indicate noise
            cls_str = " ".join(tag.get('class') or []).lower()
            id_str = (tag.get('id') or "").lower()
            if any(noise in cls_str or noise in id_str for noise in ['sidebar', 'footer', 'nav', 'header', 'comment', 'widget', 'ad-', 'social']):
                continue
                
            p_tags = tag.find_all('p', recursive=True)
            text = tag.get_text(strip=True)
            text_len = len(text)
            if text_len < 150: continue
            
            # Scoring: Base on paragraph count and text length
            score = len(p_tags) * 80 + text_len
            
            # Boost for semantic tags
            if tag.name in ['article', 'main']: score *= 1.5
            
            # Link density penalty (real articles have text, not just links)
            links = tag.find_all('a')
            link_text_len = sum(len(a.get_text(strip=True)) for a in links)
            density = link_text_len / text_len if text_len > 0 else 1
            if density > 0.4: score *= 0.2 # Heavily penalize link-heavy blocks
            else: score *= (1 - density)
            
            scores[tag] = score
            
        if scores:
            best_tag = max(scores, key=scores.get)
            if scores[best_tag] > 300:
                # Use separator to preserve paragraph breaks
                txt = best_tag.get_text(separator="\n\n", strip=True)
                if txt and not is_junk_body(txt): candidates.append(txt)
    except: pass

    # Strategy 6: Greedy Paragraph Collection (Fallback for fragmented layouts)
    try:
        soup = BeautifulSoup(html_content, "lxml")
        paragraphs = []
        # Find all P tags anywhere
        for p in soup.find_all('p'):
            txt = p.get_text(strip=True)
            # Only count substantial paragraphs
            if len(txt) > 30:
                paragraphs.append(txt)
        
        if len(paragraphs) > 2:
            txt = "\n\n".join(paragraphs)
            if not is_junk_body(txt): candidates.append(txt)
    except: pass

    # FINAL SELECTION: Return the longest candidate (most comprehensive content)
    if not candidates: return None
    
    # Sort by length descending and return the longest unique candidate
    candidates.sort(key=len, reverse=True)
    
    # Optional: Clean up extra whitespace/newlines
    final_body = re.sub(r'\n{3,}', '\n\n', candidates[0]).strip()
    return final_body if len(final_body) > 100 else None

# Legacy wrappers
def extract_author(html: str) -> Optional[str]:
    return extract_author_v2(html).get("name")
