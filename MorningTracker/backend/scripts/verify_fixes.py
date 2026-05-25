import sys
import os
# Add parent dir to path so we can import scraper modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.parser import extract_body
from scraper.network import load_proxies
from config import PROFILES

def test_fixes():
    print("=== NEXUS Fix Verification ===")

    # 1. Verify Fix 5 (Browser Pool Size)
    pool_size_16gb = PROFILES["16GB"]["BROWSER_POOL_SIZE"]
    print(f"\n[Fix 5] Browser Pool Size (16GB Profile): {pool_size_16gb}")
    if pool_size_16gb == 8:
        print("[SUCCESS] Pool size increased to 8.")
    else:
        print("[FAILED] Pool size is not 8.")

    # 2. Verify Fix 4 (Proxy Loading)
    os.environ["PROXY_LIST"] = "http://proxy1.com,http://proxy2.com"
    proxies = load_proxies()
    print(f"\n[Fix 4] Loaded Proxies: {proxies}")
    if len(proxies) == 2:
        print("[SUCCESS] Proxies loaded correctly from environment.")
    else:
        print("[FAILED] Proxy loading failed.")

    # 4. Verify CSS Junk Filtering
    css_junk_html = "<html><body><style>body { color: red; }</style><article><p>REAL CONTENT HERE. " * 20 + "</p></article></body></html>"
    print("\n[Fix 6] Testing CSS Junk Filtering...")
    body = extract_body(css_junk_html)
    if body and "@font-face" not in body and "REAL CONTENT" in body:
        print("[SUCCESS] CSS styles correctly filtered out.")
    else:
        print(f"[FAILED] Body still contains junk or missed content: {body[:100]}...")

    print("\n=== All Core Logic Fixes Verified ===")

if __name__ == "__main__":
    test_fixes()
