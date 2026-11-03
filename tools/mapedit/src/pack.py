#!/usr/bin/env python3
"""Make the single-file MyV2 Editor from its two halves:
    python3 pack.py            -> ../mapedit.py  (the file that runs, in the Server folder and here)
The program is mapedit_template.py (it holds the marker @@PAGE@@), the web page is mapedit.html.
Edit those two, run this, then copy ../mapedit.py to the Windows Server folder and ask the editor
to restart itself (a control request {"action":"reload-editor"}), and the browser: F5."""
import os
here = os.path.dirname(os.path.abspath(__file__))
py = open(os.path.join(here, 'mapedit_template.py'), encoding='utf-8').read()
html = open(os.path.join(here, 'mapedit.html'), encoding='utf-8').read()
assert '@@PAGE@@' in py
open(os.path.join(here, '..', 'mapedit.py'), 'w', encoding='utf-8').write(py.replace('@@PAGE@@', html, 1))
print('wrote', os.path.normpath(os.path.join(here, '..', 'mapedit.py')))
