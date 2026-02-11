#!/usr/bin/env python3
"""Motion-triggered: one connection to remote MJPEG stream, piped to local server so you can view it while Python pulls frames."""

import io
import sys
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

import numpy as np
import requests
from PIL import Image

CAPTURES_DIR = Path(__file__).resolve().parent / "captures"
HTTP_TIMEOUT = 15
FRAME_INTERVAL = 0.4       # seconds between frame checks
MOTION_THRESHOLD = 12.0    # mean pixel delta (tune: higher = less sensitive)
MIN_SECONDS_BETWEEN_VLM = 2.0  # rate limit VLM calls
PIPE_PORT = 8765            # local stream: http://localhost:8765/stream.mjpg

# Your working command (single image, describe in detail)
VLM_MODEL = "mlx-community/Qwen2-VL-2B-Instruct-4bit"
VLM_PROMPT = "Describe this image in detail."
VLM_MAX_TOKENS = 2048
VLM_TEMP = 0.0


def jpg_to_gray(jpg: bytes) -> np.ndarray:
    """Decode JPEG to grayscale float array."""
    img = Image.open(io.BytesIO(jpg)).convert("L")
    return np.array(img, dtype=np.float32)


def motion_score(prev: np.ndarray, curr: np.ndarray) -> float:
    """Mean absolute pixel difference (0 = no change)."""
    if prev.shape != curr.shape:
        return float("inf")
    return float(np.mean(np.abs(curr - prev)))


def stream_loop(stream_url: str, latest_frame: list, lock: threading.Lock, stop: threading.Event):
    """Continuously read MJPEG stream and store the latest JPEG in latest_frame[0]."""
    while not stop.is_set():
        try:
            r = requests.get(stream_url, stream=True, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"\nStream error: {e}", file=sys.stderr)
            stop.wait(timeout=2)
            continue
        buf = b""
        for chunk in r.iter_content(chunk_size=8192):
            if stop.is_set():
                return
            if chunk:
                buf += chunk
            start = buf.find(b"\xff\xd8")
            end = buf.find(b"\xff\xd9")
            if start != -1 and end != -1 and end > start:
                jpg = buf[start : end + 2]
                buf = buf[end + 2 :]
                with lock:
                    latest_frame[0] = jpg
            if len(buf) > 10 * 1024 * 1024:
                buf = b""


def run_pipe_server_thread(port: int, latest_frame: list, lock: threading.Lock, stop: threading.Event):
    """Serve latest_frame as MJPEG so you can view the stream at http://localhost:PORT/stream.mjpg while Python uses the same source."""
    class StreamHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/" and self.path != "/stream.mjpg":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=--frame")
            self.end_headers()
            boundary = b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n"
            last_jpg = None
            while not stop.is_set():
                with lock:
                    jpg = latest_frame[0]
                if jpg is not None and jpg != last_jpg:
                    try:
                        self.wfile.write(boundary % len(jpg))
                        self.wfile.write(jpg)
                        self.wfile.write(b"\r\n")
                        self.wfile.flush()
                        last_jpg = jpg
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        break
                time.sleep(0.05)
        def log_message(self, format, *args):
            pass

    server = HTTPServer(("", port), StreamHandler)
    server.socket.settimeout(1.0)
    while not stop.is_set():
        try:
            server.handle_request()
        except Exception:
            pass


def run_vlm_command(image_path: str) -> str:
    """Run the exact command you pasted: python -m mlx_vlm.generate --model ... --prompt ... --image ... --max-tokens 2048 --temp 0.0"""
    path = str(Path(image_path).resolve())
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "mlx_vlm.generate",
            "--model",
            VLM_MODEL,
            "--prompt",
            VLM_PROMPT,
            "--image",
            path,
            "--max-tokens",
            str(VLM_MAX_TOKENS),
            "--temperature",
            str(VLM_TEMP),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    result = (out.stdout or "").strip()
    if out.returncode != 0 and out.stderr:
        result = result or out.stderr.strip()
    return result


def main():
    url = (sys.argv[1] if len(sys.argv) > 1 else "").strip() or input("Stream URL: ").strip()
    if not url:
        print("Usage: python capture_frame.py <stream_url>", file=sys.stderr)
        sys.exit(1)
    if "<" in url or ">" in url or "pi_ip" in url.lower() or "%3cpi_ip%3e" in url.lower():
        print("Replace <PI_IP> with your Pi's IP or hostname, e.g.:", file=sys.stderr)
        print('  python capture_frame.py "http://192.168.1.100:8080/stream.mjpg"', file=sys.stderr)
        print('  python capture_frame.py "http://preceptra-1.local:8080/stream.mjpg"', file=sys.stderr)
        sys.exit(1)
    CAPTURES_DIR.mkdir(exist_ok=True)

    latest_frame = [None]
    lock = threading.Lock()
    stop = threading.Event()
    t = threading.Thread(target=stream_loop, args=(url, latest_frame, lock, stop), daemon=True)
    t.start()
    pipe = threading.Thread(
        target=run_pipe_server_thread,
        args=(PIPE_PORT, latest_frame, lock, stop),
        daemon=True,
    )
    pipe.start()

    print("View stream (browser):  http://localhost:%s/stream.mjpg" % PIPE_PORT)
    print("VLM / motion (Python):  uses the single connection to remote %s" % url)
    print("Motion-triggered: running VLM when motion is detected; no new capture until VLM returns (Ctrl+C to exit).")
    prev_jpg = None
    prev_gray = None
    last_vlm_time = 0.0
    vlm_busy = False
    try:
        while True:
            time.sleep(FRAME_INTERVAL)
            if vlm_busy:
                continue
            with lock:
                jpg = latest_frame[0] if latest_frame[0] is not None else None
            if jpg is None:
                print("[no frame yet]")
                continue
            gray = jpg_to_gray(jpg)
            if prev_gray is None:
                prev_gray = gray
                prev_jpg = jpg
                continue
            score = motion_score(prev_gray, gray)
            print(f"[motion {score:.1f}]")
            if score >= MOTION_THRESHOLD:
                now = time.time()
                if now - last_vlm_time >= MIN_SECONDS_BETWEEN_VLM:
                    vlm_busy = True
                    print("→ motion detected, running VLM")
                    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    name = f"frame_{ts}.jpg"
                    out_path = CAPTURES_DIR / name
                    out_path.write_bytes(jpg)
                    print(out_path)
                    desc = run_vlm_command(str(out_path))
                    print(desc)
                    (CAPTURES_DIR / f"frame_{ts}.txt").write_text(desc, encoding="utf-8")
                    last_vlm_time = now
                    vlm_busy = False
            prev_gray = gray
            prev_jpg = jpg
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()


if __name__ == "__main__":
    main()
