# HStream Extractor

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/zenin-373/Hstream-Extractor/blob/main/HStream_Extractor_Colab.ipynb)

Bulk downloader + subtitle remuxer for [hstream.moe](https://hstream.moe).

Uses **yt-dlp** + **[hanime-plugin](https://pypi.org/project/hanime-plugin/)** (required for hstream.moe) + optional external `.ass` mux into MKV.

**No hardcoded credentials.**

## Features

- yt-dlp + aria2c (ffmpeg fallback)
- **hanime-plugin** extractor for hstream.moe
- Cookie support (file, browser, or Colab form tokens)
- Optional English `.ass` download + MKV remux
- Progress bars
- CLI + Google Colab notebook

## Important: hstream.moe needs hanime-plugin

Stock yt-dlp does **not** support hstream.moe. Install:

```bash
pip install -U yt-dlp hanime-plugin
```

Some plugin features also need [Deno](https://deno.land).

## Cookies (blocked / login-only titles)

### Local CLI

```bash
# Netscape cookies.txt
python hstream_extractor.py --cookies cookies.txt "https://hstream.moe/hentai/..."

# Or from browser
python hstream_extractor.py --cookies-from-browser chrome "https://hstream.moe/hentai/..."
```

### Google Colab

In the Settings form, paste:

- `XSRF_TOKEN` — cookie value from DevTools
- `HSTREAM_SESSION` — cookie value from DevTools

How to copy: log in → DevTools → Application → Cookies → `hstream.moe` → copy values only (not the names).

> Never commit real cookies. They expire and grant account access.

---

## Run on Google Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/zenin-373/Hstream-Extractor/blob/main/HStream_Extractor_Colab.ipynb)

1. Open the notebook (badge above).
2. Run **Install dependencies** (installs yt-dlp, hanime-plugin, aria2, ffmpeg, deno).
3. Fill **Settings**:
   - `URL_LIST` — space-separated URLs
   - `DESTINATION_FOLDER`
   - `XSRF_TOKEN` / `HSTREAM_SESSION`
   - `SERIES_SLUG` — optional, if auto subtitle path fails (use dots)
4. Run the extractor cell.
5. Zip/download from the Files sidebar.

---

## Local CLI

### Requirements

- Python 3.9+
- `aria2c`, `ffmpeg` recommended
- Deno recommended (for hanime-plugin)

```bash
# Debian/Ubuntu/WSL
sudo apt update && sudo apt install -y aria2 ffmpeg

# macOS
brew install aria2 ffmpeg
```

### Install

```bash
git clone https://github.com/zenin-373/Hstream-Extractor.git
cd Hstream-Extractor
pip install -r requirements.txt
```

### Usage

```bash
python hstream_extractor.py --cookies cookies.txt \
  "https://hstream.moe/hentai/sweet-home-h-na-oneesan-wa-suki-desu-ka-1"

python hstream_extractor.py -o ~/Videos \
  --series-slug "Sweet.Home.H.na.Oneesan.wa.Suki.desu.ka" \
  --cookies cookies.txt \
  "https://hstream.moe/hentai/sweet-home-h-na-oneesan-wa-suki-desu-ka-1"
```

| Flag | Description |
|------|-------------|
| `urls` | Video URLs |
| `-o`, `--output` | Output directory |
| `--cookies` | Netscape `cookies.txt` |
| `--cookies-from-browser` | e.g. `chrome`, `firefox` |
| `--series-slug` | Subtitle host folder (dots) |
| `--year` | Subtitle year folder (default `2024`) |
| `--skip-deps` | Skip dependency install |

## Subtitles

After download, the tool tries:

```text
https://oppai-str.shoujo-h.org/2024/{Series.Slug}/E{ep:02}/eng.ass
```

If found → remux to `.mkv` with ffmpeg (`-c copy`).  
If not → keeps the original video. Set `--series-slug` / `SERIES_SLUG` when auto-guess fails.

## License

MIT

## Disclaimer

Personal / educational / archival use only. Respect site ToS and copyright.
