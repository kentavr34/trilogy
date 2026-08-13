# -*- coding: utf-8 -*-
"""Автосинхронизация в конце сессии (постановка Кенана 25.07.2026):
1) новые реплики из локальных транскриптов Claude -> RULES/ЧАТ_ДИАЛОГ.md (хронологический единый файл);
2) ЧАТ_ДИАЛОГ.md -> ЦНС /opt/claudia/illuminant/ (scp);
3) ЧАТ_ДИАЛОГ.md + CLAUDE.md + RULES/06_РЕЕСТР_И_ЖУРНАЛ.md -> Google Drive «ИЛЛЮМИНАНТ» (rclone на ЦНС).
Запускается хуком SessionEnd (.claude/settings.json). Ошибки не валят сессию.
"""
import json, os, re, glob, subprocess, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAT = os.path.join(ROOT, 'RULES', 'ЧАТ_ДИАЛОГ.md')
MARK = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'last_sync.txt')
TRANSCRIPTS = r'C:\Users\SAM\.claude\projects\D------------BOOKS-illumunant'
SSH = ['ssh', '-i', os.path.expanduser('~/.ssh/claude_deploy_key'), '-o', 'StrictHostKeyChecking=no',
       '-o', 'ConnectTimeout=10', 'root@45.67.216.36']
DRIVE_ID = '1AwvUF7VTKzztIGX4qF1wsW0ZZmjGUxrO'  # Drive: «ИЛЛЮМИНАНТ»

def text_of(msg):
    c = msg.get('content')
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return '\n'.join(b.get('text', '') for b in c if isinstance(b, dict) and b.get('type') == 'text')
    return ''

def collect_new(after_ts):
    rows = []
    for f in glob.glob(os.path.join(TRANSCRIPTS, '*.jsonl')):
        with open(f, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                if '"type":"user"' not in line and '"type":"assistant"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get('type') not in ('user', 'assistant'):
                    continue
                ts = d.get('timestamp') or ''
                if not ts or ts <= after_ts:
                    continue
                t = text_of(d.get('message') or {}).strip()
                if not t or t.startswith(('<system-reminder>', '<command-name>', '<local-command',
                                          '[Request interrupted', 'Caveat:', '<task-notification>')):
                    continue
                rows.append((ts, d['type'], t))
    rows.sort(key=lambda r: r[0])
    return rows

def append_chat(rows):
    out, cur_day = [], ''
    last = open(CHAT, encoding='utf-8').read()[-4000:] if os.path.exists(CHAT) else ''
    m = re.findall(r'^## (\d{4}-\d{2}-\d{2})', last, re.M)
    cur_day = m[-1] if m else ''
    for ts, role, t in rows:
        t = re.sub(r'\n{3,}', '\n\n', t)
        day, hm = ts[:10], ts[11:16]
        if day != cur_day:
            out.append(f"\n\n## {day}\n")
            cur_day = day
        if role == 'user':
            out.append(f"\n**[{hm} · локально] КЕНАН:** {t}\n")
        else:
            if len(t) > 400:
                t = t[:400].rsplit(' ', 1)[0] + ' […]'
            out.append(f"\n[{hm}] отв: {t}\n")
    with open(CHAT, 'a', encoding='utf-8') as f:
        f.write(''.join(out))

def main():
    after = open(MARK, encoding='utf-8').read().strip() if os.path.exists(MARK) else '2026-07-25T17:00'
    rows = collect_new(after)
    if rows:
        append_chat(rows)
        open(MARK, 'w', encoding='utf-8').write(rows[-1][0])
    # ЦНС + Drive (не критично при сбое сети)
    try:
        subprocess.run(['scp', '-i', os.path.expanduser('~/.ssh/claude_deploy_key'),
                        '-o', 'StrictHostKeyChecking=no', CHAT,
                        'root@45.67.216.36:/opt/claudia/illuminant/'], timeout=60, capture_output=True)
        subprocess.run(SSH + ['rclone copy "/opt/claudia/illuminant/ЧАТ_ДИАЛОГ.md" gdrive:RULES/ '
                              f'--drive-root-folder-id {DRIVE_ID}'], timeout=90, capture_output=True)
    except Exception as e:
        print(f'sync warn: {e}', file=sys.stderr)
    print(f'[illuminant-sync] +{len(rows)} новых реплик, {datetime.datetime.now():%H:%M}')

if __name__ == '__main__':
    main()
