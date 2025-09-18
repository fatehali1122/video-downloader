import os
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

FFMPEG_DIR = os.path.join(os.getcwd(), "ffmpeg", "bin")

COMMON_RESOLUTIONS = ["360p", "480p", "720p", "1080p"]

def get_available_formats(url):

    formats_dict = {}

    ydl_opts = {"quiet": True, "no_warnings": True}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])

    for res in COMMON_RESOLUTIONS:
        target_h = int(res.replace("p", ""))

        candidates = [
            f for f in formats
            if f.get("vcodec") != "none"
            and f.get("height")
            and f.get("height") >= target_h
        ]
        if candidates:
            best_match = min(candidates, key=lambda x: x.get("height"))
            actual_h = best_match["height"]
            formats_dict[res] = f"bestvideo[height={actual_h}]+bestaudio/best"

    audio_formats = [f for f in formats if f.get("acodec") != "none" and f.get("vcodec") == "none"]
    if audio_formats:
        best_audio = max(audio_formats, key=lambda x: x.get("abr") or 0)
        formats_dict["Audio only"] = best_audio["format_id"]

    return formats_dict


def pick_nearest_format(requested, available_formats):

    if requested in available_formats:
        return available_formats[requested]

    if requested != "Audio only":
        try:
            target = int(requested.replace("p", ""))
            # numeric resolutions from keys
            res_list = [int(k.replace("p", "")) for k in available_formats.keys() if k.endswith("p")]
            res_list.sort(reverse=True)
            for r in res_list:
                if r <= target:
                    return available_formats[f"{r}p"]
        except ValueError:
            pass

    return available_formats.get("Audio only", "bestvideo+bestaudio/best")


def download_with_format(url, format_str, output_dir="downloads", progress_hook=None):

    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        "format": format_str,
        "outtmpl": os.path.join(output_dir, "%(title)s.50s [%(id)s].%(ext)s"),
        "restrictfilenames": True,
        "merge_output_format": "mp4",   # always merge to mp4
        "noplaylist": True,
    }
    if progress_hook:
        ydl_opts["progress_hooks"] = [progress_hook]

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except DownloadError:
        print(f"⚠️ Primary format {format_str} failed, falling back to best...")
        fallback_opts = ydl_opts.copy()
        fallback_opts["format"] = "bestvideo+bestaudio/best"
        with YoutubeDL(fallback_opts) as ydl:
            ydl.download([url])
