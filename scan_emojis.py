import os
import re
from pathlib import Path

ROOT_DIR = Path(".")
DIRS_TO_SCAN = [
    "accounts", "ai", "common", "config", "journal",
    "media_app", "notifications", "persons", "static", "tags", "templates"
]

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "]+",
    flags=re.UNICODE
)

results = {}

for d in DIRS_TO_SCAN:
    d_path = ROOT_DIR / d
    if not d_path.exists():
        continue
    for root, _, files in os.walk(d_path):
        for f in files:
            if f.endswith((".joblib", ".pyc", ".png", ".jpg", ".jpeg", ".ico", ".woff", ".woff2", ".ttf", ".eot")):
                continue
            f_path = Path(root) / f
            try:
                with open(f_path, "r", encoding="utf-8", errors="ignore") as file:
                    for line_num, line in enumerate(file, 1):
                        matches = EMOJI_PATTERN.findall(line)
                        if matches:
                            rel_p = str(f_path.as_posix())
                            if rel_p not in results:
                                results[rel_p] = []
                            results[rel_p].append((line_num, matches, line.strip()))
            except Exception as e:
                pass

output_lines = [f"Total files with emojis: {len(results)}\n"]
for file_p, hits in sorted(results.items()):
    output_lines.append(f"=== {file_p} ({len(hits)} lines) ===")
    for line_num, matches, line in hits:
        output_lines.append(f"  L{line_num} [{', '.join(matches)}]: {line[:120]}")
    output_lines.append("")

with open("emoji_scan_report.txt", "w", encoding="utf-8") as out:
    out.write("\n".join(output_lines))

print(f"Report written to emoji_scan_report.txt ({len(results)} files found)")
