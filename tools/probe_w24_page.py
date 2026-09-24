import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "src")
from ruwritingstyles import rcsi
meta = rcsi.article_meta("0131-2812", "article/351602")
html = meta.get("html", "")
print("citation_ count:", html.count("citation_"))
import re
m = re.search(r"<title>([^<]*)</title>", html)
print("page title:", m.group(1) if m else None)
m2 = re.search(r'name="citation_title"\s+content="([^"]*)"', html)
print("citation_title tag:", m2.group(1) if m2 else None)
i = html.find("citation_")
print("context:", html[max(0,i-200):i+200] if i>=0 else "none")
