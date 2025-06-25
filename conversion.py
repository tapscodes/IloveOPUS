import os
import subprocess
from pathlib import Path
from config import SUPPORTED_EXTS
from mutagen.oggopus import OggOpus
from mutagen.flac import Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC
from PIL import Image
import io

# Get the user's Downloads folder, or home if not present
def get_downloads_folder():
    home = str(Path.home())
    downloads = os.path.join(home, "Downloads")
    return downloads if os.path.exists(downloads) else home

# Generate output filename with .opus extension
def get_output_filename(src):
    base, _ = os.path.splitext(src)
    return base + ".opus"

# Extract embedded cover art from the source file (mp3, m4a/alac, flac)
def extract_cover_art(src):
    ext = os.path.splitext(src)[1].lower()
    try:
        if ext == ".mp3":
            audio = MP3(src, ID3=ID3)
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    pic = Picture()
                    # Resize image data to 1000x1000
                    img = Image.open(io.BytesIO(tag.data))
                    img = img.convert("RGB")
                    img = img.resize((1000, 1000), Image.LANCZOS)
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG")
                    pic.data = buf.getvalue()
                    pic.type = 3
                    pic.mime = "image/jpeg"
                    pic.desc = tag.desc or "Cover"
                    return pic
        elif ext in (".m4a", ".alac"):
            audio = MP4(src)
            covers = audio.tags.get('covr')
            if covers:
                cover = covers[0]
                pic = Picture()
                # Resize image data to 1000x1000
                img = Image.open(io.BytesIO(cover if isinstance(cover, bytes) else cover))
                img = img.convert("RGB")
                img = img.resize((1000, 1000), Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="JPEG")
                pic.data = buf.getvalue()
                pic.type = 3
                pic.mime = "image/jpeg"
                pic.desc = "Cover"
                return pic
        elif ext == ".flac":
            audio = FLAC(src)
            if audio.pictures:
                orig_pic = audio.pictures[0]
                # Resize image data to 1000x1000
                img = Image.open(io.BytesIO(orig_pic.data))
                img = img.convert("RGB")
                img = img.resize((1000, 1000), Image.LANCZOS)
                buf = io.BytesIO()
                img.save(buf, format="JPEG")
                pic = Picture()
                pic.data = buf.getvalue()
                pic.type = 3
                pic.mime = "image/jpeg"
                pic.desc = orig_pic.desc or "Cover"
                return pic
    except Exception:
        pass
    return None

# Convert files to OPUS and embed cover art if present
def convert_files(file_list, status_callback, progress_callback):
    total = len(file_list)
    for idx, src in enumerate(file_list):
        status_callback(f"Converting {os.path.basename(src)} ({idx+1}/{total})...")
        dst = get_output_filename(src)
        # ffmpeg command to convert to OPUS
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

        # --- Extract and embed cover art from source file ---
        try:
            pic = extract_cover_art(src)
            if pic:
                import base64
                opus = OggOpus(dst)
                # METADATA_BLOCK_PICTURE must be base64-encoded for Opus
                opus["METADATA_BLOCK_PICTURE"] = [base64.b64encode(pic.write()).decode("ascii")]
                opus.save()
            # else: no cover art found, skip embedding
        except Exception as e:
            status_callback(f"Failed to embed cover art: {e}")

        progress_callback(int((idx+1)/total*100))
    status_callback("Done!")
    progress_callback(100)
