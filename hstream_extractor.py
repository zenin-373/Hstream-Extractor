#!/usr/bin/env python3
"""HStream Extractor - yt-dlp + hanime-plugin bulk downloader / subtitle muxer."""
import argparse, re, subprocess, sys
from pathlib import Path
from urllib.parse import unquote
import requests
from tqdm import tqdm

def ensure_dependencies():
    print("Checking dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade",
                        "yt-dlp", "requests", "tqdm", "hanime-plugin"],
                       check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"pip failed: {e}"); sys.exit(1)
    for pkg in ("aria2c", "ffmpeg"):
        if subprocess.run(["which", pkg], capture_output=True).returncode != 0:
            print(f"WARNING: '{pkg}' not in PATH")
    print("OK\n")

def download_video(url, dest, cookies_file=None, cookies_from_browser=None):
    out = str(dest / "%(title)s.%(ext)s")
    formats = ["best", "bestvideo*+bestaudio/best", "best[height<=2160]",
               "best[height<=1080]", "best[height<=720]"]
    def cmd(fmt, dl):
        c = ["yt-dlp", "-f", fmt, "--downloader", dl, "--concurrent-fragments", "8",
             "-o", out, "--no-mtime", "--retries", "5", "--fragment-retries", "5"]
        if dl == "aria2c":
            c += ["--downloader-args", "aria2c:-x 16 -s 16 -k 1M"]
        if cookies_file:
            c += ["--cookies", str(cookies_file)]
        elif cookies_from_browser:
            c += ["--cookies-from-browser", cookies_from_browser]
        c.append(url)
        return c
    print(f"Downloading: {url}")
    err = None
    for fmt in formats:
        for dl in ("aria2c", "ffmpeg"):
            try:
                print(f"  try {fmt} / {dl}")
                subprocess.run(cmd(fmt, dl), check=True)
                return max([p for p in dest.glob("*") if p.suffix.lower() != ".ass"],
                           key=lambda p: p.stat().st_ctime)
            except subprocess.CalledProcessError as e:
                err = e
    raise err or RuntimeError("download failed")

def download_subtitle(sub_url, sub_path):
    print(f"Trying subtitle: {sub_url}")
    try:
        with requests.get(sub_url, stream=True, timeout=30) as r:
            if r.status_code != 200:
                return False
            total = int(r.headers.get("content-length", 0))
            with open(sub_path, "wb") as f, tqdm(
                desc="Subtitle", total=total, unit="B", unit_scale=True,
                unit_divisor=1024, leave=False) as bar:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk); bar.update(len(chunk))
        return True
    except Exception:
        return False

def _cookies_header(cookies_file):
    if not cookies_file or not Path(cookies_file).is_file():
        return None
    parts = []
    for line in Path(cookies_file).read_text(errors="ignore").splitlines():
        if not line or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) >= 7 and "hstream.moe" in cols[0]:
            parts.append(f"{cols[5]}={cols[6]}")
    return "; ".join(parts) if parts else None

