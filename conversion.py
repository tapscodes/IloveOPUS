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
def get_output_filename(src, convert_in_place=True):
    if convert_in_place:
        base, _ = os.path.splitext(src)
        return base + ".opus"
    else:
        # Export to Downloads/opus_exports
        home = str(Path.home())
        downloads = os.path.join(home, "Downloads")
        export_dir = os.path.join(downloads, "opus_exports")
        os.makedirs(export_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(src))[0]
        return os.path.join(export_dir, base + ".opus")

# Extract embedded cover art from the source file (mp3, m4a/alac, flac)
def extract_cover_art(src, resize_cover=True):
    ext = os.path.splitext(src)[1].lower()
    try:
        if ext == ".mp3":
            audio = MP3(src, ID3=ID3)
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    pic = Picture()
                    img_data = tag.data
                    if resize_cover:
                        img = Image.open(io.BytesIO(img_data))
                        img = img.convert("RGB")
                        img = img.resize((1000, 1000), Image.LANCZOS)
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG")
                        img_data = buf.getvalue()
                        pic.mime = "image/jpeg"
                    else:
                        pic.mime = tag.mime
                    pic.data = img_data
                    pic.type = 3
                    pic.desc = tag.desc or "Cover"
                    return pic
        elif ext in (".m4a", ".alac"):
            audio = MP4(src)
            covers = audio.tags.get('covr')
            if covers:
                cover = covers[0]
                pic = Picture()
                img_data = cover if isinstance(cover, bytes) else cover
                if resize_cover:
                    img = Image.open(io.BytesIO(img_data))
                    img = img.convert("RGB")
                    img = img.resize((1000, 1000), Image.LANCZOS)
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG")
                    img_data = buf.getvalue()
                    pic.mime = "image/jpeg"
                else:
                    pic.mime = "image/jpeg" if cover.imageformat == MP4Cover.FORMAT_JPEG else "image/png"
                pic.data = img_data
                pic.type = 3
                pic.desc = "Cover"
                return pic
        elif ext == ".flac":
            audio = FLAC(src)
            if audio.pictures:
                orig_pic = audio.pictures[0]
                img_data = orig_pic.data
                if resize_cover:
                    img = Image.open(io.BytesIO(img_data))
                    img = img.convert("RGB")
                    img = img.resize((1000, 1000), Image.LANCZOS)
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG")
                    img_data = buf.getvalue()
                    pic_mime = "image/jpeg"
                else:
                    pic_mime = orig_pic.mime
                pic = Picture()
                pic.data = img_data
                pic.type = 3
                pic.mime = pic_mime
                pic.desc = orig_pic.desc or "Cover"
                return pic
    except Exception:
        pass
    return None

# Convert files to OPUS and embed cover art if present
def convert_files(
    file_list,
    status_callback,
    progress_callback,
    resize_cover=True,
    convert_in_place=True,
    delete_original=False
):
    import logging
    from kivy.logger import Logger
    import shutil
    logging.basicConfig(
        filename="conversion_errors.log",
        filemode="a",
        level=logging.ERROR,
        format="%(asctime)s %(levelname)s: %(message)s"
    )

    # Find the bundled ffmpeg executable
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        error_msg = "FFmpeg executable not found in PATH. Conversion cannot proceed."
        status_callback(error_msg)
        logging.error(error_msg)
        Logger.error(f"conversion: {error_msg}")
        return

    total = len(file_list)
    failed_files = []
    for idx, src in enumerate(file_list):
        status_callback(f"Converting {os.path.basename(src)} ({idx+1}/{total})...")
        dst = get_output_filename(src, convert_in_place=convert_in_place)
        cmd = [
            ffmpeg_path, "-y", "-i", src,
            "-c:a", "libopus", "-b:a", "192k",
            "-map_metadata", "0",
            dst
        ]
        try:
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            error_msg = (
                f"Error converting {src}:\n"
                f"Command: {' '.join(cmd)}\n"
                f"Exit code: {e.returncode}\n"
                f"STDOUT:\n{e.stdout.decode(errors='replace')}\n"
                f"STDERR:\n{e.stderr.decode(errors='replace')}\n"
                "NOTE: If you see an error like 'version `OPENSSL_3.2.0' not found', "
                "the bundled ffmpeg binary may not be compatible with your system's libraries. "
                "Try using a different ffmpeg build or install ffmpeg from your distribution's package manager."
            )
            status_callback(f"Error converting {os.path.basename(src)} (see log for details)")
            logging.error(error_msg)
            Logger.error(f"conversion: {error_msg}")
            failed_files.append(src)
            continue

        try:
            pic = extract_cover_art(src, resize_cover=resize_cover)
            if pic:
                import base64
                opus = OggOpus(dst)
                opus["METADATA_BLOCK_PICTURE"] = [base64.b64encode(pic.write()).decode("ascii")]
                opus.save()
        except Exception as e:
            status_callback(f"Failed to embed cover art: {e}")
            logging.error(f"Failed to embed cover art for {src}: {e}")
            Logger.error(f"conversion: Failed to embed cover art for {src}: {e}")

        if delete_original:
            try:
                os.remove(src)
            except Exception as e:
                status_callback(f"Failed to delete original: {e}")
                logging.error(f"Failed to delete original file {src}: {e}")
                Logger.error(f"conversion: Failed to delete original file {src}: {e}")

        progress_callback(int((idx+1)/total*100))
    if failed_files:
        status_callback(f"Done! {len(failed_files)} file(s) failed. See log for details.")
    else:
        status_callback("Done!")
    progress_callback(100)
