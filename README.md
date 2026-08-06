# HStream Extractor

Bulk downloader + subtitle remuxer for [hstream.moe](https://hstream.moe).

Uses **yt-dlp** + **[hanime-plugin](https://github.com/cynthia2006/hanime-plugin)** (required for hstream.moe) + optional external `.ass` mux into MKV.

**No hardcoded credentials.**

## Limitations

- **Single episode / single file links only.**  
  Pass one or more **individual episode URLs** (e.g. `.../hentai/title-1`).  
  **Playlists / series pages are not supported** — they will not expand or download as a batch from one series URL.
- Subtitle host paths and domains can change; set `--series-slug` / `SERIES_SLUG` if auto-detect fails.

## Features

- yt-dlp + aria2c (ffmpeg fallback)
- **hanime-plugin** extractor for hstream.moe
- Cookie support (file, browser, or Colab form tokens)
- Optional English `.ass` download + MKV remux (old + new subtitle hosts)
- Optional timed sample clips (`--sample`)
- Progress bars
- CLI + Google Colab notebook

## Credits

hstream.moe extraction is provided by **[hanime-plugin](https://github.com/cynthia2006/hanime-plugin)** by [cynthia2006](https://github.com/cynthia2006).

- GitHub: https://github.com/cynthia2006/hanime-plugin  
- PyPI: https://pypi.org/project/hanime-plugin/

This project is a thin bulk-download / remux / sample wrapper around yt-dlp + that plugin. All credit for site support goes to the plugin author.

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
   - `URL_LIST` — **space-separated single episode URLs** (not playlist/series pages)
   - `DESTINATION_FOLDER`
   - `XSRF_TOKEN` / `HSTREAM_SESSION`
   - `SERIES_SLUG` — optional, if auto subtitle path fails (use dots)
   - Sample options if you want a 1-minute clip
4. Run the extractor cell, then sample cell if needed.
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
# Single episode URLs only (list multiple episodes explicitly)
python hstream_extractor.py --cookies cookies.txt \
  "https://hstream.moe/hentai/houkago-nureta-seifuku-1" \
  "https://hstream.moe/hentai/houkago-nureta-seifuku-2"

python hstream_extractor.py -o ~/Videos \
  --series-slug "Houkago.Nureta.Seifuku" \
  --cookies cookies.txt \
  --sample --sample-start 00:12:01 --sample-duration 60 \
  "https://hstream.moe/hentai/houkago-nureta-seifuku-2"
```

| Flag | Description |
|------|-------------|
| `urls` | **Single episode** video URLs (not playlists) |
| `-o`, `--output` | Output directory |
| `--cookies` | Netscape `cookies.txt` |
| `--cookies-from-browser` | e.g. `chrome`, `firefox` |
| `--series-slug` | Subtitle host folder (dots) |
| `--year` | Subtitle year folder (default `2024`) |
| `--sample` | Create timed sample clips after download |
| `--sample-start` | Sample start (`HH:MM:SS`, default `00:12:01`) |
| `--sample-duration` | Sample length in seconds (default `60`) |
| `--skip-deps` | Skip dependency install |

## Subtitles

After download, the tool tries **old host first**, then **new host**:

```text
https://oppai-str.shoujo-h.org/2024/{Series.Slug}/E{ep:02}/eng.ass
https://imoto-str.ane-h.xyz/2024/{Series.Slug}/E{ep:02}/eng.ass
```

If found → remux to `.mkv` with ffmpeg (`-c copy`).  
If not → keeps the original video. Set `--series-slug` / `SERIES_SLUG` when auto-guess fails.

## License

MIT

## Disclaimer

Personal / educational / archival use only. Respect site ToS and copyright.
