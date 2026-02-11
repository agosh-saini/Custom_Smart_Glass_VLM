# Preceptra Puck

Motion-triggered vision-language model (VLM) on an MJPEG stream: one connection to the remote camera, a local pipe for viewing in the browser, and an optional web UI for stream, descriptions, and captures.

## Requirements

- Python 3.x
- See [requirements.txt](requirements.txt) for dependencies (e.g. `requests`, `numpy`, `PIL`, `fastapi`, `uvicorn`, `httpx`, `mlx-vlm` for VLM).

## Quick start

1. **Start the capture pipeline** (single connection to camera, pipe for viewing, motion detection, VLM on motion):

   ```bash
   python capture_frame.py "http://<PI_IP>:8080/stream.mjpg"
   ```

   Replace `<PI_IP>` with your Pi’s IP or hostname (e.g. `192.168.1.100` or `preceptra-1.local`).

   - **View stream in browser:** http://localhost:8765/stream.mjpg  
   - **VLM / motion:** uses the same single connection to the remote URL.

2. **Optional – Web UI** (stream + latest description + recent captures):

   ```bash
   python backend/main.py
   ```

   Open http://localhost:8000/ . The UI shows the piped stream (proxied), latest VLM description, and list of recent captures.

## Project layout

| Path | Description |
|------|-------------|
| **capture_frame.py** | Connects once to the remote MJPEG URL, pipes frames to port 8765, runs motion detection and VLM (via `mlx_vlm.generate`) when motion is detected. |
| **backend/main.py** | FastAPI app: serves `frontend/`, proxies the pipe stream at `/api/stream`, and exposes APIs for captures and latest description. |
| **frontend/index.html** | Single-page UI: live stream, latest VLM text, recent captures. |
| **captures/** | Saved frames and descriptions (timestamped `.jpg` and `.txt`). |

## License

MIT. See [LICENSE](LICENSE).
