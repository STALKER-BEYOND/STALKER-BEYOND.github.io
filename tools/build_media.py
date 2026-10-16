"""Build the Media page's files.

Drop original images (jpg, png, webp) and videos (mp4, mov, mkv, webm) into media-src/, then run
    python tools/build_media.py
from the repo root. Every new file is compressed into assets/media/ and gets an entry in
media/media.json with an empty title, category and credit to fill in. Existing entries keep their
text, and nothing is removed: delete an entry from media.json by hand to take it off the page.
Long videos belong on YouTube; add them to media.json by hand as {"type": "youtube", "youtube": "<id>"}.

Needs ffmpeg and ffprobe on PATH. media-src/ is git-ignored, so originals never get pushed.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "media-src"
OUT = ROOT / "assets" / "media"
DATA = ROOT / "media" / "media.json"

IMAGES = {".jpg", ".jpeg", ".png", ".webp"}
VIDEOS = {".mp4", ".mov", ".mkv", ".webm"}

FULL_IMAGE = 2560   # longest edge of the image shown in the viewer
FULL_VIDEO = 1920   # longest edge of the video shown in the viewer
THUMB = 960         # longest edge of grid thumbnails and video posters
PREVIEW = 640       # longest edge of the silent hover/featured preview clip
PREVIEW_SECONDS = 6
WARN_MB = 50        # GitHub warns above 50 MB and rejects files above 100 MB


def run(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
         "-of", "json", str(path)],
        check=True, capture_output=True, text=True).stdout
    info = json.loads(out)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    audio = any(s["codec_type"] == "audio" for s in info["streams"])
    duration = float(info.get("format", {}).get("duration") or 0)
    return video["width"], video["height"], audio, duration


def fit(w, h, edge):
    """Scale (w, h) so the longest edge is at most `edge`, keeping both sides even."""
    s = min(1, edge / max(w, h))
    return max(2, round(w * s / 2) * 2), max(2, round(h * s / 2) * 2)


def fresh(out, src):
    return out.exists() and out.stat().st_mtime >= src.stat().st_mtime


def build_image(src, key):
    w, h, _, _ = probe(src)
    fw, fh = fit(w, h, FULL_IMAGE)
    tw, th = fit(w, h, THUMB)
    full, thumb = OUT / f"{key}.webp", OUT / f"{key}-thumb.webp"
    if not fresh(full, src):
        run(["-i", str(src), "-vf", f"scale={fw}:{fh}", "-frames:v", "1", "-c:v", "libwebp", "-quality", "82", str(full)])
    if not fresh(thumb, src):
        run(["-i", str(src), "-vf", f"scale={tw}:{th}", "-frames:v", "1", "-c:v", "libwebp", "-quality", "72", str(thumb)])
    return {"type": "image", "src": f"assets/media/{full.name}", "thumb": f"assets/media/{thumb.name}", "w": fw, "h": fh}


def build_video(src, key):
    w, h, audio, duration = probe(src)
    fw, fh = fit(w, h, FULL_VIDEO)
    tw, th = fit(w, h, THUMB)
    pw, ph = fit(w, h, PREVIEW)
    full, poster = OUT / f"{key}.mp4", OUT / f"{key}-poster.webp"
    preview = OUT / f"{key}-preview.mp4"
    h264 = ["-c:v", "libx264", "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if not fresh(full, src):
        sound = ["-map", "0:a:0", "-c:a", "aac", "-b:a", "128k"] if audio else ["-an"]
        run(["-i", str(src), "-map", "0:v:0", *sound, "-vf", f"scale={fw}:{fh}", *h264, "-crf", "23", str(full)])
    if not fresh(poster, src):
        run(["-ss", f"{min(1.0, duration / 3):.2f}", "-i", str(src), "-frames:v", "1", "-vf", f"scale={tw}:{th}",
             "-c:v", "libwebp", "-quality", "75", str(poster)])
    if not fresh(preview, src):
        run(["-i", str(src), "-t", str(PREVIEW_SECONDS), "-an", "-vf", f"scale={pw}:{ph}", *h264, "-crf", "28", str(preview)])
    return {"type": "video", "src": f"assets/media/{full.name}", "thumb": f"assets/media/{poster.name}",
            "preview": f"assets/media/{preview.name}", "w": fw, "h": fh, "duration": round(duration, 1)}


def main():
    if not SRC.is_dir():
        sys.exit(f"Put your media in {SRC} first.")
    OUT.mkdir(parents=True, exist_ok=True)
    entries = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else []
    known = {e["id"]: e for e in entries}
    added = []
    for src in sorted(p for p in SRC.iterdir() if p.suffix.lower() in IMAGES | VIDEOS):
        key = "".join(c if c.isalnum() else "-" for c in src.stem.lower()).strip("-")
        print(f"  {src.name}")
        files = (build_image if src.suffix.lower() in IMAGES else build_video)(src, key)
        if key in known:
            known[key].update(files)  # refresh file info, keep the text you wrote
        else:
            entry = {"id": key, **files, "title": "", "category": "", "credit": "", "date": "", "featured": False}
            known[key] = entry
            added.append(entry)
    entries = added[::-1] + entries  # newest first
    DATA.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for f in OUT.iterdir():
        if f.stat().st_size > WARN_MB * 1024 * 1024:
            print(f"WARNING: {f.name} is {f.stat().st_size // 2**20} MB; GitHub rejects files over 100 MB.")
    print(f"{len(added)} new, {len(entries)} total in {DATA.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
