#!/usr/bin/env python3
"""
HStream Extractor
Bulk downloader + optional subtitle muxer for hstream.moe.

Requires hanime-plugin for hstream.moe support.
Subtitles: try old host first, then imoto-str.ane-h.xyz.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

import requests
from tqdm import tqdm


def ensure_dependencies():
    print("Checking / installing dependencies...")
    try:
        subprocess.run(
            [
                sys.executable, "-m", "pip", "install", "--upgrade",
                "yt-dlp", "requests", "tqdm", "hanime-plugin",
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"pip install failed: {e}")
        sys.exit(1)

    for pkg in ("aria2c", "ffmpeg"):
        if subprocess.run(["which", pkg], capture_output=True).returncode != 0:
            print(f"WARNING: '{pkg}' not found in PATH.")
    print("Dependency check done.\n")


def download_video(
    url: str,
    dest: Path,
    cookies_file: Path | None = None,
    cookies_from_browser: str | None = None,
) -> Path:
    output_template = str(dest / "%(title)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "--downloader", "aria2c",
        "--downloader-args", "aria2c:-x 16 -s 16 -k 1M",
        "--concurrent-fragments", "8",
        "-o", output_template,
        "--no-mtime",
    ]
    if cookies_file:
        cmd.extend(["--cookies", str(cookies_file)])
    elif cookies_from_browser:
        cmd.extend(["--cookies-from-browser", cookies_from_browser])
    cmd.append(url)

    print(f"Downloading video: {url}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print("Retrying with --downloader ffmpeg ...")
        cmd2 = [
            "yt-dlp", "--downloader", "ffmpeg",
            "-o", output_template, "--no-mtime",
        ]
        if cookies_file:
            cmd2.extend(["--cookies", str(cookies_file)])
        elif cookies_from_browser:
            cmd2.extend(["--cookies-from-browser", cookies_from_browser])
        cmd2.append(url)
        subprocess.run(cmd2, check=True)

    files = [p for p in dest.glob("*") if p.suffix.lower() != ".ass"]
    if not files:
        raise FileNotFoundError("No file was downloaded.")
    return max(files, key=lambda p: p.stat().st_ctime)


def download_subtitle(sub_url: str, sub_path: Path) -> bool:
    print(f"Trying subtitle: {sub_url}")
    try:
        with requests.get(sub_url, stream=True, timeout=30) as r:
            if r.status_code != 200:
                return False
            total = int(r.headers.get("content-length", 0))
            with open(sub_path, "wb") as f, tqdm(
                desc="Subtitle",
                total=total,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                leave=False,
            ) as bar:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        bar.update(len(chunk))
        return True
    except Exception:
        return False


def remux_to_mkv(video_path: Path, sub_path: Path, output_mkv: Path) -> None:
    print("Remuxing into MKV...")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(sub_path),
            "-map", "0", "-map", "1", "-c", "copy",
            "-metadata:s:s:0", "language=eng",
            str(output_mkv),
        ],
        check=True,
        capture_output=True,
    )


def process_url(
    url: str,
    dest: Path,
    series_slug: str | None = None,
    year: str = "2024",
    cookies_file: Path | None = None,
    cookies_from_browser: str | None = None,
) -> None:
    video_path = download_video(
        url, dest,
        cookies_file=cookies_file,
        cookies_from_browser=cookies_from_browser,
    )
    base_name = video_path.stem
    final_mkv = dest / f"{base_name}.mkv"

    if video_path.suffix.lower() == ".mkv":
        print(f"Already MKV: {video_path}")
        return

    ep_match = re.search(r"-(\d+)/?$", url.rstrip("/"))
    if not ep_match:
        print("Could not extract episode number – keeping original.")
        return

    ep_num = int(ep_match.group(1))
    slug_part = re.sub(r"-\d+$", "", url.rstrip("/").split("/")[-1])

    candidates = []
    if series_slug:
        candidates.append(series_slug)
    candidates += [
        slug_part.replace("-", "."),
        slug_part,
        ".".join(w.capitalize() for w in slug_part.split("-")),
    ]
    seen = set()
    candidates = [c for c in candidates if not (c in seen or seen.add(c))]

    # Try old host first, then new host
    sub_hosts = [
        "https://oppai-str.shoujo-h.org",
        "https://imoto-str.ane-h.xyz",
    ]

    sub_path = dest / f"{base_name}.ass"
    sub_ok = False
    for host in sub_hosts:
        for slug in candidates:
            sub_url = f"{host}/{year}/{slug}/E{ep_num:02d}/eng.ass"
            if download_subtitle(sub_url, sub_path):
                sub_ok = True
                break
        if sub_ok:
            break

    if sub_ok:
        remux_to_mkv(video_path, sub_path, final_mkv)
        sub_path.unlink(missing_ok=True)
        if video_path != final_mkv and video_path.exists():
            video_path.unlink()
        print(f"Finished: {final_mkv}")
    else:
        print(f"Subtitle not found on old or new host – kept original: {video_path}")
        print("Tip: pass --series-slug with the subtitle host folder name (dots)")


def parse_ts(ts: str) -> int:
    """HH:MM:SS or MM:SS or SS -> total seconds."""
    parts = [int(x) for x in ts.strip().split(":")]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]


def fmt_ts(total: int) -> str:
    h, r = divmod(max(0, total), 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def make_samples(dest: Path, start: str = "00:12:01", duration_sec: int = 60) -> None:
    """Cut timed sample clips from finished videos in dest."""
    start_sec = parse_ts(start)
    dur = int(duration_sec)
    end_sec = start_sec + dur
    start_label = fmt_ts(start_sec)
    end_label = fmt_ts(end_sec)
    mins = max(1, int(round(dur / 60)))

    videos = sorted(
        p
        for p in dest.iterdir()
        if p.suffix.lower() in {".mkv", ".mp4", ".webm", ".ts"}
        and "-sample" not in p.stem.lower()
    )
    if not videos:
        print("No videos found for samples.")
        return

    print(f"\nCreating {dur}s samples starting at {start_label} → {len(videos)} file(s)")
    for vid in videos:
        base = re.sub(r'[\\/:*?"<>|]', "", vid.stem)
        base = re.sub(r"\s+", " ", base).strip()
        out_name = f"{base}-sample [{start_label} - {end_label}] {mins} Minute{vid.suffix}"
        out_path = dest / out_name
        print(f"Sample: {vid.name} → {out_name}")
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_sec),
            "-i", str(vid),
            "-t", str(dur),
            "-c", "copy",
            str(out_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"  OK: {out_path}")
        except subprocess.CalledProcessError:
            print("  stream copy failed, re-encoding...")
            cmd2 = [
                "ffmpeg", "-y",
                "-ss", str(start_sec),
                "-i", str(vid),
                "-t", str(dur),
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k",
                str(out_path),
            ]
            try:
                subprocess.run(cmd2, check=True, capture_output=True)
                print(f"  OK (re-encode): {out_path}")
            except subprocess.CalledProcessError as e:
                print(f"  FAILED: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="HStream Extractor – bulk download & optional subtitle mux for hstream.moe",
    )
    parser.add_argument("urls", nargs="+", help="One or more hstream.moe URLs")
    parser.add_argument("-o", "--output", default=".", help="Destination folder")
    parser.add_argument("--cookies", type=Path, help="Netscape cookies.txt")
    parser.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help="chrome, firefox, edge, ...",
    )
    parser.add_argument(
        "--series-slug",
        help="Subtitle host series folder (dots), e.g. Houkago.Nureta.Seifuku",
    )
    parser.add_argument("--year", default="2024", help="Subtitle host year folder")
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Also create timed sample clips after downloads",
    )
    parser.add_argument(
        "--sample-start",
        default="00:12:01",
        help="Sample start time HH:MM:SS or MM:SS (default: 00:12:01)",
    )
    parser.add_argument(
        "--sample-duration",
        type=int,
        default=60,
        help="Sample duration in seconds (default: 60)",
    )
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency install")
    args = parser.parse_args()

    if args.cookies and args.cookies_from_browser:
        parser.error("Use either --cookies or --cookies-from-browser, not both.")

    if not args.skip_deps:
        ensure_dependencies()

    dest = Path(args.output).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    urls = [u.strip() for u in args.urls if u.strip()]
    print(f"{len(urls)} URL(s) → {dest}\n")

    if not args.cookies and not args.cookies_from_browser:
        print("No cookies provided. Some links need a logged-in session.")
        print("Use --cookies cookies.txt or --cookies-from-browser chrome\n")

    for i, url in enumerate(tqdm(urls, desc="Overall", unit="video"), start=1):
        tqdm.write(f"\n[{i}/{len(urls)}] {url}")
        try:
            process_url(
                url,
                dest,
                series_slug=args.series_slug,
                year=args.year,
                cookies_file=args.cookies,
                cookies_from_browser=args.cookies_from_browser,
            )
        except Exception as e:
            tqdm.write(f"Failed: {e}")

    if args.sample:
        make_samples(dest, start=args.sample_start, duration_sec=args.sample_duration)

    print("\nAll tasks completed!")


if __name__ == "__main__":
    main()
