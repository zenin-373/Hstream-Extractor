# HStream Extractor

A clean, standalone bulk downloader and remuxer for [hstream.moe](https://hstream.moe) (and any other site supported by [yt-dlp](https://github.com/yt-dlp/yt-dlp)).

Originally based on a Google Colab notebook. This version is a proper command-line tool with no hardcoded series names or Colab-specific markup.

## Features

- Fast downloads via **yt-dlp** + **aria2c**
- Optional external English `.ass` subtitle download + automatic remux into **MKV**
- Progress bars (overall + per-subtitle)
- Simple CLI – works on Linux, macOS, Windows (WSL / Git Bash recommended)
- No API keys or credentials required

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
# Basic – download one or more episodes
python hstream_extractor.py "https://hstream.moe/hentai/gibo-no-toiki-1" "https://hstream.moe/hentai/gibo-no-toiki-2"

# Specify output folder
python hstream_extractor.py -o ~/Videos/HStream "https://hstream.moe/hentai/..."

# Provide the correct series slug for external subtitles
# (use dots instead of spaces/hyphens, e.g. "Gibo.no.Toiki")
python hstream_extractor.py --series-slug "Gibo.no.Toiki" --year 2024 \
  "https://hstream.moe/hentai/gibo-no-toiki-1"

# Skip the automatic dependency check (if you already have everything)
python hstream_extractor.py --skip-deps ...
```

### Arguments

| Flag | Description |
|------|-------------|
| `urls` | One or more video URLs (positional) |
| `-o`, `--output` | Destination directory (default: current dir) |
| `--series-slug` | Series name used by the external subtitle host (dots instead of hyphens) |
| `--year` | Year folder on the subtitle host (default: `2024`) |
| `--skip-deps` | Skip pip / system dependency checks |

## How subtitle muxing works

1. Video is downloaded with yt-dlp + aria2c.
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
