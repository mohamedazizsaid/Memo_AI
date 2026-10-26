with open("emoji_scan_report.txt", "r", encoding="utf-8") as f:
    current_file = None
    file_hits = {}
    for line in f:
        line_clean = line.strip()
        if line_clean.startswith("=== "):
            current_file = line_clean.split("=== ")[1].split(" (")[0]
            file_hits[current_file] = []
        elif line_clean.startswith("L") and current_file:
            file_hits[current_file].append(line_clean)

# Filter out static vendor, css, and static previews
for f, hits in sorted(file_hits.items()):
    if f.startswith("static/vendor") or f.endswith((".css", ".html")) and f.startswith("static/"):
        continue
    print(f"\nFILE: {f} ({len(hits)} hits)")
    for h in hits[:15]:
        # print safely in ASCII
        print("  ", h.encode('ascii', 'backslashreplace').decode('ascii'))
