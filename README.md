# Semantic mapper

A local Streamlit app that maps explicitly defined phrases to canonical concepts and optional details. No LLM, API key, embeddings, or external classification service is required.

## Run on Windows

Open PowerShell in this project folder:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

The first run creates `data/semantic_mapper.db` with three vehicle concepts and eight example mappings. Subsequent starts preserve edits and deletions. Back up this database to keep your mappings. The database is local to this computer and excluded from Git.

## Features

- Test one phrase or multiple phrases, one per line.
- Add concepts; add, edit, or delete phrase mappings.
- Delete unused concepts; reassign or remove their mappings first.
- Return a concept plus optional detail; unknown expressions return `UNMAPPED`.
- Import and export UTF-8 CSV with exact headers `phrase,concept,detail`.
- Dark theme configured in `.streamlit/config.toml`.

## Matching rules

Matching applies Unicode NFKC normalization, case folding, punctuation-to-space replacement, and whitespace collapsing. It then looks up the entire normalized phrase. There is no substring matching, word reordering, stemming, or semantic guessing. `Noise from wheel!` matches `noise from wheel`; `my wheel makes noise` remains unmapped unless explicitly added. Hyphenated words normalize to separate words; removing punctuation inside a word can therefore change its match.

Concepts and optional details use uppercase labels starting with a letter and containing letters, digits, and underscores. `UNMAPPED` is reserved. Normalized phrases are unique, preventing ambiguous results.

## CSV behavior

Import creates missing concepts and appends new mappings. Identical existing mappings are skipped. Conflicting existing phrases, duplicate normalized phrases within the file, invalid labels, and malformed rows reject the entire import. Export includes all mappings, without internal IDs. Empty concepts are not included in exports.

```csv
phrase,concept,detail
sound from wheel,WHEEL_NOISE,
rattling from tyre,WHEEL_NOISE,RATTLING
```

## Tests

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests use temporary databases. This first version is intended for local use; it has no sign-in or per-user workspace separation.
