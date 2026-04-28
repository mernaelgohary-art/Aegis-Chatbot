import os
import sys
from datetime import date

# 1. PATH SETUP
# This allows Sphinx to "read" your aegis_app.py and benchmark.py files
sys.path.insert(0, os.path.abspath('..'))

# 2. PROJECT INFORMATION
project = 'Aegis: Cyber-Physical Digital Twin'
copyright = f'{date.today().year}, Merna Hazem Mohamed Elgohary'
author = 'Merna Hazem Mohamed Elgohary'
version = '1.0'
release = '1.0.0'

# 3. GENERAL CONFIGURATION
# 'myst_parser' allows you to use Markdown (.md) instead of the old .rst format
extensions = [
    'myst_parser',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx_copybutton',
]

# Support for both Markdown and reStructuredText
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# 4. MYST PARSER SETTINGS (For professional tables and icons)
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "tasklist",
]

# 5. OPTIONS FOR HTML OUTPUT
# This gives you the clean, professional sidebar look
html_theme = 'sphinx_rtd_theme'
html_title = "Aegis Technical Reference"
html_static_path = ['_static']

# This removes the "Created using Sphinx" text at the bottom for a cleaner look
html_show_sphinx = False