#!/usr/bin/env python3
"""
HStream Extractor
Bulk downloader + optional subtitle muxer for hstream.moe (and similar yt-dlp supported sites).

Features:
- Downloads videos with yt-dlp + aria2c
- Cookie support for age-restricted / logged-in-only content
- Optional external .ass subtitle download + remux into MKV
- Progress bars via tqdm
- Clean CLI interface (no Colab markup, no hardcoded credentials)
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

import requests
from tqdm import tqdm


def ensure_dependencies():
    """Install/upgrade required packages and system tools if missing."""
    print("📦 Checking / installing dependencies...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp", "requests", "tqdm"],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"⚠️  pip install failed: {e}")
        sys.exit(1)

    for pkg in ("aria2c", "ffmpeg"):
        if subprocess.run(["which", pkg], capture_output=True).returncode != 0:
            print(f"⚠️  '{pkg}' not found in PATH. Install it manually for best results.")
    print("✅ Dependency check done.\n")


def download_video(
    url: str,
    dest: Path,
    cookies_file: Path | None = None,
    cookies_from_browser: str | None = None,
) -> Path:
    """Download a single video using yt-dlp + aria2c. Returns path to downloaded file."""
    output_template = str(dest / "%(title)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "--downloader", "aria2c",
        "--downloader-args", "aria2c:-x 16 -s 16 -k 1M",
        "--concurrent-fragments", "8",
        "-o", output_template,
        "--no-mtime",
    ]

    # Cookie handling (required for many hstream.moe links)
    if cookies_file:
        cmd.extend(["--cookies", str(cookies_file)])
    elif cookies_from_browser:
        cmd.extend(["--cookies-from-browser", cookies_from_browser])

    cmd.append(url)

    print(f"⬇️  Downloading video: {url}")
    subprocess.run(cmd, check=True)

    files = list(dest.glob("*"))
    if not files:
        raise FileNotFoundError("No file was downloaded.")
    latest = max(files, key=lambda p: p.stat().st_ctime)
    return latest


def download_subtitle(sub_url: str, sub_path: Path) -> bool:
    """Download a subtitle file with a progress bar. Returns True on success."""
    print(f"⬇️  Downloading subtitle: {sub_url}")
    try:
        with requests.get(sub_url, stream=True, timeout=30) as r:
            if r.status_code != 200:
                print(f"⚠️  Subtitle not found (HTTP {r.status_code})")
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
    except Exception as e:
        print(f"⚠️  Subtitle download failed: {e}")
        return False


def remux_to_mkv(video_path: Path, sub_path: Path, output_mkv: Path) -> None:
    """Mux video + ASS subtitle into an MKV container (stream copy)."""
    print("🔗 Remuxing into MKV...")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(sub_path),
        "-map", "0",
        "-map", "1",
        "-c", "copy",
        "-metadata:s:s:0", "language=eng",
        str(output_mkv),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def process_url(
    url: str,
    dest: Path,
    series_slug: str | None = None,
    year: str = "2024",
    cookies_file: Path | None = None,
    cookies_from_browser: str | None = None,
) -> None:
    """Full pipeline for one URL."""
    video_path = download_video(
        url, dest,
        cookies_file=cookies_file,
        cookies_from_browser=cookies_from_browser,
    )
    base_name = video_path.stem
    final_mkv = dest / f"{base_name}.mkv"

    # Skip if already an mkv from a previous run
    if video_path.suffix.lower() == ".mkv" and video_path == final_mkv:
        print(f"✅ Already exists as MKV: {video_path}")
        return

    # Attempt to derive episode number from URL (last segment after last '-')
    ep_match = re.search(r"-(\d+)/?$", url.rstrip("/"))
    if not ep_match:
        print("⚠️  Could not extract episode number from URL – skipping subtitle.")
        print(f"✅ Kept original: {video_path}")
        return

    ep_num = int(ep_match.group(1))

    if not series_slug:
        # Fallback guess: /hentai/gibo-no-toiki-1 → gibo-no-toiki
        slug_part = url.rstrip("/").split("/")[-1]
        series_slug = re.sub(r"-\d+$", "", slug_part)

    # External subtitle host format (community-sourced, may change)
    # https://oppai-str.shoujo-h.org/{year}/{Series.Name}/E{ep:02}/eng.ass
    sub_url = f"https://oppai-str.shoujo-h.org/{year}/{series_slug}/E{ep_num:02d}/eng.ass"
    sub_path = dest / f"{base_name}.ass"

    if download_subtitle(sub_url, sub_path):
        remux_to_mkv(video_path, sub_path, final_mkv)
        sub_path.unlink(missing_ok=True)
        if video_path != final_mkv and video_path.exists():
            video_path.unlink()
        print(f"✅ Finished: {final_mkv}")
    else:
        print(f"⚠️  Subtitle unavailable – keeping original video: {video_path}")


def main():
    parser = argparse.ArgumentParser(
        description="HStream Extractor – bulk download & optional subtitle mux for hstream.moe",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic download
  python hstream_extractor.py "https://hstream.moe/hentai/..."

  # With cookies from a Netscape cookies.txt file (recommended)
  python hstream_extractor.py --cookies cookies.txt "https://hstream.moe/hentai/..."

  # Automatically pull cookies from your browser
  python hstream_extractor.py --cookies-from-browser chrome "https://hstream.moe/hentai/..."
  python hstream_extractor.py --cookies-from-browser firefox "https://hstream.moe/hentai/..."

  # Full example with series slug for subtitles
  python hstream_extractor.py -o ~/Videos --series-slug "Sweet.Home.H.na.Oneesan.wa.Suki.desu.ka" \\
      --cookies cookies.txt "https://hstream.moe/hentai/sweet-home-h-na-oneesan-wa-suki-desu-ka-1"
""",
    )
    parser.add_argument(
        "urls",
        nargs="+",
        help="One or more hstream.moe (or yt-dlp supported) URLs",
    )
    parser.add_argument(
        "-o", "--output",
        default=".",
        help="Destination folder (default: current directory)",
    )
    parser.add_argument(
        "--cookies",
        type=Path,
        help="Path to a Netscape-format cookies.txt file (for blocked / age-gated content)",
    )
    parser.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help="Load cookies directly from a browser (chrome, firefox, edge, brave, opera, ...)",
    )
    parser.add_argument(
        "--series-slug",
        help="Series slug for external subtitles, e.g. 'Gibo.no.Toiki' "
             "(use dots instead of spaces/hyphens). If omitted, a simple guess is made.",
    )
    parser.add_argument(
        "--year",
        default="2024",
        help="Year folder used by the external subtitle host (default: 2024)",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip dependency installation check",
    )
    args = parser.parse_args()

    if args.cookies and args.cookies_from_browser:
        parser.error("Use either --cookies or --cookies-from-browser, not both.")

    if not args.skip_deps:
        ensure_dependencies()

    dest = Path(args.output).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    urls = [u.strip() for u in args.urls if u.strip()]
    print(f"📋 {len(urls)} URL(s) to process → {dest}\n")

    if not args.cookies and not args.cookies_from_browser:
        print("ℹ️  No cookies provided. Some hstream.moe links are blocked without a logged-in session.")
        print("   Use --cookies cookies.txt  or  --cookies-from-browser chrome\n")

    for i, url in enumerate(tqdm(urls, desc="Overall", unit="video"), start=1):
        tqdm.write(f"\n🔄 [{i}/{len(urls)}] {url}")
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
            tqdm.write(f"❌ Failed: {e}")

    print("\n🎉 All tasks completed!")


if __name__ == "__main__":
    main()