def resolve_subtitle_url(page_url, cookies_file=None):
    """Permanent: HTML scrape + /player/api (CDN hosts rotate)."""
    ch = _cookies_header(cookies_file)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Referer": "https://hstream.moe/",
    }
    if ch:
        headers["Cookie"] = ch
    html = ""
    try:
        r = requests.get(page_url, headers=headers, timeout=30)
        if r.status_code == 200:
            html = r.text
            found = []
            for pat in [r'href=["\'](https?://[^"\']+?/eng\.ass)["\']',
                        r'href=["\'](https?://[^"\']+?\.ass)["\']']:
                for m in re.finditer(pat, html, re.I):
                    if m.group(1) not in found:
                        found.append(m.group(1))
            for u in found:
                if "eng.ass" in u.lower():
                    print(f"  page subtitle: {u}"); return u
            if found:
                print(f"  page subtitle: {found[0]}"); return found[0]
            print("  no .ass on page")
        else:
            print(f"  page HTTP {r.status_code}")
    except Exception as e:
        print(f"  page scrape failed: {e}")

    try:
        m = re.search(
            r'id=["\']e_id["\'][^>]*value=["\']([^"\']+)["\']'
            r'|value=["\']([^"\']+)["\'][^>]*id=["\']e_id["\']',
            html or "", re.I)
        e_id = (m.group(1) or m.group(2)) if m else None
        if not e_id:
            print("  no e_id"); return None
        api = dict(headers)
        api["Content-Type"] = "application/json"
        api["X-Requested-With"] = "XMLHttpRequest"
        if ch:
            for part in ch.split(";"):
                part = part.strip()
                if part.upper().startswith("XSRF-TOKEN="):
                    api["X-XSRF-TOKEN"] = unquote(part.split("=", 1)[1])
                    break
        resp = requests.post("https://hstream.moe/player/api", headers=api,
                             json={"episode_id": e_id}, timeout=30)
        if resp.status_code != 200:
            resp = requests.post("https://hstream.moe/player/api", headers=api,
                                 data={"episode_id": e_id}, timeout=30)
        if resp.status_code != 200:
            print(f"  player API HTTP {resp.status_code}"); return None
        data = resp.json()
        stream_url = data.get("stream_url") or data.get("streamUrl") or ""
        domains = data.get("stream_domains") or data.get("streamDomains") or []
        if isinstance(domains, str):
            domains = [domains]
        if not stream_url or not domains:
            print("  player API missing fields"); return None
        domain = domains[0]
        if not str(domain).startswith("http"):
            domain = "https://" + str(domain).lstrip("/")
        sub = f"{str(domain).rstrip('/')}/{stream_url.strip('/')}/eng.ass"
        print(f"  player API subtitle: {sub}")
        return sub
    except Exception as e:
        print(f"  player API failed: {e}")
        return None

def remux_to_mkv(video, sub, out):
    print("Remuxing MKV...")
    subprocess.run(["ffmpeg", "-y", "-i", str(video), "-i", str(sub),
                    "-map", "0", "-map", "1", "-c", "copy",
                    "-metadata:s:s:0", "language=eng", str(out)],
                   check=True, capture_output=True)

def series_folder_name(url: str) -> str:
    """e.g. .../modaete-yo-adam-kun-1 → modaete-yo-adam-kun"""
    token = url.rstrip("/").split("/")[-1]
    name = re.sub(r"-\d+$", "", token)
    name = re.sub(r'[\\/:*?"<>|]+', "", name).strip() or "unknown"
    return name

def process_url(url, dest, series_slug=None, year="2024",
                cookies_file=None, cookies_from_browser=None):
    folder = dest / series_folder_name(url)
    folder.mkdir(parents=True, exist_ok=True)
    print(f"Series folder: {folder}")

    video = download_video(url, folder, cookies_file, cookies_from_browser)
    base = video.stem
    final = folder / f"{base}.mkv"
    if video.suffix.lower() == ".mkv":
        print(f"Already MKV: {video}"); return
    m = re.search(r"-(\d+)/?$", url.rstrip("/"))
    if not m:
        print("No episode number"); return
    ep = int(m.group(1))
    slug_part = re.sub(r"-\d+$", "", url.rstrip("/").split("/")[-1])
    sub_path = folder / f"{base}.ass"
    ok = False

    print("Resolving subtitle (page + player API)...")
    live = resolve_subtitle_url(url, cookies_file=cookies_file)
    if live and download_subtitle(live, sub_path):
        ok = True

    if not ok:
        particles = {"no","wa","wo","ga","ni","de","to","na","o","yo","kun","chan","san"}
        parts = slug_part.split("-")
        cands = []
        if series_slug:
            cands.append(series_slug)
        cands.append(".".join(parts))
        cands.append(".".join(w if w in particles else w.capitalize() for w in parts))
        glued, i = [], 0
        while i < len(parts):
            w = parts[i]
            if i+1 < len(parts) and parts[i+1] in {"kun","chan","san"} and w not in particles:
                glued.append(w.capitalize() + parts[i+1]); i += 2
            else:
                glued.append(w if w in particles else w.capitalize()); i += 1
        cands.append(".".join(glued))
        cands.append(slug_part)
        cands = list(dict.fromkeys(cands))
        hosts = ["https://oppai-str.shoujo-h.org", "https://imoto-str.ane-h.xyz",
                 "https://shinobu-str.rorikon-h.xyz"]
        years = []
        for y in (year, "2026", "2025", "2024", "2023", "2022", "2021"):
            if y not in years: years.append(y)
        print("Live resolve failed – known hosts...")
        for host in hosts:
            for y in years:
                for s in cands:
                    if download_subtitle(f"{host}/{y}/{s}/E{ep:02d}/eng.ass", sub_path):
                        ok = True; break
                if ok: break
            if ok: break

    if ok:
        remux_to_mkv(video, sub_path, final)
        sub_path.unlink(missing_ok=True)
        if video != final and video.exists():
            video.unlink()
        print(f"Finished: {final}")
    else:
        print(f"No subtitle – kept: {video}")

