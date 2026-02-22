import re
from pathlib import Path

root = Path(__file__).parent
changed = []

patterns = [
    # remove nav/blog anchor list items
    (re.compile(r'\n?\s*<li[^>]*>\s*<a[^>]*href=["\"][^"\"]*blog[^"\"]*["\"][^>]*>\s*Blog\s*</a>\s*</li>\s*', re.I), ''),
    (re.compile(r'\n?\s*<a[^>]*href=["\"][^"\"]*blog[^"\"]*["\"][^>]*>\s*Blog\s*</a>\s*', re.I), ''),
    # remove sections with id/class blog
    (re.compile(r'<section[^>]*(id|class)=["\"][^"\"]*blog[^"\"]*["\"][^>]*>[\s\S]*?</section>', re.I), ''),
    # remove headings titled Blog
    (re.compile(r'\n?\s*<h[1-6][^>]*>\s*Blog\s*</h[1-6]>\s*', re.I), ''),
]

for p in root.glob('*.html'):
    text = p.read_text(encoding='utf-8')
    original = text
    for rx, repl in patterns:
        text = rx.sub(repl, text)

    # clean double blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    if text != original:
        p.write_text(text, encoding='utf-8')
        changed.append(p.name)

# remove common standalone blog pages if present
for name in ['blog.html', 'blogs.html']:
    f = root / name
    if f.exists():
        f.unlink()
        changed.append(f'{name} (deleted)')

print('\n'.join(changed) if changed else 'No changes')
