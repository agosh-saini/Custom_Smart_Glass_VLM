"""
Backend for the capture_frame UI. Serves the frontend and APIs for stream URL and captures.
Run capture_frame.py separately; this only reads captures/ and proxies the pipe stream.
"""
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

# Must match capture_frame.py
PIPE_PORT = 8765
PIPE_URL = f"http://127.0.0.1:{PIPE_PORT}/stream.mjpg"
CAPTURES_DIR = Path(__file__).resolve().parent.parent / "captures"

app = FastAPI(title="Preceptra Puck UI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/stream_url")
def get_stream_url():
    """URL for the MJPEG stream. Prefer /api/stream (proxied) so the frontend works same-origin."""
    return {"url": "/api/stream"}


@app.get("/api/stream")
async def proxy_stream():
    """Proxy the pipe stream so the frontend can use same-origin <img src='/api/stream'>."""
    async def stream():
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("GET", PIPE_URL) as r:
                    r.raise_for_status()
                    async for chunk in r.aiter_bytes():
                        yield chunk
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            # Pipe not running or not responding
            yield b""
    return StreamingResponse(
        stream(),
        media_type="multipart/x-mixed-replace; boundary=--frame",
    )


@app.get("/api/captures")
def list_captures():
    """List recent captures (frame_*.jpg + frame_*.txt), newest first."""
    if not CAPTURES_DIR.exists():
        return {"captures": []}
    pairs = []
    for jpg in sorted(CAPTURES_DIR.glob("frame_*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True):
        ts = jpg.stem.replace("frame_", "")
        txt = CAPTURES_DIR / f"frame_{ts}.txt"
        desc = ""
        if txt.exists():
            desc = txt.read_text(encoding="utf-8").strip()
        pairs.append({
            "id": ts,
            "image_url": f"/api/captures/{ts}/image",
            "description": desc,
        })
    return {"captures": pairs[:50]}


@app.get("/api/captures/{capture_id}/image")
def get_capture_image(capture_id: str):
    """Serve one capture image by id (e.g. 2026-02-10_16-11-29)."""
    from fastapi.responses import FileResponse
    path = CAPTURES_DIR / f"frame_{capture_id}.jpg"
    if not path.is_file():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(path, media_type="image/jpeg")


@app.get("/api/latest")
def get_latest():
    """Latest VLM description (from the most recent capture .txt)."""
    if not CAPTURES_DIR.exists():
        return {"text": ""}
    txts = list(CAPTURES_DIR.glob("frame_*.txt"))
    if not txts:
        return {"text": ""}
    latest = max(txts, key=lambda p: p.stat().st_mtime)
    return {"text": latest.read_text(encoding="utf-8").strip()}


# Serve frontend last so routes take precedence
frontend_path = Path(__file__).resolve().parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
