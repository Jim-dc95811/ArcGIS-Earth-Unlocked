"""md2pdf.py <input.md> <output.pdf> "<footer title>"
Markdown -> clean print HTML -> PDF (Chromium via Playwright). Relative images resolve from the .md folder.
Links to other repo files become absolute GitHub links when GH_BASE is set (env), so they work inside the PDF."""
import os, re, sys, pathlib, markdown, asyncio
from playwright.async_api import async_playwright

src, out, title = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve(), sys.argv[3]
base = os.environ.get("GH_BASE")  # e.g. https://github.com/Jim-dc95811/Parcel100/blob/main/
md = src.read_text(encoding="utf-8")
if base:
    rel = os.path.relpath(src.parent, pathlib.Path(os.environ.get("REPO_ROOT", src.parent))).replace("\\", "/")
    prefix = "" if rel == "." else rel + "/"
    def fix(m):
        text, url = m.group(1), m.group(2)
        if re.match(r"^(https?:|mailto:|#)", url) or url.lower().endswith((".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp")):
            return m.group(0)
        path = os.path.normpath(prefix + url).replace("\\", "/")
        return f"[{text}]({base}{path})"
    md = re.sub(r"(?<!!)\[([^\]]+)\]\(([^)\s]+)\)", fix, md)
body = markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists", "attr_list"])
html = f"""<!doctype html><html><head><meta charset="utf-8"><base href="{src.parent.as_uri()}/">
<style>
@page {{ size: Letter; margin: 0.8in 0.75in 0.85in 0.75in; }}
body {{ font-family: "Segoe UI", "DejaVu Sans", Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #17212b; }}
h1 {{ font-size: 22pt; color: #0e355d; border-bottom: 3px solid #1269b0; padding-bottom: 6px; margin: 0 0 14px; }}
h2 {{ font-size: 14.5pt; color: #0e355d; margin: 20px 0 6px; border-bottom: 1px solid #d9e2ea; padding-bottom: 3px; page-break-after: avoid; }}
h3 {{ font-size: 12pt; color: #1269b0; margin: 14px 0 4px; page-break-after: avoid; }}
p, li {{ margin: 4px 0; }}
code {{ font-family: Consolas, "DejaVu Sans Mono", monospace; font-size: 9.2pt; background: #f1f4f7; padding: 1px 3px; border-radius: 3px; }}
pre {{ background: #f1f4f7; border: 1px solid #d9e2ea; border-radius: 5px; padding: 8px 10px; white-space: pre-wrap; word-break: break-word; page-break-inside: avoid; }}
pre code {{ background: none; padding: 0; }}
table {{ border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 9.6pt; page-break-inside: avoid; }}
th, td {{ border: 1px solid #c9d4de; padding: 4px 7px; text-align: left; vertical-align: top; }}
th {{ background: #e8eff6; }}
blockquote {{ border-left: 4px solid #f4b400; background: #fff8e1; margin: 8px 0; padding: 5px 12px; }}
img {{ max-width: 100%; }}
a {{ color: #1269b0; text-decoration: none; }}
</style></head><body>{body}</body></html>"""
tmp = out.with_suffix(".tmp.html"); tmp.write_text(html, encoding="utf-8")

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        await pg.goto(tmp.as_uri()); await pg.wait_for_load_state("networkidle")
        await pg.pdf(path=str(out), format="Letter", print_background=True, display_header_footer=True,
                     header_template="<span></span>",
                     footer_template=f'<div style="font-size:8pt;color:#5d6b78;width:100%;padding:0 0.75in;display:flex;justify-content:space-between;font-family:Arial"><span>{title}</span><span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>',
                     margin={"top": "0.7in", "bottom": "0.8in", "left": "0.75in", "right": "0.75in"})
        await b.close()
asyncio.run(main()); tmp.unlink()
print("wrote", out)
