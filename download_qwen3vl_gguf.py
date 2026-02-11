#!/usr/bin/env python3
"""
Download Qwen3-VL-2B-Instruct GGUF files from the official Qwen Hugging Face repo
for use with a llama.cpp vision server (e.g. capture_frame.py + scripts/start_llama_server.sh).

Repo: https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct-GGUF

Downloads to the current directory (or --output-dir):
  - LLM: Qwen3VL-2B-Instruct-Q4_K_M.gguf (~1.11 GB) — default; or Q8_0 (~1.83 GB)
  - Projector: mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf (~445 MB) or F16 (~819 MB)

Requires: pip install huggingface_hub
"""

from __future__ import annotations

import argparse
import os
from typing import Tuple

try:
    from huggingface_hub import hf_hub_download
except ImportError as e:
    raise ImportError("huggingface_hub is required. Install with: pip install huggingface_hub") from e


REPO_ID = "Qwen/Qwen3-VL-2B-Instruct-GGUF"
DEFAULT_LLM_FILENAME = "Qwen3VL-2B-Instruct-Q4_K_M.gguf"
DEFAULT_MMPROJ_FILENAME = "mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf"


def download_gguf(
    output_dir: str = ".",
    llm_filename: str = DEFAULT_LLM_FILENAME,
    mmproj_filename: str = DEFAULT_MMPROJ_FILENAME,
    repo_id: str = REPO_ID,
) -> Tuple[str, str]:
    """Download LLM and mmproj GGUF files. Returns (path_to_llm, path_to_mmproj)."""
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Downloading from {repo_id}")
    print(f"Output directory: {output_dir}\n")

    print(f"1/2 LLM (text): {llm_filename}")
    llm_path = hf_hub_download(
        repo_id=repo_id,
        filename=llm_filename,
        local_dir=output_dir,
        local_dir_use_symlinks=False,
    )
    print(f"   -> {llm_path}\n")

    print(f"2/2 Projector (vision): {mmproj_filename}")
    mmproj_path = hf_hub_download(
        repo_id=repo_id,
        filename=mmproj_filename,
        local_dir=output_dir,
        local_dir_use_symlinks=False,
    )
    print(f"   -> {mmproj_path}\n")

    print("Done. Start the llama.cpp vision server with:")
    print(f"  MODEL_PATH={os.path.basename(llm_path)} MMPROJ_PATH={os.path.basename(mmproj_path)} \\")
    print("    scripts/start_llama_server.sh")
    return llm_path, mmproj_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Qwen3-VL-2B-Instruct GGUF from Qwen/Qwen3-VL-2B-Instruct-GGUF "
        "for use with llama.cpp vision server.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=".",
        help="Directory to save GGUF files (default: current directory)",
    )
    parser.add_argument(
        "--llm",
        type=str,
        default=DEFAULT_LLM_FILENAME,
        help=f"LLM GGUF filename (default: {DEFAULT_LLM_FILENAME}). Options: Q4_K_M.gguf, Q8_0.gguf, F16.gguf",
    )
    parser.add_argument(
        "--mmproj",
        type=str,
        default=DEFAULT_MMPROJ_FILENAME,
        help=f"MMProj GGUF filename (default: {DEFAULT_MMPROJ_FILENAME}). "
        "Options: mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf, F16.gguf",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=REPO_ID,
        help=f"Hugging Face repo (default: {REPO_ID})",
    )
    args = parser.parse_args()

    download_gguf(
        output_dir=args.output_dir,
        llm_filename=args.llm,
        mmproj_filename=args.mmproj,
        repo_id=args.repo,
    )


if __name__ == "__main__":
    main()

