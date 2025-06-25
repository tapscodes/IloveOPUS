import os
import subprocess
from pathlib import Path
from config import SUPPORTED_EXTS

def get_downloads_folder():
    home = str(Path.home())
    downloads = os.path.join(home, "Downloads")
    return downloads if os.path.exists(downloads) else home

def get_output_filename(src):
    base, _ = os.path.splitext(src)
    return base + ".opus"

def convert_files(file_list, status_callback, progress_callback):
    total = len(file_list)
    for idx, src in enumerate(file_list):
        status_callback(f"Converting {os.path.basename(src)} ({idx+1}/{total})...")
        dst = get_output_filename(src)
        cmd = [
            "ffmpeg", "-y", "-i", src,
            "-c:a", "libopus", "-b:a", "320k",
            "-map_metadata", "0",
            dst
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            status_callback(f"Error converting {os.path.basename(src)}")
            continue
        progress_callback(int((idx+1)/total*100))
    status_callback("Done!")
    progress_callback(100)
