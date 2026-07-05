import json
import threading
import uuid
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import speedtest

HOST = "127.0.0.1"
PORT = 8080

JOBS_LOCK = threading.Lock()
JOBS = {}


def _iso_now():
        return datetime.utcnow().isoformat() + "Z"


def _set_job(job_id, **fields):
        with JOBS_LOCK:
                if job_id in JOBS:
                        JOBS[job_id].update(fields)


def _run_speed_test(job_id):
        try:
                _set_job(job_id, status="running", phase="Initializing engine")
                st = speedtest.Speedtest()

                _set_job(job_id, phase="Finding best server")
                st.get_best_server()

                _set_job(job_id, phase="Measuring download speed")
                download = st.download() / 1_000_000

                _set_job(job_id, phase="Measuring upload speed")
                upload = st.upload() / 1_000_000

                ping = st.results.ping
                server = st.results.server or {}
                client = st.results.client or {}

                _set_job(
                        job_id,
                        status="completed",
                        phase="Completed",
                        finishedAt=_iso_now(),
                        result={
                                "download": round(download, 2),
                                "upload": round(upload, 2),
                                "ping": round(ping, 2),
                                "server": {
                                        "name": server.get("name", "Unknown"),
                                        "country": server.get("country", "Unknown"),
                                        "sponsor": server.get("sponsor", "Unknown"),
                                },
                                "client": {
                                        "ip": client.get("ip", "Unknown"),
                                        "isp": client.get("isp", "Unknown"),
                                        "country": client.get("country", "Unknown"),
                                },
                        },
                )
        except Exception as exc:
                _set_job(
                        job_id,
                        status="error",
                        phase="Failed",
                        finishedAt=_iso_now(),
                        error=str(exc),
                )


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Pulse Net Speed Lab</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Syne:wght@700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --ink: #0b1f2a;
            --paper: #f4efe7;
            --gold: #f3a712;
            --teal: #00a6a6;
            --red: #d1495b;
            --slate: #4b5865;
            --card: rgba(255, 255, 255, 0.72);
            --line: rgba(11, 31, 42, 0.15);
        }

        * { box-sizing: border-box; }

        body {
            margin: 0;
            min-height: 100vh;
            font-family: "Space Grotesk", sans-serif;
            color: var(--ink);
            background:
                radial-gradient(circle at 10% 20%, rgba(243, 167, 18, 0.35), transparent 35%),
                radial-gradient(circle at 90% 10%, rgba(0, 166, 166, 0.25), transparent 30%),
                linear-gradient(130deg, #f4efe7 0%, #e8f3f2 60%, #e9ecef 100%);
            display: grid;
            place-items: center;
            padding: 24px;
        }

        .shell {
            width: min(980px, 100%);
            border: 1px solid var(--line);
            background: var(--card);
            backdrop-filter: blur(8px);
            border-radius: 24px;
            padding: 24px;
            box-shadow: 0 20px 80px rgba(11, 31, 42, 0.15);
            animation: in 500ms ease-out;
        }

        @keyframes in {
            from { transform: translateY(12px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        .title {
            margin: 0 0 6px;
            font-family: "Syne", sans-serif;
            font-size: clamp(1.6rem, 4vw, 2.8rem);
            letter-spacing: 0.02em;
        }

        .subtitle {
            margin: 0 0 20px;
            color: var(--slate);
            font-size: 0.98rem;
        }

        .toolbar {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 18px;
        }

        button {
            border: none;
            border-radius: 999px;
            padding: 12px 20px;
            font-size: 0.95rem;
            font-weight: 700;
            cursor: pointer;
            transition: transform 160ms ease, box-shadow 160ms ease, opacity 160ms ease;
        }

        .run {
            background: linear-gradient(120deg, var(--gold), #ffd166);
            color: #1e1e1e;
            box-shadow: 0 10px 30px rgba(243, 167, 18, 0.32);
        }

        .run:hover { transform: translateY(-2px); }
        .run:disabled { opacity: 0.5; cursor: not-allowed; }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            border-radius: 999px;
            border: 1px solid var(--line);
            padding: 10px 14px;
            background: rgba(255, 255, 255, 0.8);
            font-weight: 500;
        }

        .dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--slate);
        }

        .running .dot { background: var(--teal); box-shadow: 0 0 0 6px rgba(0, 166, 166, 0.2); }
        .completed .dot { background: #2a9d8f; }
        .error .dot { background: var(--red); }

        .grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin-top: 10px;
        }

        .card {
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 16px;
            background: rgba(255, 255, 255, 0.78);
            min-height: 140px;
        }

        .label {
            margin: 0;
            font-size: 0.86rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--slate);
        }

        .value {
            margin: 12px 0 6px;
            font-size: clamp(1.4rem, 4vw, 2.2rem);
            font-weight: 700;
            line-height: 1;
        }

        .units {
            font-size: 0.92rem;
            color: var(--slate);
        }

        .meta {
            margin-top: 18px;
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 16px;
            background: rgba(255, 255, 255, 0.7);
            display: grid;
            gap: 8px;
            font-size: 0.95rem;
        }

        .phase {
            margin-top: 12px;
            color: var(--slate);
            font-weight: 500;
        }

        @media (max-width: 860px) {
            .grid {
                grid-template-columns: 1fr;
            }

            .shell {
                padding: 18px;
                border-radius: 18px;
            }
        }
    </style>
</head>
<body>
    <main class="shell">
        <h1 class="title">Pulse Net Speed Lab</h1>
        <p class="subtitle">Run a full network benchmark with a richer dashboard view.</p>

        <div class="toolbar">
            <button id="runBtn" class="run">Run Speed Test</button>
            <div id="statusPill" class="status-pill idle"><span class="dot"></span><span id="statusText">Idle</span></div>
        </div>

        <div class="grid">
            <section class="card">
                <p class="label">Download</p>
                <p id="download" class="value">--</p>
                <p class="units">Mbps</p>
            </section>
            <section class="card">
                <p class="label">Upload</p>
                <p id="upload" class="value">--</p>
                <p class="units">Mbps</p>
            </section>
            <section class="card">
                <p class="label">Ping</p>
                <p id="ping" class="value">--</p>
                <p class="units">ms</p>
            </section>
        </div>

        <p id="phase" class="phase">No test running.</p>

        <section id="meta" class="meta">
            <div><strong>Server:</strong> <span id="server">-</span></div>
            <div><strong>ISP / IP:</strong> <span id="client">-</span></div>
            <div><strong>Last finished:</strong> <span id="finished">-</span></div>
            <div><strong>Error:</strong> <span id="error">-</span></div>
        </section>
    </main>

    <script>
        const runBtn = document.getElementById("runBtn");
        const statusPill = document.getElementById("statusPill");
        const statusText = document.getElementById("statusText");
        const phaseText = document.getElementById("phase");

        const downloadEl = document.getElementById("download");
        const uploadEl = document.getElementById("upload");
        const pingEl = document.getElementById("ping");

        const serverEl = document.getElementById("server");
        const clientEl = document.getElementById("client");
        const finishedEl = document.getElementById("finished");
        const errorEl = document.getElementById("error");

        let pollId = null;

        function setStatus(status, text) {
            statusPill.className = `status-pill ${status}`;
            statusText.textContent = text;
        }

        function clearResult() {
            downloadEl.textContent = "--";
            uploadEl.textContent = "--";
            pingEl.textContent = "--";
            serverEl.textContent = "-";
            clientEl.textContent = "-";
            finishedEl.textContent = "-";
            errorEl.textContent = "-";
        }

        function applySnapshot(snapshot) {
            const status = snapshot.status || "idle";
            const phase = snapshot.phase || "No test running.";
            phaseText.textContent = phase;

            if (status === "running") {
                setStatus("running", "Running");
            } else if (status === "completed") {
                setStatus("completed", "Completed");
            } else if (status === "error") {
                setStatus("error", "Failed");
            } else {
                setStatus("idle", "Idle");
            }

            if (snapshot.result) {
                const r = snapshot.result;
                downloadEl.textContent = Number(r.download).toFixed(2);
                uploadEl.textContent = Number(r.upload).toFixed(2);
                pingEl.textContent = Number(r.ping).toFixed(2);
                serverEl.textContent = `${r.server.sponsor} - ${r.server.name}, ${r.server.country}`;
                clientEl.textContent = `${r.client.isp} / ${r.client.ip} (${r.client.country})`;
            }

            finishedEl.textContent = snapshot.finishedAt || "-";
            errorEl.textContent = snapshot.error || "-";
        }

        async function poll(jobId) {
            if (pollId) {
                clearInterval(pollId);
            }

            pollId = setInterval(async () => {
                const res = await fetch(`/api/tests/${jobId}`);
                const data = await res.json();
                applySnapshot(data);

                if (data.status === "completed" || data.status === "error") {
                    clearInterval(pollId);
                    pollId = null;
                    runBtn.disabled = false;
                }
            }, 1000);
        }

        runBtn.addEventListener("click", async () => {
            clearResult();
            runBtn.disabled = true;
            setStatus("running", "Running");
            phaseText.textContent = "Queueing test...";

            const res = await fetch("/api/tests", { method: "POST" });
            const data = await res.json();
            poll(data.jobId);
        });
    </script>
</body>
</html>
"""


class SpeedTestHandler(BaseHTTPRequestHandler):
        def _send_json(self, payload, status=HTTPStatus.OK):
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def _send_html(self, html):
                body = html.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def do_GET(self):
                path = urlparse(self.path).path

                if path == "/":
                        self._send_html(HTML_PAGE)
                        return

                if path.startswith("/api/tests/"):
                        job_id = path.split("/")[-1]
                        with JOBS_LOCK:
                                job = JOBS.get(job_id)

                        if not job:
                                self._send_json({"error": "Job not found"}, status=HTTPStatus.NOT_FOUND)
                                return

                        self._send_json(job)
                        return

                self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def do_POST(self):
                path = urlparse(self.path).path

                if path == "/api/tests":
                        job_id = str(uuid.uuid4())
                        with JOBS_LOCK:
                                JOBS[job_id] = {
                                        "jobId": job_id,
                                        "status": "queued",
                                        "phase": "Queued",
                                        "createdAt": _iso_now(),
                                        "finishedAt": None,
                                        "result": None,
                                        "error": None,
                                }

                        thread = threading.Thread(target=_run_speed_test, args=(job_id,), daemon=True)
                        thread.start()
                        self._send_json({"jobId": job_id}, status=HTTPStatus.ACCEPTED)
                        return

                self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

        def log_message(self, fmt, *args):
                return


def main():
        server = ThreadingHTTPServer((HOST, PORT), SpeedTestHandler)
        print(f"Speed test dashboard running at http://{HOST}:{PORT}")
        print("Press Ctrl+C to stop.")
        try:
                server.serve_forever()
        except KeyboardInterrupt:
                print("\nShutting down...")
        finally:
                server.server_close()


if __name__ == "__main__":
        main()