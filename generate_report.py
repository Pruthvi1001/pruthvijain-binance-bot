"""Generate report.html from report.md with embedded screenshots."""
import markdown
import base64
import os
import re

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Read markdown
with open('report.md', 'r') as f:
    md_content = f.read()

# Convert to HTML
html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])

# Embed images as base64
pattern = r'<img\s+([^>]*?)src="([^"]+)"([^>]*?)/?>'
def replace_img(match):
    prefix, img_path, suffix = match.group(1), match.group(2), match.group(3)
    if os.path.exists(img_path):
        with open(img_path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode()
        ext = img_path.rsplit('.', 1)[-1].lower()
        mime = 'image/png' if ext == 'png' else 'image/jpeg'
        return f'<img {prefix}src="data:{mime};base64,{b64}"{suffix} style="max-width:100%;border:1px solid #ddd;border-radius:8px;margin:12px 0;" />'
    print(f"  WARNING: Image not found: {img_path}")
    return match.group(0)

html_body = re.sub(pattern, replace_img, html_body)

# Build full HTML
html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #1a1a2e; }}
  h1 {{ color: #16213e; border-bottom: 3px solid #0f3460; padding-bottom: 10px; }}
  h2 {{ color: #0f3460; border-bottom: 1px solid #e0e0e0; padding-bottom: 6px; margin-top: 40px; }}
  h3 {{ color: #533483; }}
  table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
  th {{ background: #0f3460; color: white; }}
  tr:nth-child(even) {{ background: #f8f9fa; }}
  code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
  pre {{ background: #1a1a2e; color: #e0e0e0; padding: 16px; border-radius: 8px; overflow-x: auto; }}
  pre code {{ background: none; color: inherit; }}
  img {{ max-width: 100%; }}
  blockquote {{ border-left: 4px solid #0f3460; margin: 16px 0; padding: 8px 16px; background: #f0f4ff; }}
</style>
</head>
<body>
{html_body}
</body>
</html>'''

with open('report.html', 'w') as f:
    f.write(html)
print(f"✅ report.html generated ({len(html):,} bytes)")
