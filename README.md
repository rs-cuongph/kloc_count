# KLOC Count Tool

A desktop application for counting **Kilo Lines of Code (KLOC)** in Git repositories, with monthly breakdown and cumulative tracking.

Built with Python + tkinter. Cross-platform: **Windows** & **macOS**.

## Features

- **Auto-detect project type** — Reads `package.json`, `pubspec.yaml`, `Gemfile`, `composer.json` to identify frameworks
- **Multi-select project types** — Flutter, NodeJs, ReactJs, NextJs, NuxtJs, VueJs, RubyOnRail, Laravel
- **Date range picker** — Calendar-based date selection with clear button
- **Commit regex filter** — Filter commits with regex (includes suggestion dropdown)
- **Monthly KLOC breakdown** — Cumulative KLOC per month
- **Real-time process log** — See git/cloc operations as they run
- **Portable build** — Build as `.exe` (Windows) or `.app` (macOS)

## Prerequisites

- **Python 3.8+**
- **git** — installed and available in PATH
- **cloc** — installed and available in PATH
  ```bash
  # Install cloc
  npm install -g cloc        # via npm
  brew install cloc           # macOS
  choco install cloc          # Windows (Chocolatey)
  sudo apt install cloc       # Ubuntu/Debian
  ```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

## Build Portable Executable

```bash
# Install build dependencies
pip install -r requirements.txt

# Build (Windows → .exe, macOS → .app)
bash build.sh
```

Output will be in the `dist/` folder:
- **Windows**: `dist/KlocCount.exe`
- **macOS**: `dist/KlocCount.app`

> **Note**: The target machine must have `git` and `cloc` installed in PATH.

## Usage

1. **Path** — Click `Browse` to select a Git repository folder
2. **Commit Regex** — (Optional) Enter a regex to filter commits. Click the field for suggestions
3. **Project Type** — Select one or more project types (auto-detected on folder selection)
4. **Date** — (Optional) Pick a date range. Leave empty to count from first to last commit
5. **Count KLOC** — Click to start counting

### Result Format

```
From: 20240101  To: 20241231
Commit Regex: (all)
Project Type: Flutter

2024-01: 5.20  (lũy kế: 5.20)
2024-02: 6.10  (lũy kế: 11.30)
2024-03: 7.50  (lũy kế: 18.80)
```

## Project Structure

```
kloc_count_tool/
├── app.py              # Main application (GUI + logic)
├── requirements.txt    # Python dependencies
├── build.sh            # Build script for portable executables
└── README.md
```
