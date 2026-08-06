# HStream Extractor

A clean, standalone bulk downloader and remuxer for [hstream.moe](https://hstream.moe) (and any other site supported by [yt-dlp](https://github.com/yt-dlp/yt-dlp)).

Originally based on a Google Colab notebook. This version is a proper command-line tool with **no hardcoded credentials or session cookies**.

## Features

- Fast downloads via **yt-dlp** + **aria2c**
- **Cookie support** for age-restricted / logged-in-only content
- Optional external English `.ass` subtitle download + automatic remux into **MKV**
- Progress bars (overall + per-subtitle)
- Simple CLI – works on Linux, macOS, Windows (WSL / Git Bash recommended)
- No API keys or hardcoded credentials

## Important: Cookies for blocked links

Many titles on hstream.moe are **blocked for anonymous visitors**. You need a valid logged-in session.

### Recommended methods (safe)

#### 1. Export cookies to a file (best for automation)

1. Log in to [hstream.moe](https://hstream.moe) in your normal browser.
2. Use a browser extension such as:
   - [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Chrome/Edge)
   - [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox)
3. Export cookies for `hstream.moe` in **Netscape** format → save as `cookies.txt`.
4. Run the tool with:

```bash
python hstream_extractor.py --cookies cookies.txt "https://hstream.moe/hentai/..."
```

#### 2. Let yt-dlp read cookies directly from your browser

```bash
python hstream_extractor.py --cookies-from-browser chrome "https://hstream.moe/hentai/..."
# or
python hstream_extractor.py --cookies-from-browser firefox "https://hstream.moe/hentai/..."
```

Supported browsers: `chrome`, `firefox`, `edge`, `brave`, `opera`, `chromium`, `safari` (macOS), etc.

> **Security note**  
> Never commit real cookies to a public repository. Cookies expire and give access to your account.  
> Keep `cookies.txt` in `.gitignore` (already configured).

## Requirements

- Python 3.9+
- `yt-dlp`, `requests`, `tqdm` (installed automatically on first run)
- System tools: `aria2c` and `ffmpeg` (recommended)

### Install system tools

**Debian / Ubuntu / WSL**
```bash
sudo apt update
sudo apt install -y aria2 ffmpeg
```

**macOS (Homebrew)**
```bash
brew install aria2 ffmpeg
```

**Windows**  
Install via [Scoop](https://scoop.sh/) or [Chocolatey](https://chocolatey.org/), or place the binaries in your PATH.

## Installation

```bash
git clone https://github.com/zenin-373/Hstream-Extractor.git
cd Hstream-Extractor
python -m pip install -r requirements.txt   # optional – the script can also install them
```

Or just download `hstream_extractor.py` and run it.

## Usage

```bash
# Basic (works only for public links)
python hstream_extractor.py "https://hstream.moe/hentai/..."

# With cookies file (recommended for most titles)
python hstream_extractor.py --cookies cookies.txt \\
  "https://hstream.moe/hentai/sweet-home-h-na-oneesan-wa-suki-desu-ka-1" \\
  "https://hstream.moe/hentai/sweet-home-h-na-oneesan-wa-suki-desu-ka-2"

# Pull cookies live from browser
python hstream_extractor.py --cookies-from-browser chrome \\
  "https://hstream.moe/hentai/..."

# Specify output folder + series slug for external subtitles
python hstream_extractor.py -o ~/Videos \\
  --series-slug "Sweet.Home.H.na.Oneesan.wa.Suki.desu.ka" \\
  --year 2024 \\
  --cookies cookies.txt \\
  "https://hstream.moe/hentai/sweet-home-h-na-oneesan-wa-suki-desu-ka-1"
```

### Arguments

| Flag | Description |
|------|-------------|
| `urls` | One or more video URLs (positional) |
| `-o`, `--output` | Destination directory (default: current dir) |
| `--cookies` | Path to Netscape-format `cookies.txt` |
| `--cookies-from-browser` | Browser name to load cookies from (`chrome`, `firefox`, …) |
| `--series-slug` | Series name used by the external subtitle host (dots instead of hyphens) |
| `--year` | Year folder on the subtitle host (default: `2024`) |
| `--skip-deps` | Skip pip / system dependency checks |

## How subtitle muxing works

1. Video is downloaded with yt-dlp + aria2c (using cookies if provided).
2. Episode number is extracted from the URL (last numeric segment).
3. An external `.ass` subtitle is attempted from:
   ```
   https://oppai-str.shoujo-h.org/{year}/{Series.Slug}/E{ep:02}/eng.ass
   ```
4. If the subtitle is found, video + sub are remuxed into a single `.mkv` (stream copy, no re-encode).
5. Temporary files are cleaned up.

If the subtitle is missing or the slug is wrong, the original video file is kept.

> **Note:** The external subtitle host and path format are community-sourced and may change. Always supply the correct `--series-slug` for best results.

## License

MIT – do whatever you want, just don’t blame the author.

## Disclaimer

This tool is for personal, educational, and archival use only.  
Respect the terms of service of the sites you download from and the copyright of the content creators.
