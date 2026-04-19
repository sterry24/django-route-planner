"""Sphinx configuration for django-route-planner.

Configures Django before autodoc imports any app modules — Django models and
views can't be imported without ``DJANGO_SETTINGS_MODULE`` and ``setup()``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Make the project root importable so ``import routes``, ``import planning``,
# etc. work the same way they do in ``manage.py``.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'planner_project.settings')

import django  # noqa: E402

django.setup()


# -- Project information -----------------------------------------------------

project = 'django-route-planner'
copyright = '2026, django-route-planner contributors'
author = 'django-route-planner contributors'
release = '0.1'


# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Napoleon: use Google-style docstrings (the style used throughout the code).
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_use_param = True
napoleon_use_rtype = True
# Render Google-style ``Attributes:`` blocks as :ivar: entries rather than
# standalone py:attribute directives — avoids duplicate-description warnings
# when autodoc also picks up the same Django model fields.
napoleon_use_ivar = True

# Cross-link to Django's docs so e.g. :class:`django.db.models.Model` resolves.
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'django': (
        'https://docs.djangoproject.com/en/stable/',
        'https://docs.djangoproject.com/en/stable/_objects/',
    ),
}

autodoc_default_options = {
    'members': True,
    'undoc-members': False,
    'show-inheritance': True,
}

# Django model fields appear both in the class' "Attributes" docstring block
# and as separate autodoc entries — silence the resulting duplicate warnings.
suppress_warnings = ['ref.python']

# Skip imports that aren't installed in the docs build environment so Sphinx
# autodoc can still run on a minimal set of dependencies.
autodoc_mock_imports: list[str] = []


# -- HTML output -------------------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
