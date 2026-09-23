"""Remove exactly the unused import names pyflakes reports, leaving deliberate ones alone."""
import re, subprocess, sys
from pathlib import Path

KEEP = {  # (file substring, name): reason
    ("sandbox/pool.py", "sympy"), ("sandbox/pool.py", "mpmath"), ("sandbox/pool.py", "z3"),
}

def unused(paths):
    out = subprocess.run([sys.executable, "-m", "pyflakes", *paths], capture_output=True, text=True).stdout
    rows = []
    for line in out.splitlines():
        m = re.match(r"^(.*?):(\d+):\d+: '(.+?)' imported but unused$", line)
        if m:
            rows.append((m.group(1).replace("\\", "/"), int(m.group(2)), m.group(3)))
    return rows

def name_of(dotted):
    return dotted.split(" as ")[-1].strip() if " as " in dotted else dotted.split(".")[-1]

def main():
    paths = sys.argv[1:]
    rows = unused(paths)
    byfile = {}
    for f, ln, dotted in rows:
        if any(k[0] in f and k[1] == name_of(dotted) for k in KEEP):
            continue
        byfile.setdefault(f, []).append((ln, name_of(dotted)))
    changed = 0
    for f, items in byfile.items():
        p = Path(f)
        lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
        for ln, name in sorted(items, reverse=True):
            i = ln - 1
            # an import may span several lines (parenthesised); join the statement
            j = i
            while lines[j].rstrip().endswith(("(", ",", "\\")) or (lines[j].count("(") > lines[j].count(")")):
                j += 1
                if j >= len(lines):
                    break
            stmt = "".join(lines[i:j + 1])
            if re.match(r"\s*from .+ import ", stmt):
                new = re.sub(r"(?<![\w.])" + re.escape(name) + r"(?![\w])\s*,\s*", "", stmt, count=1)
                if new == stmt:
                    new = re.sub(r",\s*(?<![\w.])" + re.escape(name) + r"(?![\w])", "", stmt, count=1)
                if new == stmt:
                    continue
                new = re.sub(r"import\s*\(\s*\)", "import ()", new)
                if re.search(r"import\s*$", new.rstrip()) or re.search(r"import\s*\(\s*\)", new):
                    continue  # would empty the import: leave it
            else:
                continue
            lines[i:j + 1] = [new]
            changed += 1
        p.write_text("".join(lines), encoding="utf-8")
    print(f"removed {changed} unused import names from {len(byfile)} files")

main()
