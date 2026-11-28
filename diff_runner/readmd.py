import re


def parse_md(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    m = re.search(r'<!--\s*AIOJ-META(.*?)-->', text, re.S)
    meta = m.group(1) if m else ""
    tl = re.search(r'TL:\s*(\d+(?:\.\d{1,3})?)\s*s?', meta)
    timeout_md = float(tl.group(1)) if tl else None
    return timeout_md
