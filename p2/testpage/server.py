"""P2 시험 페이지 서버.

- 127.0.0.1에서만 받는다 (외부 접근 차단)
- GET: 이 폴더의 정적 파일
- POST /event: 페이지가 보낸 이벤트를 JSONL로 한 줄씩 추가 (서버 시각을 붙임)

실행: python -I p2/testpage/server.py --port 8765 --log p2/testpage/events.jsonl
"""

import argparse
import json
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Handler(SimpleHTTPRequestHandler):
    log_path: Path

    def do_POST(self):
        if self.path != "/event":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            event = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_error(400, "invalid json")
            return
        event["server_ts"] = datetime.now(timezone.utc).isoformat()
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        self.send_response(204)
        self.end_headers()

    def log_message(self, fmt, *args):
        # 요청 로그는 콘솔에만 짧게
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--log", type=Path, default=Path(__file__).with_name("events.jsonl"))
    args = parser.parse_args()

    Handler.log_path = args.log
    handler = partial(Handler, directory=str(Path(__file__).parent))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"serving http://127.0.0.1:{args.port}/  log -> {args.log}")
    server.serve_forever()


if __name__ == "__main__":
    main()