def make_samples(dest, start="00:12:01", duration_sec=60):
    def pts(ts):
        p = [int(x) for x in ts.split(":")]
        return p[0]*3600+p[1]*60+p[2] if len(p)==3 else (p[0]*60+p[1] if len(p)==2 else p[0])
    def fts(t):
        h,r = divmod(max(0,t),3600); m,s = divmod(r,60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    st, dur = pts(start), int(duration_sec)
    sl, el, mins = fts(st), fts(st+dur), max(1, round(dur/60))
    vids = []
    for p in dest.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".mkv", ".mp4", ".webm"} and "-sample" not in p.stem.lower():
            vids.append(p)
    vids = sorted(vids)
    for v in vids:
        out = v.parent / f"{v.stem}-sample [{sl} - {el}] {mins} Minute{v.suffix}"
        print(f"Sample {v} -> {out.name}")
        try:
            subprocess.run(["ffmpeg","-y","-ss",str(st),"-i",str(v),"-t",str(dur),"-c","copy",str(out)],
                           check=True, capture_output=True)
        except subprocess.CalledProcessError:
            subprocess.run(["ffmpeg","-y","-ss",str(st),"-i",str(v),"-t",str(dur),
                            "-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac",str(out)],
                           check=False, capture_output=True)

def main():
    p = argparse.ArgumentParser(description="HStream Extractor")
    p.add_argument("urls", nargs="+")
    p.add_argument("-o", "--output", default=".")
    p.add_argument("--cookies", type=Path)
    p.add_argument("--cookies-from-browser")
    p.add_argument("--series-slug")
    p.add_argument("--year", default="2024")
    p.add_argument("--sample", action="store_true")
    p.add_argument("--sample-start", default="00:12:01")
    p.add_argument("--sample-duration", type=int, default=60)
    p.add_argument("--skip-deps", action="store_true")
    a = p.parse_args()
    if a.cookies and a.cookies_from_browser:
        p.error("Use either --cookies or --cookies-from-browser")
    if not a.skip_deps:
        ensure_dependencies()
    dest = Path(a.output).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    print(f"{len(a.urls)} URL(s) -> {dest}\n")
    for i, url in enumerate(tqdm(a.urls, desc="Overall", unit="video"), 1):
        tqdm.write(f"\n[{i}/{len(a.urls)}] {url}")
        try:
            process_url(url, dest, a.series_slug, a.year, a.cookies, a.cookies_from_browser)
        except Exception as e:
            tqdm.write(f"Failed: {e}")
    if a.sample:
        make_samples(dest, a.sample_start, a.sample_duration)
    print("\nDone")

if __name__ == "__main__":
    main()
