# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is the source for Odoo's official documentation (odoo.com/documentation), built with **Sphinx**
from **reStructuredText (RST)** files. There is no application code to run — the deliverable is
static HTML generated from `content/`. A custom `odoo_theme` Sphinx extension and several other
custom extensions control rendering.

## Common commands

```bash
# Setup (once)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Build the full site to _build/html/
make html

# Faster build for local iteration (collapses the sidebar menu)
make fast

# Remove build artifacts
make clean

# Build only one language
make html CURRENT_LANG=fr

# Build with language switcher enabled (must be run once per CURRENT_LANG)
make html CURRENT_LANG=fr LANGUAGES=en,fr,de

# Build with version switcher enabled (must be run once per version)
make html VERSIONS=17.0,18.0,saas-18.4,19.0,master

# Lint/test all content (same check CI runs as "documentation_guideline")
make test

# Lint one path interactively with a custom max line length (manual review tool)
make review
```

Output is written to `_build/html/index.html` (or `_build/html/<version>/<lang>/index.html` when
`VERSIONS`/`CURRENT_LANG` are set). `make test`/`make review` invoke `tests/main.py`, a wrapper
around `sphinxlint` plus custom checkers in `tests/checkers/`; there is no separate
unit-test suite for the extensions.

### Running a subset of lint checks

`tests/main.py` takes file/directory paths, so you can lint just the file(s) you changed instead of
the whole tree:

```bash
python tests/main.py content/applications/sales/crm/acquire_leads.rst
```

Pass `--max-line-length=N` (only meaningful with `REVIEW=1`, which `make review` sets) to check the
100-character line-length rule and the early-line-break rule — both disabled by default and only
enforced during manual review, not in CI's `make test`.

### Optional local Odoo/upgrade-util sources

The "Developer" section under `content/developer/` uses Sphinx `autodoc` to pull Python docstrings
live from the `odoo/odoo` and `odoo/upgrade-util` repos. Without them, `conf.py` falls back to an
`autodoc_placeholder` extension and those directives are skipped (with a warning), so the build still
succeeds. To get full developer-doc rendering, clone (or symlink) `odoo` and `upgrade-util` as
siblings of this repo, or inside it, on a matching branch/version.

## Architecture

- **`content/`** — the actual documentation source, organized by top-level `.rst` "index" files each
  with a matching directory of sub-pages (`administration.rst` + `administration/`,
  `applications.rst` + `applications/`, `developer.rst` + `developer/`, `contributing.rst` +
  `contributing/`, `legal.rst` + `legal/`). This mirrors the site's navigation tree — every page must
  appear in a `toctree` directive somewhere unless marked `orphan`.
- **`conf.py`** — the single Sphinx configuration file. It computes version metadata
  (`version`/`release`/`current_branch`/`current_version`), detects local `odoo`/`upgrade-util`
  checkouts to decide whether `autodoc` runs for real or is stubbed, defines `languages_names` (the
  full list of supported locales), and assembles the `extensions` list.
- **`extensions/`** — custom Sphinx extensions, each a self-contained Python package registered in
  `conf.py`'s `extensions` list:
  - `odoo_theme` — the actual HTML theme (templates + SCSS in `static/`); `make html` compiles its
    SCSS to `_build/html/_static/style.css` as a Makefile prerequisite.
  - `custom_admonitions` — adds the `example`/`exercise` admonition directives used throughout docs.
  - `cards`, `spoilers`, `embedded_video`, `html_domain` — custom RST directives (`card`/`cards`,
    `spoiler`, `youtube`/`vimeo`, etc.).
  - `redirects` — generates redirect pages from the `redirects/*.txt` files at build time.
  - `github_link`, `autodoc_field`, `autodoc_placeholder` — support the Developer docs' Python
    autodoc integration described above.
  - `graphviz_placeholder` — stub used when the `dot` binary isn't installed on the build machine.
- **`locale/`** — gettext `.po` translation files per language (managed via Weblate, see
  `.weblate.json`); `.pot` templates are regenerated with `make gettext` and exported to
  `locale/sources` by default.
- **`redirects/*.txt`** — one file per documentation version (e.g. `19.0.txt`), each holding
  `old/path.rst new/path.rst` line pairs grouped under `# section` comments. Required whenever an
  `.rst` file is moved or deleted (see "Moving/deleting pages" below).
- **`invs/`** — pre-fetched Sphinx intersphinx inventories (`python.inv`, `werkzeug.inv`) so
  cross-project references resolve without hitting the network at build time.
- **`static/`** — global assets (`css/`, `js/`, `img/`) copied verbatim into the built site (`make
  static`), separate from the theme's own `extensions/odoo_theme/static/`.
- **`tests/`** — `main.py` drives `sphinxlint` with this repo's custom directive list and custom
  checkers in `tests/checkers/` (`resource_files.py` validates image size/color depth/naming/usage,
  `rst_style.py` has the opt-in line-length/early-break checks, `redirect_rules.py` validates the
  `redirects/*.txt` format).

## Content conventions (enforced by `make test` / reviewed in PRs)

Full guides live at `content/contributing/documentation/rst_guidelines.rst` and
`content/contributing/documentation/content_guidelines.rst` — read those before writing docs. Key
points worth remembering while editing:

- **One H1 per file.** Heading underline characters, in order: `=` (H1/H2), `-` (H3), `~` (H4), `*`
  (H5), `^` (H6). The underline must be exactly as long as the heading text.
- **Indent with spaces only**, aligned to the character above (commonly 3 spaces for directive
  bodies, 2 for list continuations) — never tabs.
- Prefer wrapping lines under 100 characters (only checked when `REVIEW=1`, i.e. `make review`, not
  in default `make test`/CI).
- Every `.rst` file must be reachable from a `toctree` directive unless it declares the `orphan`
  document-metadata markup. Other document-metadata markups: `show-content`, `show-toc`,
  `hide-page-toc`, `nosearch`, `code-column`, `custom-css`, `custom-js`, `classes` — set as
  colon-delimited fields at the very top of the file.
- Use the semantic roles/directives instead of plain bold/italic where applicable:
  `:menuselection:` for UI navigation paths, `:guilabel:` for buttons/fields/labels, `example`/
  `exercise` custom admonitions, standard `note`/`tip`/`important`/`warning` admonitions.
- **Moving or deleting a page**: add a redirect entry to the `redirects/<version>.txt` file matching
  the branch you're working on, under the relevant `# path/section` comment block — `old/path.rst
  new/path.rst`.
- Titles/headings: sentence case, no leading pronouns, avoid "how to" phrasing, be concise.

## Commit message convention

This repo uses its own tag set (distinct from the general Odoo `git_guidelines.rst`, which lists a
broader tag list for the main product codebase). See `commit_template.txt`, configurable via
`git config commit.template commit_template.txt`:

```
[TAG] application/module: describe your changes in a short sentence
```

Tags: `[ADD]` new content, `[IMP]` improvement, `[FIX]` content or RST fix, `[REM]` removal, `[REF]`
refactoring/restructuring, `[MOV]` move/rename. Explain *why* in the body; the diff already shows
*what*.

## Versioning model

The docs are versioned per Odoo release (currently `19.0`, set via `version`/`release` in `conf.py`).
Content changes normally target the branch matching the Odoo version they document; check which
branch you're on (`current_branch` in `conf.py`) before editing version-sensitive content or
`redirects/` files.
