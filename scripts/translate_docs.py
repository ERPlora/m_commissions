#!/usr/bin/env python3
"""
translate_docs.py — Translate docs/en/**/*.md into target languages.

Usage:
    python scripts/translate_docs.py [--file docs/en/xxx.md] [--all] [--check]

Runs from repo root. Uses OPENAI_API_KEY env var.
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import click

# ── Config ────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_SRC = REPO_ROOT / "docs" / "en"
DOCS_ROOT = REPO_ROOT / "docs"
LOCK_FILE = DOCS_ROOT / ".translations.lock"

TARGET_LANGS = ["es", "fr", "it", "de", "pt"]

LANG_NAMES = {
    "es": "Spanish",
    "fr": "French",
    "it": "Italian",
    "de": "German",
    "pt": "Portuguese",
}

MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "Translate the following technical markdown to {lang_name}. "
    "Preserve markdown syntax, code blocks (untranslated), and mermaid blocks "
    "(untranslated). Translate only prose. "
    "Output only the translated markdown without preamble."
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_lock() -> dict:
    if LOCK_FILE.exists():
        return json.loads(LOCK_FILE.read_text())
    return {}


def save_lock(lock: dict) -> None:
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOCK_FILE.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")


def lock_key(en_path: Path) -> str:
    return str(en_path.relative_to(DOCS_SRC))


def target_path(en_path: Path, lang: str) -> Path:
    rel = en_path.relative_to(DOCS_SRC)
    return DOCS_ROOT / lang / rel


def needs_translation(en_path: Path, lock: dict) -> list[str]:
    """Return list of langs that need (re-)translation."""
    key = lock_key(en_path)
    content = en_path.read_text()
    current_sha = sha256_of(content)
    stored_sha = lock.get(key)

    missing_langs = []
    for lang in TARGET_LANGS:
        tp = target_path(en_path, lang)
        if stored_sha != current_sha or not tp.exists():
            missing_langs.append(lang)
    return missing_langs, current_sha


def translate_content(content: str, lang: str, api_key: str) -> str:
    """Call OpenAI with retry (2x backoff) and return translated markdown."""
    import openai

    client = openai.OpenAI(api_key=api_key)
    lang_name = LANG_NAMES.get(lang, lang)
    prompt = SYSTEM_PROMPT.format(lang_name=lang_name)

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content},
                ],
            )
            translated = response.choices[0].message.content
            if translated:
                return translated
        except Exception as e:
            if attempt < 2:
                wait = 2 ** attempt
                click.echo(
                    f"  [WARN] OpenAI error (attempt {attempt + 1}/3): {e} — retrying in {wait}s",
                    err=True,
                )
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Translation failed after 3 attempts")


def translate_file(en_path: Path, langs: list[str], api_key: str, lock: dict) -> str:
    """Translate en_path into each lang and update lock. Returns new sha."""
    content = en_path.read_text()
    current_sha = sha256_of(content)

    for lang in langs:
        tp = target_path(en_path, lang)
        click.echo(f"  Translating → {lang}: {en_path.relative_to(REPO_ROOT)}")
        try:
            translated = translate_content(content, lang, api_key)
            tp.parent.mkdir(parents=True, exist_ok=True)
            tp.write_text(translated)
            click.echo(f"    Saved: {tp.relative_to(REPO_ROOT)}")
        except Exception as e:
            click.echo(f"    [ERROR] {lang}: {e}", err=True)

    lock[lock_key(en_path)] = current_sha
    return current_sha


# ── CLI ───────────────────────────────────────────────────────────────────────


@click.command()
@click.option("--file", "target_file", default=None, help="Translate a specific docs/en/... file.")
@click.option("--all", "translate_all", is_flag=True, default=False, help="Translate all outdated files.")
@click.option(
    "--check",
    is_flag=True,
    default=False,
    help="Exit 1 if any translations are missing or outdated (for pre-commit).",
)
def main(target_file, translate_all, check):
    """Translate docs/en/**/*.md into ES, FR, IT, DE, PT."""

    if not DOCS_SRC.exists():
        if check:
            click.echo("[OK] docs/en/ not found — nothing to check.")
            sys.exit(0)
        click.echo("[INFO] docs/en/ not found — nothing to translate.")
        sys.exit(0)

    lock = load_lock()

    # ── --check mode ──────────────────────────────────────────────────────────
    if check:
        outdated = []
        for en_path in sorted(DOCS_SRC.rglob("*.md")):
            missing_langs, _ = needs_translation(en_path, lock)
            if missing_langs:
                outdated.append(f"  {en_path.relative_to(REPO_ROOT)} → needs: {', '.join(missing_langs)}")
        if outdated:
            click.echo("[FAIL] Docs translations are out of date:")
            for line in outdated:
                click.echo(line)
            click.echo("\nRun: python scripts/translate_docs.py --all")
            sys.exit(1)
        click.echo("[OK] All docs translations are up to date.")
        sys.exit(0)

    # ── Resolve API key ───────────────────────────────────────────────────────
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        click.echo("[ERROR] OPENAI_API_KEY env var is not set.", err=True)
        sys.exit(1)

    # ── --file mode ───────────────────────────────────────────────────────────
    if target_file:
        en_path = Path(target_file).resolve()
        if not en_path.exists():
            click.echo(f"[ERROR] File not found: {en_path}", err=True)
            sys.exit(1)
        if not str(en_path).startswith(str(DOCS_SRC)):
            click.echo(f"[ERROR] File must be inside docs/en/: {en_path}", err=True)
            sys.exit(1)
        missing_langs, _ = needs_translation(en_path, lock)
        if not missing_langs:
            click.echo(f"[SKIP] Already up to date: {en_path.relative_to(REPO_ROOT)}")
        else:
            translate_file(en_path, missing_langs, api_key, lock)
            save_lock(lock)
        sys.exit(0)

    # ── --all (default) ───────────────────────────────────────────────────────
    en_files = sorted(DOCS_SRC.rglob("*.md"))
    if not en_files:
        click.echo("[INFO] No .md files found in docs/en/")
        sys.exit(0)

    changed = False
    for en_path in en_files:
        missing_langs, _ = needs_translation(en_path, lock)
        if missing_langs:
            translate_file(en_path, missing_langs, api_key, lock)
            changed = True
        else:
            click.echo(f"[SKIP] {en_path.relative_to(REPO_ROOT)}")

    if changed:
        save_lock(lock)
        click.echo("[DONE] Translations updated and lock saved.")
    else:
        click.echo("[DONE] All translations already up to date.")


if __name__ == "__main__":
    main()
