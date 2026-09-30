"""Download FRED macro series for ML overlay features."""
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, ".")

# ── Extract API key from credentials file ─────────────────────────────────
cred_path = Path("C:/Users/david/OneDrive/Documents/fx-prival/fred-credentials.txt")
content = cred_path.read_text(encoding="utf-8")
m = re.search(r"FRED_API_KEY\s*=\s*['\"]([^'\"]+)['\"]", content)
if not m:
    print("ERROR: Could not extract API key")
    sys.exit(1)
API_KEY = m.group(1)
print(f"API key: {API_KEY[:8]}...")

# ── Series to download ────────────────────────────────────────────────────
# Daily series: observable at close of date t (no publication lag concern)
# Monthly series: released with ~45-day lag → shift by publication buffer
SERIES = {
    "DGS3MO": "US 3M Treasury yield (daily)",
    "DGS10": "US 10Y Treasury yield (daily)",
    "T10Y3M": "US 10Y-3M yield spread (daily)",
    "VIXCLS": "VIX close (daily, market fear)",
    "CPIAUCSL": "CPI All Urban (monthly, ~45d lag)",
    "UNRATE": "Unemployment rate (monthly, ~45d lag)",
}

START = "2014-01-01"
END = datetime.now().strftime("%Y-%m-%d")
OUT_DIR = Path("data/raw/fred")
OUT_DIR.mkdir(parents=True, exist_ok=True)

for series_id, desc in SERIES.items():
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={API_KEY}"
        f"&file_type=json&observation_start={START}&observation_end={END}"
    )
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        obs = data.get("observations", [])
        rows = [
            {"date": o["date"], "value": o.get("value")}
            for o in obs if o.get("value") not in (None, ".")
        ]
        out = OUT_DIR / f"{series_id}.csv"
        with open(out, "w", encoding="utf-8") as f:
            f.write("date,value\n")
            for r in rows:
                f.write(f"{r['date']},{r['value']}\n")
        print(f"  {series_id}: {len(rows)} observations -> {out.name}")
    except Exception as e:
        print(f"  {series_id}: ERROR {e}")

print("\nDone.")