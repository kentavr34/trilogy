#!/usr/bin/env python3
"""
Синхронизация Иллюминант → GitHub
Запускать в конце каждой рабочей сессии.
"""

import os, subprocess, shutil, sys
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(__file__), ".github_config")
config = {}
with open(CONFIG_FILE) as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            config[k] = v

TOKEN = config["GITHUB_TOKEN"]
REPO  = config["GITHUB_REPO"]
BASE  = config["GITHUB_BASE_PATH"]   # "claude"

LOCAL = os.path.dirname(os.path.abspath(__file__))  # папка Иллюминант
CLONE = "/tmp/illuminant_sync_repo"

# ── Clone / update ─────────────────────────────────────────────────────────
REMOTE = f"https://{TOKEN}@github.com/{REPO}.git"

if os.path.exists(CLONE):
    subprocess.run(["git", "-C", CLONE, "pull", "--rebase"], check=True)
else:
    subprocess.run(["git", "clone", REMOTE, CLONE], check=True)

subprocess.run(["git", "-C", CLONE, "config", "user.email", "rpm.baku@gmail.com"], check=True)
subprocess.run(["git", "-C", CLONE, "config", "user.name",  "Kenan Rahimov"],       check=True)

TARGET = os.path.join(CLONE, BASE)
os.makedirs(TARGET, exist_ok=True)

# ── Mapping: local folder → github subfolder ───────────────────────────────
MAPPINGS = [
    # (local_subdir_or_file,  github_subdir,  pattern)
    ("КНИГА_I_ФИНАЛ",         "Book_1",        "*.md"),
    ("КНИГА_I",               "Book_1/drafts", "*.md"),
    ("КНИГА_II",              "Book_2",        "*.md"),
    ("КНИГА_III",             "Book_3",        "*.md"),
    # Rules
    ("РОАДМАП_ТРИЛОГИИ_ИЛЛЮМИНАНТ.md",  "Rules/РОАДМАП_ТРИЛОГИИ.md",     None),
    ("МАСТЕР-ПЛАН_ТРИЛОГИИ_ФИНАЛ.md",   "Rules/МАСТЕР-ПЛАН_ТРИЛОГИИ.md", None),
    ("НАХОДКИ_ИЗ_СТАРЫХ_ВЕРСИЙ.md",     "Rules/НАХОДКИ_ИЗ_СТАРЫХ_ВЕРСИЙ.md", None),
]

copied = 0
for src_rel, dst_rel, pattern in MAPPINGS:
    src = os.path.join(LOCAL, src_rel)
    dst = os.path.join(TARGET, dst_rel)

    if pattern is None:
        # single file
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
    else:
        # directory
        if os.path.isdir(src):
            os.makedirs(dst, exist_ok=True)
            import glob
            for fpath in glob.glob(os.path.join(src, pattern)):
                shutil.copy2(fpath, os.path.join(dst, os.path.basename(fpath)))
                copied += 1

print(f"Copied {copied} files.")

# ── chat.md — update timestamp ─────────────────────────────────────────────
chat_path = os.path.join(TARGET, "Rules", "chat.md")
if os.path.exists(chat_path):
    with open(chat_path, "a") as f:
        f.write(f"\n---\n*Синхронизировано: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

# ── Commit & push ──────────────────────────────────────────────────────────
subprocess.run(["git", "-C", CLONE, "add", BASE], check=True)

result = subprocess.run(["git", "-C", CLONE, "status", "--short"], capture_output=True, text=True)
if not result.stdout.strip():
    print("Nothing to commit.")
    sys.exit(0)

msg = f"📚 Illuminant sync {datetime.now().strftime('%Y-%m-%d %H:%M')}"
subprocess.run(["git", "-C", CLONE, "commit", "-m", msg], check=True)
subprocess.run(["git", "-C", CLONE, "push", REMOTE, "main"], check=True)

print("✓ Pushed to GitHub successfully.")
