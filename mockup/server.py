"""커리어노트 목업 서버 (가상 서비스, docs/design-stage1.md 4장).

- 127.0.0.1에서만 받음
- GET  /?s=<run_id>         : 화면 (mockup/static/)
- GET  /api/session?s=<id>  : 이 실행에 배정된 조건, 내용, 버튼 순서를 설정 파일에서 풀어서 돌려줌
- POST /event               : 페이지 이벤트를 JSONL 한 줄로 추가 (서버 시각 KST를 붙임)

조건은 배정 파일(mockup/runtime/assignments/<run_id>.json)과 configs/ 값으로만 정해짐.
조건별 코드 분기는 없음 (CLAUDE.md 6장).

실행: python -I mockup/server.py --port 8765
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from session import ASSIGN_DIR, EVENT_LOG, STATIC_DIR, resolve  # noqa: E402

KST = timezone(timedelta(hours=9))
RUN_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
WRITE_LOCK = threading.Lock()  # 동시에 들어온 이벤트가 한 줄에 섞이지 않게 함


class Handler(SimpleHTTPRequestHandler):
    event_log: Path = EVENT_LOG

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self):
        # 캐시 때문에 이전 실행 화면이 섞이지 않게 함
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _json(self, code: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/session":
            run_id = parse_qs(url.query).get("s", [""])[0]
            if not RUN_ID_RE.match(run_id):
                return self._json(400, {"error": "bad run_id"})
            try:
                return self._json(200, resolve(run_id))
            except FileNotFoundError:
                return self._json(404, {"error": "unknown run_id"})
        if url.path not in ("/", "/index.html", "/app.js", "/style.css"):
            return self.send_error(404)
        return super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/event":
            return self.send_error(404)
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        try:
            event = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self.send_error(400, "invalid json")
        if not isinstance(event, dict) or not RUN_ID_RE.match(str(event.get("run_id", ""))):
            return self.send_error(400, "bad run_id")
        event["server_ts"] = datetime.now(KST).isoformat(timespec="milliseconds")
        self.event_log.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False) + "\n"
        with WRITE_LOCK, self.event_log.open("a", encoding="utf-8") as f:
            f.write(line)
        self.send_response(204)
        self.end_headers()

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--log", type=Path, default=EVENT_LOG)
    args = parser.parse_args()
    Handler.event_log = args.log
    ASSIGN_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"serving http://127.0.0.1:{args.port}/  log -> {args.log}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
