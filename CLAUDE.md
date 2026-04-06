# CLAUDE.md

This file provides context and guidance for AI assistants (Claude and others) working in this repository.

## Repository Overview

**ashishmanwani.github.io** is a personal GitHub Pages repository for Ashish Manwani. GitHub Pages automatically serves content from this repository at `https://ashishmanwani.github.io` (or a custom domain if a `CNAME` file is present).

### Current State (as of April 2026)

The repository is currently **empty** — all previous content (a minimal README and a CNAME file pointing to `rstkatni.me`) was deleted in April 2026. The repo is ready to be rebuilt with a new site.

### History

- **Aug 2025**: Repository initialized with a CNAME for the custom domain `rstkatni.me`
- **Apr 2026**: All content removed; repository reset to a clean slate

---

## GitHub Pages Conventions

When building or rebuilding this site, follow these GitHub Pages conventions:

### Serving Options

1. **Plain HTML/CSS/JS** — Place an `index.html` at the root; GitHub Pages will serve it directly with no build step.
2. **Jekyll** — GitHub Pages has native Jekyll support. Add a `_config.yml` to enable it. Jekyll processes Markdown, Liquid templates, and front matter automatically.
3. **Static Site Generator (SSG) output** — Build locally (e.g., with Hugo, Eleventy, Next.js export) and push the output to a `gh-pages` branch or `docs/` folder, then configure GitHub Pages in repo settings.

### Custom Domain

If restoring a custom domain:
- Add a `CNAME` file at the root containing exactly the domain (e.g., `rstkatni.me`), no `https://` prefix.
- Configure DNS at the domain registrar (A/CNAME records pointing to GitHub Pages IPs).

### Key Files

| File | Purpose |
|------|---------|
| `index.html` | Site entry point (or `index.md` with Jekyll) |
| `CNAME` | Custom domain configuration |
| `_config.yml` | Jekyll configuration (if using Jekyll) |
| `.nojekyll` | Disables Jekyll processing (needed for plain HTML or other SSGs) |
| `404.html` | Custom 404 page |

---

## Development Workflow

### Branch Strategy

- **`main`** — Production branch; GitHub Pages is configured to serve from `main`.
- **`claude/<feature-slug>`** — Feature branches for AI-assisted development (e.g., the branch this file was created on).
- Merge feature branches into `main` via pull request when ready to deploy.

### Making Changes

Since there is no build system currently:

```bash
# Edit files directly, then commit and push
git add <files>
git commit -m "descriptive commit message"
git push -u origin <branch-name>
```

If a build system is added in the future, document the build commands here.

### No Local Dev Server Required

For plain HTML sites, you can open `index.html` directly in a browser. If using Jekyll:

```bash
bundle exec jekyll serve
# Site available at http://localhost:4000
```

---

## Conventions for AI Assistants

### What to Do

- **Prefer minimal, standards-compliant HTML/CSS** — This is a personal site, not an enterprise app. Keep it simple.
- **Preserve the CNAME file** if one exists — deleting it breaks the custom domain.
- **Keep `CLAUDE.md` up to date** — If you significantly change the tech stack or conventions, update this file.
- **Use semantic HTML** — `<header>`, `<main>`, `<footer>`, `<nav>`, `<article>`, etc.
- **Commit with descriptive messages** — e.g., `"Add about section to homepage"` not `"Update index.html"`.

### What to Avoid

- Do not add heavy JavaScript frameworks (React, Vue, Angular) unless explicitly requested — a personal portfolio site rarely needs them.
- Do not add a build pipeline without explicit instructions — this increases complexity with little benefit for a simple static site.
- Do not commit generated build artifacts (e.g., `node_modules/`, `_site/`, `.next/`) to `main` unless the site is explicitly configured to serve from a build output directory.
- Do not push directly to `main` without a pull request when working on a feature branch.

### File Structure (Recommended Starting Point)

```
ashishmanwani.github.io/
├── CLAUDE.md          # This file
├── CNAME              # Custom domain (if applicable)
├── index.html         # Homepage
├── assets/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── main.js    # Only if needed
│   └── images/
└── 404.html           # Optional custom 404 page
```

---

## Repository Metadata

| Field | Value |
|-------|-------|
| Owner | Ashish Manwani (`ashishmanwani`) |
| Platform | GitHub Pages |
| Previous custom domain | `rstkatni.me` |
| Default branch | `main` |
| Last meaningful content | Aug 2025 (initial setup) |
