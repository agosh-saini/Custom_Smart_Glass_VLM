## Preceptra Puck – llama.cpp (Qwen3-VL-2B) Setup

This README documents the **native llama.cpp + Qwen3-VL-2B-Instruct** path, which replaces the original MLX-VLM backend. The motion detection, capture logic, and web UI remain the same; only the VLM implementation changes.

### 1. Prerequisites

- **Hardware**: Apple Silicon (Metal) recommended.
- **Python**: 3.x
- **Dependencies**:
  - Install from `requirements.txt` (already includes `huggingface_hub`, `requests`, `numpy`, `Pillow`, FastAPI, etc.):

    ```bash
    pip install -r requirements.txt
    ```

  - `git`, `cmake`, and a C/C++ toolchain (for building `llama.cpp`).

### 2. Download Qwen3-VL-2B GGUF models

Use the helper script to download the text model and vision projector from the official Qwen GGUF repo.

From the project root:

```bash
python download_qwen3vl_gguf.py --output-dir .
```

This will download (by default) into the current directory:

- `Qwen3VL-2B-Instruct-Q4_K_M.gguf`
- `mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf`

The script will print the resolved paths and an example `MODEL_PATH=... MMPROJ_PATH=...` invocation for the server.

> You can override filenames, precision, or repo with:
> `--llm`, `--mmproj`, and `--repo`. See `download_qwen3vl_gguf.py` for details.

### 3. Build llama.cpp with Metal

From the project root, run:

```bash
scripts/build_llama_cpp.sh
```

What this does:

- Clones `https://github.com/ggml-org/llama.cpp` into `./llama.cpp` (or uses an existing clone).
- Configures with `-DGGML_METAL=ON`.
- Builds `llama-server` in `llama.cpp/build/bin/llama-server`.

If you prefer a different location, set `LLAMA_CPP_DIR` before running:

```bash
LLAMA_CPP_DIR=/path/to/llama.cpp scripts/build_llama_cpp.sh
```

### 4. Start the llama.cpp vision server (Qwen3-VL-2B)

In **a separate terminal**, from the project root:

```bash
scripts/start_llama_server.sh
```

Defaults:

- Uses `./Qwen3VL-2B-Instruct-Q4_K_M.gguf` as the main model.
- Uses `./mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf` as the projector.
- Binds to `http://127.0.0.1:8080`.
- Exposes:
  - Native llama.cpp completion endpoint: `POST /completion`
  - OpenAI-compatible chat endpoint: `POST /v1/chat/completions`

You can override paths and settings with environment variables, e.g.:

```bash
MODEL_PATH=/path/to/Qwen3VL-2B-Instruct-Q4_K_M.gguf \
MMPROJ_PATH=/path/to/mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf \
PORT=8080 \
CTX_SIZE=2048 \
NGL=99 \
scripts/start_llama_server.sh
```

The script will validate that:

- `llama.cpp/build/bin/llama-server` exists.
- The specified `MODEL_PATH` and `MMPROJ_PATH` files exist.

### 5. Run motion-triggered capture with llama.cpp VLM

The main driver remains `capture_frame.py`, but it now calls the local llama.cpp server instead of `mlx_vlm`.

In another terminal, from the project root:

```bash
python capture_frame.py "http://<PI_IP>:8080/stream.mjpg"
```

Replace `<PI_IP>` with your Pi’s IP or hostname, e.g.:

- `http://192.168.1.100:8080/stream.mjpg`
- `http://preceptra-1.local:8080/stream.mjpg`

Behavior:

- Creates a single connection to the remote MJPEG stream.
- Pipes frames to a local MJPEG server at `http://localhost:8765/stream.mjpg`.
- Does simple frame-to-frame motion detection.
- When motion exceeds the configured threshold:
  - Saves the current frame as `captures/frame_<timestamp>.jpg`.
  - Sends the saved image to the local llama.cpp vision server (`POST /completion` with `image_data`).
  - Stores the decoded text response as `captures/frame_<timestamp>.txt`.

Key details in `capture_frame.py`:

- **Server configuration**:

  ```python
  LLAMA_SERVER_URL = "http://127.0.0.1:8080/completion"
  VLM_PROMPT = "Describe this image in detail."
  VLM_MAX_TOKENS = 256
  VLM_TEMP = 0.0
  ```

  You can adjust these constants to change the prompt, max tokens, or temperature.

- **API format**:

  - Uses the llama.cpp `/completion` endpoint with `image_data`:

    ```jsonc
    {
      "prompt": "USER:[img-1]Describe this image in detail.\nASSISTANT:",
      "n_predict": 256,
      "temperature": 0.0,
      "image_data": [
        {
          "id": 1,
          "data": "<base64-encoded JPEG bytes>"
        }
      ]
    }
    ```

  - The response is parsed from the `content` field and written alongside the image.

### 6. Optional: Web UI (unchanged)

The FastAPI backend and static frontend still work with this new VLM backend because they only read from the `captures/` directory.

1. Start the backend:

   ```bash
   python backend/main.py
   ```

2. Open the UI:

   - Visit `http://localhost:8000/` in your browser.

   You will see:

   - Live stream proxied from the pipe server (`/api/stream`).
   - Latest VLM description (reads the most recent `captures/frame_*.txt`).
   - List of recent captures with thumbnail and text.

### 7. Summary of files involved

- `capture_frame.py`  
  Motion detection, frame capture, and calls to the local llama.cpp vision server with Qwen3-VL-2B.

- `download_qwen3vl_gguf.py`  
  Helper script to download `Qwen3-VL-2B-Instruct` GGUF and mmproj files from Hugging Face.

- `scripts/build_llama_cpp.sh`  
  Clones and builds `llama.cpp` with Metal support and produces the `llama-server` binary.

- `scripts/start_llama_server.sh`  
  Starts `llama-server` configured for Qwen3-VL-2B with Metal offload.

- `backend/main.py` & `frontend/index.html`  
  Web UI for viewing the stream and captures (unchanged; consume the `.jpg`/`.txt` outputs produced by `capture_frame.py`).

