#!/usr/bin/env python3
"""
KLOC Count Tool — Desktop GUI (tkinter)
Cross-platform: macOS / Windows
Requires: git, cloc installed and available in PATH
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
import threading
from datetime import datetime, date as date_type
from calendar import monthrange
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
import webbrowser

# ─────────────────────────────────────────────
# Exclude rules per project type
# ─────────────────────────────────────────────
EXCLUDE_RULES = {
    "Flutter": {
        "dirs": ".dart_tool,.idea,build,.flutter-plugins,.flutter-plugins-dependencies,Pods,.gradle,.git,windows,linux,macos,web",
        "exts": "lock,svg,png,jpg,jpeg,gif,ico",
        "match": r"(\.g\.dart|\.freezed\.dart)$",
    },
    "NodeJs": {
        "dirs": "node_modules,dist,build,coverage,.cache,.git",
        "exts": "log,lock,min.js,min.css,svg,png,jpg,jpeg,gif,ico",
        "match": "",
    },
    "ReactJs": {
        "dirs": "node_modules,dist,build,coverage,.next,.turbo,.cache,.git",
        "exts": "log,lock,min.js,min.css,svg,png,jpg,jpeg,gif,ico",
        "match": "",
    },
    "NextJs": {
        "dirs": "node_modules,dist,build,coverage,.next,.turbo,.cache,.git",
        "exts": "log,lock,min.js,min.css,svg,png,jpg,jpeg,gif,ico",
        "match": "",
    },
    "NuxtJs": {
        "dirs": "node_modules,dist,build,coverage,.nuxt,.turbo,.cache,.git",
        "exts": "log,lock,min.js,min.css,svg,png,jpg,jpeg,gif,ico",
        "match": "",
    },
    "VueJs": {
        "dirs": "node_modules,dist,build,coverage,.nuxt,.turbo,.cache,.git",
        "exts": "log,lock,min.js,min.css,svg,png,jpg,jpeg,gif,ico",
        "match": "",
    },
    "RubyOnRail": {
        "dirs": "node_modules,log,tmp,vendor,storage,coverage,public,packs,.git",
        "exts": "log,sqlite3,db,lock,min.js,min.css",
        "match": "",
    },
    "Laravel": {
        "dirs": "node_modules,vendor,storage,bootstrap/cache,.git",
        "exts": "log,lock,min.js,min.css,svg,png,jpg,jpeg,gif,ico",
        "match": "",
    },
    "Python": {
        "dirs": "__pycache__,.venv,venv,.env,env,node_modules,.pytest_cache,.mypy_cache,.tox,dist,build,*.egg-info,.git,.ruff_cache",
        "exts": "pyc,pyo,log,lock,min.js,min.css,svg,png,jpg,jpeg,gif,ico",
        "match": "",
    },
}

PROJECT_TYPES = list(EXCLUDE_RULES.keys())


# ─────────────────────────────────────────────
# Auto-detect project type from folder
# ─────────────────────────────────────────────
def detect_project_types(path):
    """Detect project type(s) from a given folder. Returns a set of matched types."""
    detected = set()
    if not os.path.isdir(path):
        return detected

    files = set()
    try:
        for item in os.listdir(path):
            files.add(item.lower())
    except OSError:
        return detected

    # Flutter
    if "pubspec.yaml" in files or "pubspec.yml" in files:
        detected.add("Flutter")

    # Ruby on Rails
    gemfile_path = os.path.join(path, "Gemfile")
    if os.path.isfile(gemfile_path):
        try:
            with open(gemfile_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if "rails" in content.lower():
                    detected.add("RubyOnRail")
        except OSError:
            pass

    # Laravel (PHP)
    composer_path = os.path.join(path, "composer.json")
    if os.path.isfile(composer_path):
        try:
            with open(composer_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.loads(f.read())
                all_deps = {}
                all_deps.update(data.get("require", {}))
                all_deps.update(data.get("require-dev", {}))
                if any("laravel" in k.lower() for k in all_deps):
                    detected.add("Laravel")
        except (OSError, json.JSONDecodeError):
            pass

    # Node-based projects (package.json)
    pkg_path = os.path.join(path, "package.json")
    if os.path.isfile(pkg_path):
        try:
            with open(pkg_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.loads(f.read())
                all_deps = {}
                all_deps.update(data.get("dependencies", {}))
                all_deps.update(data.get("devDependencies", {}))
                dep_keys = {k.lower() for k in all_deps}

                if "next" in dep_keys:
                    detected.add("NextJs")
                if "nuxt" in dep_keys or "nuxt3" in dep_keys:
                    detected.add("NuxtJs")
                if "react" in dep_keys:
                    detected.add("ReactJs")
                if "vue" in dep_keys:
                    detected.add("VueJs")

                # Generic NodeJs if none of the specific frameworks detected
                if not detected.intersection({"NextJs", "NuxtJs", "ReactJs", "VueJs"}):
                    detected.add("NodeJs")

        except (OSError, json.JSONDecodeError):
            detected.add("NodeJs")

    # Python
    python_markers = {"requirements.txt", "setup.py", "pyproject.toml", "pipfile", "manage.py", "setup.cfg"}
    if python_markers.intersection(files):
        detected.add("Python")

    return detected


# ─────────────────────────────────────────────
# Core KLOC counter logic
# ─────────────────────────────────────────────
class KlocCounter:
    """Handles git + cloc operations."""

    def __init__(self, repo_path, project_types, branch="", commit_regex="", log_callback=None):
        self.repo_path = repo_path
        self.project_types = project_types  # list of selected types
        self.branch = branch.strip() if branch else ""
        self.commit_regex = commit_regex.strip() if commit_regex else ""
        self.log = log_callback or (lambda msg: None)

    def _merged_rules(self):
        """Merge exclude rules from all selected project types."""
        all_dirs = set()
        all_exts = set()
        all_match = []
        for pt in self.project_types:
            rules = EXCLUDE_RULES[pt]
            all_dirs.update(d.strip() for d in rules["dirs"].split(",") if d.strip())
            all_exts.update(e.strip() for e in rules["exts"].split(",") if e.strip())
            if rules["match"]:
                all_match.append(rules["match"])
        return {
            "dirs": ",".join(sorted(all_dirs)),
            "exts": ",".join(sorted(all_exts)),
            "match": "|".join(all_match) if all_match else "",
        }

    def _run(self, cmd, cwd=None):
        self.log(f"> {' '.join(cmd)}")

        # Resolve executable full path (handles .cmd/.bat on Windows)
        resolved = shutil.which(cmd[0])
        if resolved:
            cmd = [resolved] + cmd[1:]

        # On Windows, .cmd/.bat files always run through cmd.exe internally,
        # even without shell=True. Special chars like ( ) | in arguments
        # (e.g. --not-match-f regex) get interpreted by cmd.exe.
        # Fix: double-quote args with special chars and use shell=True.
        _cmd_special = set('()|&<>^')
        if (sys.platform == "win32" and resolved
                and resolved.lower().endswith(('.cmd', '.bat'))):
            quoted = []
            for arg in cmd:
                if any(c in arg for c in _cmd_special):
                    quoted.append(f'"{arg}"')
                else:
                    quoted.append(arg)
            result = subprocess.run(
                ' '.join(quoted), capture_output=True, text=True,
                cwd=cwd or self.repo_path, shell=True,
            )
        else:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                cwd=cwd or self.repo_path,
            )

        if result.returncode != 0 and result.stderr:
            self.log(f"  stderr: {result.stderr.strip()}")
        return result.stdout.strip()

    def _git_log_latest(self, after=None, before=None):
        cmd = ["git", "log"]
        if self.branch:
            cmd.append(self.branch)
        else:
            cmd.append("--all")
        if self.commit_regex and self.commit_regex != ".":
            cmd += [f"--grep={self.commit_regex}", "--regexp-ignore-case"]
        if after:
            cmd += [f"--after={after} 00:00:00"]
        if before:
            cmd += [f"--before={before} 23:59:59"]
        cmd += ["-n", "1", "--format=%H"]
        return self._run(cmd)

    def _cloc_at_commit(self, commit_hash):
        import zipfile as _zipfile

        rules = self._merged_rules()
        tmpdir = tempfile.mkdtemp(prefix="kloc_")
        zip_path = os.path.join(tmpdir, "archive.zip")
        extract_dir = os.path.join(tmpdir, "src")
        os.makedirs(extract_dir, exist_ok=True)

        try:
            self.log(f"  Archiving {commit_hash[:10]}...")

            # Use git archive --format=zip → write to file → extract with Python
            archive_cmd = [
                "git", "archive", "--format=zip",
                "--output", zip_path, commit_hash,
            ]
            git_path = shutil.which("git")
            if git_path:
                archive_cmd[0] = git_path
            result = subprocess.run(
                archive_cmd, capture_output=True, text=True,
                cwd=self.repo_path,
            )
            if result.returncode != 0:
                self.log(f"  git archive failed: {result.stderr.strip()}")
                return 0

            # Extract zip with Python (cross-platform)
            if not os.path.isfile(zip_path) or os.path.getsize(zip_path) == 0:
                self.log("  Warning: git archive produced empty zip")
                return 0

            with _zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)

            file_count = sum(1 for _ in _walk_files(extract_dir))
            if file_count == 0:
                self.log("  Warning: archive produced 0 files")
                return 0

            self.log(f"  Extracted {file_count} files. Running cloc...")
            cloc_cmd = [
                "cloc", extract_dir,
                f"--exclude-dir={rules['dirs']}",
                f"--exclude-ext={rules['exts']}",
                "--json",
            ]
            if rules["match"]:
                cloc_cmd.append(f"--not-match-f={rules['match']}")

            cloc_out = self._run(cloc_cmd, cwd=extract_dir)
            if not cloc_out:
                self.log("  Warning: cloc returned empty output")
                return 0

            data = json.loads(cloc_out)
            loc = data.get("SUM", {}).get("code", 0)
            self.log(f"  LOC = {loc}")
            return loc
        except Exception as e:
            self.log(f"  Error: {e}")
            return 0
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def get_date_range(self):
        """Get the first and last commit dates from git history."""
        branch_arg = self.branch if self.branch else "--all"

        # First commit date
        first_cmd = ["git", "log", branch_arg, "--reverse", "--format=%ai", "-n", "1"]
        first_out = self._run(first_cmd)
        if not first_out:
            return None, None
        first_date = first_out.split()[0]  # "2024-01-15 10:30:00 +0700" → "2024-01-15"

        # Last commit date
        last_cmd = ["git", "log", branch_arg, "--format=%ai", "-n", "1"]
        last_out = self._run(last_cmd)
        if not last_out:
            return None, None
        last_date = last_out.split()[0]

        # Convert to yyyyMMdd format
        first_yyyymmdd = first_date.replace("-", "")
        last_yyyymmdd = last_date.replace("-", "")

        self.log(f"  First commit: {first_date}")
        self.log(f"  Last commit:  {last_date}")
        return first_yyyymmdd, last_yyyymmdd

    def count_monthly(self, date_from, date_to):
        self.log(f"── Mode: Monthly ({date_from} → {date_to}) ──")
        results = []
        cumulative = 0.0

        current = datetime.strptime(date_from, "%Y%m%d").replace(day=1)
        end_dt = datetime.strptime(date_to, "%Y%m%d")

        while current <= end_dt:
            year, month = current.year, current.month
            _, last_day = monthrange(year, month)
            month_start = current.strftime("%Y-%m-%d")
            month_end = f"{year}-{month:02d}-{last_day:02d}"
            month_label = current.strftime("%Y-%m")

            self.log(f"\n Processing {month_label}...")
            commit = self._git_log_latest(after=month_start, before=month_end)

            if not commit:
                self.log(f"  No commit in {month_label}, skipping.")
                if month == 12:
                    current = current.replace(year=year + 1, month=1, day=1)
                else:
                    current = current.replace(month=month + 1, day=1)
                continue

            loc = self._cloc_at_commit(commit)
            kloc = loc / 1000
            cumulative += kloc
            results.append({
                "month": month_label,
                "kloc": round(kloc, 2),
                "cumulative": round(cumulative, 2),
            })
            self.log(f"  {month_label}: {kloc:.2f} KLOC (cumulative: {cumulative:.2f})")

            if month == 12:
                current = current.replace(year=year + 1, month=1, day=1)
            else:
                current = current.replace(month=month + 1, day=1)

        return results


def _walk_files(directory):
    for root, _dirs, files in os.walk(directory):
        for f in files:
            yield os.path.join(root, f)


# ─────────────────────────────────────────────
# GUI Application
# ─────────────────────────────────────────────
class KlocApp(tk.Tk):

    # ── Colour palette ───────────────────────
    BG = "#1a1a2e"
    BG_CARD = "#16213e"
    BG_INPUT = "#0f3460"
    FG = "#e0e0e0"
    FG_DIM = "#8899aa"
    ACCENT = "#e94560"
    ACCENT_HOVER = "#ff6b81"
    BTN_BG = "#233554"
    BTN_ACTIVE = "#e94560"
    BTN_FG = "#8899aa"
    BTN_FG_ACTIVE = "#ffffff"
    SUCCESS = "#00d2d3"
    BORDER = "#233554"
    BADGE_DETECTED = "#1dd1a1"  # green tint for auto-detected

    FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "SF Pro Display"

    def __init__(self):
        super().__init__()

        # Fonts
        self.FONT = (self.FONT_FAMILY, 11)
        self.FONT_BOLD = (self.FONT_FAMILY, 11, "bold")
        self.FONT_SMALL = (self.FONT_FAMILY, 9)
        self.FONT_SMALL_BOLD = (self.FONT_FAMILY, 9, "bold")
        self.FONT_MONO = ("Consolas" if sys.platform == "win32" else "Menlo", 10)
        self.FONT_TITLE = (self.FONT_FAMILY, 20, "bold")

        self.title("KLOC COUNT")
        self.configure(bg=self.BG)
        self.geometry("1000x720")
        self.minsize(900, 620)

        # State: multi-select project types
        self._selected_projects = set()
        self._project_buttons = {}
        self._is_running = False

        self._build_ui()

    # ── Constants ─────────────────────────────
    FEEDBACK_URL = "https://github.com/rs-cuongph/kloc_count/issues"

    # ── Build UI ─────────────────────────────
    def _build_ui(self):
        # Title bar
        title_frame = tk.Frame(self, bg=self.BG)
        title_frame.pack(fill="x", pady=(20, 10))

        # Feedback button — top right
        btn_feedback = tk.Button(
            title_frame, text="💬 Feedback", font=self.FONT_SMALL,
            bg=self.BTN_BG, fg=self.FG_DIM, relief="flat",
            activebackground=self.ACCENT, activeforeground="#fff",
            cursor="hand2", padx=10, pady=2,
            command=lambda: webbrowser.open(self.FEEDBACK_URL),
        )
        btn_feedback.place(relx=1.0, x=-16, y=8, anchor="ne")

        tk.Label(
            title_frame, text="KLOC COUNT", font=self.FONT_TITLE,
            fg=self.ACCENT, bg=self.BG,
        ).pack()
        tk.Label(
            title_frame, text="Kilo Lines of Code Counter",
            font=self.FONT_SMALL, fg=self.FG_DIM, bg=self.BG,
        ).pack()

        # Body: left form + right log
        body = tk.Frame(self, bg=self.BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        body.columnconfigure(0, weight=3, uniform="col")
        body.columnconfigure(1, weight=2, uniform="col")
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=self.BG_CARD, bd=0,
                        highlightthickness=1, highlightbackground=self.BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        right = tk.Frame(body, bg=self.BG_CARD, bd=0,
                         highlightthickness=1, highlightbackground=self.BORDER)
        right.grid(row=0, column=1, sticky="nsew")

        self._build_form(left)
        self._build_log_panel(right)

    def _make_label(self, parent, text, **kw):
        return tk.Label(
            parent, text=text, font=self.FONT_BOLD,
            fg=self.FG_DIM, bg=self.BG_CARD, anchor="w", **kw,
        )

    def _make_entry(self, parent, placeholder="", width=None, **kw):
        opts = {}
        if width:
            opts["width"] = width
        entry = tk.Entry(
            parent, font=self.FONT, bg=self.BG_INPUT, fg=self.FG,
            insertbackground=self.FG, relief="flat", bd=0,
            highlightthickness=1, highlightbackground=self.BORDER,
            highlightcolor=self.ACCENT, **opts, **kw,
        )
        if placeholder:
            entry.insert(0, placeholder)
            entry.config(fg=self.FG_DIM)
            entry.bind("<FocusIn>", lambda e, ent=entry, ph=placeholder: self._clear_ph(ent, ph))
            entry.bind("<FocusOut>", lambda e, ent=entry, ph=placeholder: self._restore_ph(ent, ph))
        return entry

    def _clear_ph(self, entry, ph):
        if entry.get() == ph:
            entry.delete(0, "end")
            entry.config(fg=self.FG)

    def _restore_ph(self, entry, ph):
        if not entry.get():
            entry.insert(0, ph)
            entry.config(fg=self.FG_DIM)

    def _build_form(self, parent):
        inner = tk.Frame(parent, bg=self.BG_CARD)
        inner.pack(fill="both", expand=True, padx=20, pady=16)

        # ── Row: Path ──
        row = tk.Frame(inner, bg=self.BG_CARD)
        row.pack(fill="x", pady=(0, 12))
        self._make_label(row, "Path", width=10).pack(side="left")
        self.entry_path = self._make_entry(row)
        self.entry_path.pack(side="left", fill="x", expand=True, ipady=7, padx=(4, 10))
        btn_browse = tk.Button(
            row, text="  Browse  ", font=self.FONT_SMALL_BOLD, bg=self.BTN_BG,
            fg=self.FG, activebackground=self.ACCENT, activeforeground="#fff",
            relief="flat", cursor="hand2", command=self._browse_path, pady=4,
        )
        btn_browse.pack(side="right")

        # ── Row: Branch ──
        row = tk.Frame(inner, bg=self.BG_CARD)
        row.pack(fill="x", pady=(0, 12))
        self._make_label(row, "Branch", width=10).pack(side="left")

        self._all_branches = []  # store all branches for filtering
        self.combo_branch = ttk.Combobox(
            row, font=self.FONT, state="normal", width=30,
        )
        self.combo_branch.pack(side="left", fill="x", expand=True, ipady=5, padx=(4, 0))
        self.combo_branch.bind("<KeyRelease>", self._on_branch_keyrelease)

        # ── Row: Commit Regex ──
        row_regex = tk.Frame(inner, bg=self.BG_CARD)
        row_regex.pack(fill="x", pady=(0, 12))
        self._make_label(row_regex, "Commit\nRegex", width=10).pack(side="left")

        regex_container = tk.Frame(row_regex, bg=self.BG_CARD)
        regex_container.pack(side="left", fill="x", expand=True, padx=(4, 0))

        self.entry_regex = self._make_entry(regex_container, placeholder="Enter commit regex filter")
        self.entry_regex.pack(fill="x", ipady=7)

        # Regex suggestions dropdown
        self._regex_suggestions = [
            ("Merge",           "Match merge commits"),
            ("Merge|deploy",    "Merge or deploy commits"),
            ("^fix",            "Commits starting with 'fix'"),
            ("^feat",           "Commits starting with 'feat'"),
            ("^(fix|feat)",     "Fix or feat commits"),
            ("JIRA-[0-9]+",     "Match JIRA ticket IDs"),
            ("#[0-9]+",         "Match issue numbers (#123)"),
            (".",               "Match all commits (default)"),
        ]
        self._dropdown_frame = None
        self.entry_regex.bind("<FocusIn>", self._show_regex_dropdown)
        self.entry_regex.bind("<FocusOut>", lambda e: self.after(200, self._hide_regex_dropdown))

        # ── Row: Project Type ──
        row = tk.Frame(inner, bg=self.BG_CARD)
        row.pack(fill="x", pady=(0, 12))
        self._make_label(row, "Project\nType", width=10).pack(side="left", anchor="n", pady=(4, 0))

        badge_container = tk.Frame(row, bg=self.BG_CARD)
        badge_container.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Row 1: first 5 types
        badge_row1 = tk.Frame(badge_container, bg=self.BG_CARD)
        badge_row1.pack(fill="x", pady=(0, 6))
        for pt in PROJECT_TYPES[:5]:
            self._make_badge(badge_row1, pt)

        # Row 2: remaining types
        badge_row2 = tk.Frame(badge_container, bg=self.BG_CARD)
        badge_row2.pack(fill="x")
        for pt in PROJECT_TYPES[5:]:
            self._make_badge(badge_row2, pt)

        # ── Row: Date (DatePicker) ──
        row = tk.Frame(inner, bg=self.BG_CARD)
        row.pack(fill="x", pady=(0, 16))
        self._make_label(row, "Date", width=10).pack(side="left")

        date_container = tk.Frame(row, bg=self.BG_CARD)
        date_container.pack(side="left", fill="x", expand=True, padx=(4, 0))

        self.date_from = DateEntry(
            date_container, font=self.FONT_SMALL,
            background=self.BG_INPUT, foreground=self.FG,
            borderwidth=0, width=12, date_pattern="yyyy-mm-dd",
        )
        self.date_from.delete(0, "end")  # start empty
        self.date_from.pack(side="left", ipady=5)

        tk.Label(date_container, text="  to  ", font=self.FONT,
                 fg=self.FG_DIM, bg=self.BG_CARD).pack(side="left")

        self.date_to = DateEntry(
            date_container, font=self.FONT_SMALL,
            background=self.BG_INPUT, foreground=self.FG,
            borderwidth=0, width=12, date_pattern="yyyy-mm-dd",
        )
        self.date_to.delete(0, "end")  # start empty
        self.date_to.pack(side="left", ipady=5)

        btn_clear_date = tk.Button(
            date_container, text="  Clear  ", font=self.FONT_SMALL,
            bg=self.BTN_BG, fg=self.FG_DIM, relief="flat",
            cursor="hand2", command=self._clear_dates, pady=2,
        )
        btn_clear_date.pack(side="left", padx=(10, 0))

        # ── Count Button ──
        self.btn_count = tk.Button(
            inner, text="▶  Count KLOC", font=self.FONT_BOLD,
            bg=self.ACCENT, fg="#fff", activebackground=self.ACCENT_HOVER,
            activeforeground="#fff", relief="flat", cursor="hand2",
            pady=10, command=self._on_count,
        )
        self.btn_count.pack(fill="x", pady=(0, 16))

        # ── Result ──
        self._make_label(inner, "Result").pack(fill="x", anchor="w")
        self.result_text = tk.Text(
            inner, font=self.FONT_MONO, bg="#0a0f1e", fg=self.SUCCESS,
            relief="flat", bd=0, height=10, wrap="word", state="disabled",
            highlightthickness=1, highlightbackground=self.BORDER,
        )
        self.result_text.pack(fill="both", expand=True, pady=(4, 0))

    def _make_badge(self, parent, project_type):
        """Create a toggle badge button for a project type."""
        btn = tk.Button(
            parent, text=project_type, font=self.FONT_SMALL_BOLD,
            bg=self.BTN_BG, fg=self.BTN_FG, relief="flat",
            activebackground=self.ACCENT, activeforeground="#fff",
            cursor="hand2", width=11, pady=5, bd=0,
            highlightthickness=0,
            command=lambda p=project_type: self._toggle_project(p),
        )
        btn.pack(side="left", padx=(0, 8))
        self._project_buttons[project_type] = btn

    def _build_log_panel(self, parent):
        header = tk.Frame(parent, bg=self.BG_CARD)
        header.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(
            header, text="Process Log", font=self.FONT_BOLD,
            fg=self.FG_DIM, bg=self.BG_CARD, anchor="w",
        ).pack(side="left")

        self.log_text = tk.Text(
            parent, font=self.FONT_MONO, bg="#0a0f1e", fg="#7f8fa6",
            relief="flat", bd=0, wrap="word", state="disabled",
            highlightthickness=1, highlightbackground=self.BORDER,
        )
        self.log_text.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    # ── Project type toggle (multi-select) ───
    def _toggle_project(self, project_type):
        if project_type in self._selected_projects:
            self._selected_projects.discard(project_type)
        else:
            self._selected_projects.add(project_type)
        self._refresh_badges()

    def _refresh_badges(self):
        for pt, btn in self._project_buttons.items():
            if pt in self._selected_projects:
                btn.config(bg=self.ACCENT, fg=self.BTN_FG_ACTIVE)
            else:
                btn.config(bg=self.BTN_BG, fg=self.BTN_FG)

    # ── Regex dropdown suggestions ───────────
    def _show_regex_dropdown(self, event=None):
        self._hide_regex_dropdown()
        entry = self.entry_regex

        # Position dropdown below the entry
        x = entry.winfo_rootx() - self.winfo_rootx()
        y = entry.winfo_rooty() - self.winfo_rooty() + entry.winfo_height()

        self._dropdown_frame = tk.Frame(
            self, bg="#1e2d45", bd=1, relief="solid",
            highlightthickness=1, highlightbackground=self.ACCENT,
        )
        self._dropdown_frame.place(x=x, y=y, width=entry.winfo_width())
        self._dropdown_frame.lift()

        for pattern, desc in self._regex_suggestions:
            item = tk.Frame(self._dropdown_frame, bg="#1e2d45", cursor="hand2")
            item.pack(fill="x")

            lbl_pattern = tk.Label(
                item, text=pattern, font=self.FONT_SMALL_BOLD,
                fg=self.SUCCESS, bg="#1e2d45", anchor="w", padx=8, pady=3,
            )
            lbl_pattern.pack(side="left")

            lbl_desc = tk.Label(
                item, text=f"— {desc}", font=self.FONT_SMALL,
                fg=self.FG_DIM, bg="#1e2d45", anchor="w", padx=4, pady=3,
            )
            lbl_desc.pack(side="left", fill="x", expand=True)

            for widget in (item, lbl_pattern, lbl_desc):
                widget.bind("<Enter>", lambda e, i=item: i.config(bg="#2a3f5f"))
                widget.bind("<Leave>", lambda e, i=item: i.config(bg="#1e2d45"))
                widget.bind("<Enter>", lambda e, i=item, lp=lbl_pattern, ld=lbl_desc: (
                    i.config(bg="#2a3f5f"), lp.config(bg="#2a3f5f"), ld.config(bg="#2a3f5f")
                ))
                widget.bind("<Leave>", lambda e, i=item, lp=lbl_pattern, ld=lbl_desc: (
                    i.config(bg="#1e2d45"), lp.config(bg="#1e2d45"), ld.config(bg="#1e2d45")
                ))
                widget.bind("<Button-1>", lambda e, p=pattern: self._select_regex(p))

    def _hide_regex_dropdown(self):
        if self._dropdown_frame is not None:
            self._dropdown_frame.destroy()
            self._dropdown_frame = None

    def _select_regex(self, pattern):
        self.entry_regex.delete(0, "end")
        self.entry_regex.config(fg=self.FG)
        self.entry_regex.insert(0, pattern)
        self._hide_regex_dropdown()

    # ── Clear dates ──────────────────────────
    def _clear_dates(self):
        self.date_from.delete(0, "end")
        self.date_to.delete(0, "end")

    # ── Browse & auto-detect ─────────────────
    def _browse_path(self):
        path = filedialog.askdirectory(title="Select Git Repository Folder")
        if path:
            self.entry_path.delete(0, "end")
            self.entry_path.config(fg=self.FG)
            self.entry_path.insert(0, path)
            self._auto_detect(path)
            self._detect_branch(path)

    def _auto_detect(self, path):
        """Auto-detect project types and toggle their badges."""
        detected = detect_project_types(path)
        if detected:
            self._selected_projects = detected.copy()
            self._refresh_badges()
            self._append_log(f"Auto-detected: {', '.join(sorted(detected))}")
        else:
            self._append_log("Could not auto-detect project type. Please select manually.")

    def _detect_branch(self, path):
        """Fetch all branches and set default."""
        try:
            git_path = shutil.which("git") or "git"

            # Get all branches (local + remote)
            result = subprocess.run(
                [git_path, "branch", "-a", "--format=%(refname:short)"],
                capture_output=True, text=True, cwd=path,
            )
            branches = []
            for line in result.stdout.strip().splitlines():
                b = line.strip()
                if b and "HEAD" not in b:
                    branches.append(b)
            self._all_branches = sorted(set(branches))
            self.combo_branch["values"] = self._all_branches

            # Detect current branch
            result2 = subprocess.run(
                [git_path, "symbolic-ref", "--short", "HEAD"],
                capture_output=True, text=True, cwd=path,
            )
            current = result2.stdout.strip()
            if current:
                self.combo_branch.set(current)
                self._append_log(f"Default branch: {current}  ({len(self._all_branches)} branches found)")
        except Exception:
            pass

    def _on_branch_keyrelease(self, event):
        """Filter branch suggestions as user types."""
        # Ignore navigation/modifier keys
        if event.keysym in ("Up", "Down", "Left", "Right", "Return",
                            "Escape", "Tab", "Shift_L", "Shift_R",
                            "Control_L", "Control_R", "Alt_L", "Alt_R"):
            return
        typed = self.combo_branch.get().strip().lower()
        if not typed:
            self.combo_branch["values"] = self._all_branches
        else:
            filtered = [b for b in self._all_branches if typed in b.lower()]
            self.combo_branch["values"] = filtered

    # ── Log & Result helpers ─────────────────
    def _append_log(self, msg):
        def _do():
            self.log_text.config(state="normal")
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.after(0, _do)

    def _set_result(self, text):
        def _do():
            self.result_text.config(state="normal")
            self.result_text.delete("1.0", "end")
            self.result_text.insert("1.0", text)
            self.result_text.config(state="disabled")
        self.after(0, _do)

    def _set_running(self, running):
        def _do():
            self._is_running = running
            self.btn_count.config(
                state="disabled" if running else "normal",
                text="⏳  Counting..." if running else "▶  Count KLOC",
            )
        self.after(0, _do)

    def _get_entry_value(self, entry, placeholder=""):
        val = entry.get().strip()
        return "" if val == placeholder else val

    # ── Count action ─────────────────────────
    def _on_count(self):
        if self._is_running:
            return

        repo_path = self._get_entry_value(self.entry_path)
        if not repo_path:
            messagebox.showwarning("Warning", "Please select a repository path.")
            return
        if not os.path.isdir(repo_path):
            messagebox.showerror("Error", f"Path does not exist:\n{repo_path}")
            return
        if not self._selected_projects:
            messagebox.showwarning("Warning", "Please select at least 1 Project Type.")
            return

        branch = self.combo_branch.get().strip()
        commit_regex = self._get_entry_value(self.entry_regex, "Enter commit regex filter")

        # Read dates from DateEntry
        date_from_str = self.date_from.get().strip()
        date_to_str = self.date_to.get().strip()

        date_from = ""
        date_to = ""
        has_dates = False

        if date_from_str and date_to_str:
            try:
                df = datetime.strptime(date_from_str, "%Y-%m-%d")
                dt = datetime.strptime(date_to_str, "%Y-%m-%d")
                date_from = df.strftime("%Y%m%d")
                date_to = dt.strftime("%Y%m%d")
                has_dates = True
            except ValueError:
                pass  # treat as no date
        elif date_from_str or date_to_str:
            messagebox.showwarning("Warning", "Please select both From and To dates, or clear both.")
            return

        # Clear
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
        self._set_result("")

        self._set_running(True)
        thread = threading.Thread(
            target=self._run_count,
            args=(repo_path, list(self._selected_projects), branch,
                  commit_regex, date_from, date_to, has_dates),
            daemon=True,
        )
        thread.start()

    def _run_count(self, repo_path, project_types, branch,
                   commit_regex, date_from, date_to, has_dates):
        try:
            counter = KlocCounter(
                repo_path=repo_path,
                project_types=project_types,
                branch=branch,
                commit_regex=commit_regex,
                log_callback=self._append_log,
            )

            self._append_log(f"Branch: {branch or '(all)'}")
            self._append_log(f"Project types: {', '.join(sorted(project_types))}")

            # If no dates provided, auto-detect from git history
            if not has_dates:
                self._append_log("No date range specified. Auto-detecting from git history...")
                date_from, date_to = counter.get_date_range()
                if not date_from or not date_to:
                    self._set_result("No commits found in repository.")
                    return
                self._append_log(f"Date range: {date_from} → {date_to}")

            results = counter.count_monthly(date_from, date_to)
            lines = [
                f"From: {date_from}  To: {date_to}",
                f"Commit Regex: {commit_regex or '(all)'}",
                f"Project Type: {', '.join(sorted(project_types))}",
                "",
            ]
            if results:
                for r in results:
                    lines.append(
                        f"{r['month']}: {r['kloc']:.2f}  (lũy kế: {r['cumulative']:.2f})"
                    )
            else:
                lines.append("No commits found in this date range.")
            self._set_result("\n".join(lines))

            self._append_log("\n✓ Done.")
        except Exception as e:
            self._append_log(f"\n✗ Error: {e}")
            self._set_result(f"Error: {e}")
        finally:
            self._set_running(False)


# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = KlocApp()
    app.mainloop()
