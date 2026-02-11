#!/usr/bin/env python3
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "0.0.0.0"
PORT = 8080

CAM_CMD = [
    "rpicam-vid",
    "-t", "0",
    "--codec", "mjpeg",
    "--rotation", "180",
    "--width", "640",
    "--height", "480",
    "--framerate", "20",
    "--quality", "80",
    "-o", "-"
]

class MJPEGHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
<!doctype html>
<html>
  <body style="margin:0;background:black;display:flex;align-items:center;justify-content:center;height:100vh;">
    <img src="/stream.mjpg">
  </body>
</html>
""")
            return

        if self.path != "/stream.mjpg":
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "multipart/x-mixed-replace; boundary=frame"
        )
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        proc = subprocess.Popen(CAM_CMD, stdout=subprocess.PIPE)
        buffer = b""

        try:
            while True:
                buffer += proc.stdout.read(4096)

                while True:
                    start = buffer.find(b"\xff\xd8")  # JPEG SOI
                    end   = buffer.find(b"\xff\xd9")  # JPEG EOI

                    if start != -1 and end != -1 and end > start:
                        frame = buffer[start:end + 2]
                        buffer = buffer[end + 2:]

                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(
                            f"Content-Length: {len(frame)}\r\n\r\n".encode()
                        )
                        self.wfile.write(frame)
                        self.wfile.write(b"\r\n")
                    else:
                        break
        finally:
            proc.kill()

HTTPServer((HOST, PORT), MJPEGHandler).serve_forever()
