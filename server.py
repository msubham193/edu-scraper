"""
server.py
---------
Flask web server for the Education Institute Scraper.
Provides:
  POST /api/scrape       -> start a scrape job
  GET  /api/stream/<id>  -> SSE stream of progress + results
  GET  /api/download/<id>-> download the generated Excel file
  GET  /                 -> serve the HTML UI
"""

import os
import sys
import uuid
import json
import time
import threading
import queue

# Force UTF-8
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, Response, send_file, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

# In-memory job store: job_id -> { status, results, excel_path, events_queue, ... }
JOBS: dict[str, dict] = {}
OUTPUTS_DIR = Path("outputs")
OUTPUTS_DIR.mkdir(exist_ok=True)


# ─── SSE Helper ──────────────────────────────────────────────────────────────

def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ─── Scraping Worker ─────────────────────────────────────────────────────────

def run_scrape_job(job_id: str, query: str, num_results: int, institute_type: str = 'All Types'):
    """Runs in a background thread. Pushes SSE events into the job's queue."""
    job = JOBS[job_id]
    q: queue.Queue = job["queue"]

    def push(event: str, data: dict):
        q.put(sse_event(event, data))

    try:
        job["status"] = "searching"
        push("status", {"message": f"Searching Google for: {query}", "phase": "search"})

        # ── Step 1: Search ────────────────────────────────────────────────────
        from google_search import google_search
        urls = google_search(query, num_results=num_results)

        if not urls:
            push("error", {"message": "No URLs found. Try a different query."})
            job["status"] = "error"
            q.put(None)  # sentinel
            return

        push("search_done", {"count": len(urls), "urls": urls})

        # ── Step 2: Scrape each URL ───────────────────────────────────────────
        job["status"] = "scraping"
        from extractor import extract_all
        import requests as req_lib
        from fake_useragent import UserAgent
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse
        import random

        ua = UserAgent()
        HEADERS = {
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
            "Connection": "keep-alive",
        }
        CONTACT_PATHS = ["/contact", "/contact-us", "/about", "/about-us", "/enquiry", "/reach-us"]

        def fetch(url, timeout=15, retries=2):
            for _ in range(retries):
                try:
                    r = req_lib.get(url, headers={**HEADERS, "User-Agent": ua.random},
                                    timeout=timeout, allow_redirects=True)
                    if r.status_code == 200:
                        return r.text
                    elif r.status_code in (401, 403, 404, 429):
                        return None
                except Exception:
                    pass
            return None

        results = []
        for i, url in enumerate(urls):
            push("progress", {
                "current": i + 1,
                "total": len(urls),
                "url": url,
                "percent": round((i / len(urls)) * 100)
            })

            html = fetch(url)
            if not html:
                continue

            result = extract_all(html, url)

            # Try contact sub-pages
            base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            for path in CONTACT_PATHS:
                sub_html = fetch(base + path, timeout=8, retries=1)
                if sub_html:
                    sub = extract_all(sub_html, base + path)
                    result["emails"] = list(set(result["emails"] + sub["emails"]))
                    result["phones"] = list(set(result["phones"] + sub["phones"]))

            result["emails"] = sorted(set(result["emails"]))
            result["phones"] = sorted(set(result["phones"]))
            result["institute_type"] = institute_type
            results.append(result)

            # Push the new row immediately for live table update
            push("row", {
                "index": len(results),
                "name": result.get("name", ""),
                "url": result.get("url", ""),
                "emails": result.get("emails", []),
                "phones": result.get("phones", []),
                "institute_type": institute_type,
            })

            time.sleep(random.uniform(1.0, 2.0))

        job["results"] = results

        # ── Step 3: Export Excel ──────────────────────────────────────────────
        push("status", {"message": "Generating Excel file...", "phase": "export"})
        from exporter import export_to_excel
        safe_q = "".join(c if c.isalnum() or c in " _-" else "_" for c in query)[:40]
        filename = f"{safe_q.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        output_path = OUTPUTS_DIR / filename
        export_to_excel(results, str(output_path))
        job["excel_path"] = str(output_path)
        job["excel_name"] = filename

        push("done", {
            "total": len(results),
            "with_email": sum(1 for r in results if r.get("emails")),
            "with_phone": sum(1 for r in results if r.get("phones")),
            "both": sum(1 for r in results if r.get("emails") and r.get("phones")),
            "download_id": job_id,
        })
        job["status"] = "done"

    except Exception as e:
        push("error", {"message": str(e)})
        job["status"] = "error"
    finally:
        q.put(None)  # sentinel to close SSE stream


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/scrape", methods=["POST"])
def start_scrape():
    data = request.get_json()
    query = (data.get("query") or "").strip()
    num_results = int(data.get("num_results") or 20)
    num_results = max(5, min(50, num_results))  # clamp 5-50
    institute_type = (data.get("institute_type") or "All Types").strip()

    if not query:
        return jsonify({"error": "Query is required"}), 400

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {
        "id": job_id,
        "query": query,
        "num_results": num_results,
        "institute_type": institute_type,
        "status": "pending",
        "results": [],
        "excel_path": None,
        "excel_name": None,
        "queue": queue.Queue(),
    }

    # Run scraping in background thread
    t = threading.Thread(target=run_scrape_job, args=(job_id, query, num_results, institute_type), daemon=True)
    t.start()

    return jsonify({"job_id": job_id})


@app.route("/api/stream/<job_id>")
def stream(job_id: str):
    if job_id not in JOBS:
        return jsonify({"error": "Job not found"}), 404

    def generate():
        q = JOBS[job_id]["queue"]
        # Send heartbeat first
        yield sse_event("connected", {"job_id": job_id})
        while True:
            try:
                event = q.get(timeout=60)
                if event is None:
                    break
                yield event
            except queue.Empty:
                # Keep-alive comment
                yield ": keep-alive\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@app.route("/api/download/<job_id>")
def download(job_id: str):
    job = JOBS.get(job_id)
    if not job or not job.get("excel_path"):
        return jsonify({"error": "File not ready"}), 404
    return send_file(
        job["excel_path"],
        as_attachment=True,
        download_name=job["excel_name"],
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route("/api/status/<job_id>")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Not found"}), 404
    return jsonify({
        "status": job["status"],
        "count": len(job["results"]),
        "ready": job["excel_path"] is not None,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\n" + "="*55)
    print("  Education Institute Scraper - Web UI")
    print(f"  Starting server on port: {port}")
    print("="*55 + "\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
