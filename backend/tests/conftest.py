

# Portable synthetic-document fonts for Windows and Linux test environments.
# This affects test fixtures only; no identity evidence is altered.
from pathlib import Path as _FontPath

def synthetic_font(size, family='mono', style='regular'):
    from PIL import ImageFont
    import os
    names = (['DejaVuSansCondensed-Oblique.ttf', 'DejaVuSans-Oblique.ttf'] if style == 'oblique' else
             ['DejaVuSansMono.ttf', 'LiberationMono-Regular.ttf', 'consola.ttf', 'lucon.ttf', 'cour.ttf'] if family == 'mono' else
             ['DejaVuSans.ttf', 'LiberationSans-Regular.ttf', 'arial.ttf', 'calibri.ttf'])
    roots = [os.environ.get('SAFE_LOAD_TEST_FONT_DIR', ''),
             '/usr/share/fonts/truetype/dejavu', '/usr/share/fonts/truetype/liberation2',
             'C:/Windows/Fonts', '/Library/Fonts']
    for root in roots:
        if not root: continue
        for name in names:
            candidate = _FontPath(root) / name
            if candidate.is_file():
                return ImageFont.truetype(str(candidate), size)
    # Pillow bundles DejaVu fonts on some installations.
    for name in names:
        try: return ImageFont.truetype(name, size)
        except OSError: pass
    return ImageFont.load_default(size=size)
