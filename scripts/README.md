# Scripts

The scripts were run in the author's working layout, where `lit/` holds `extract/`, `code2/`, `audit/`, `pages/` (page-
numbered text of each source, not redistributed) and `pdfs/`. To rerun them, rebuild that layout:

1. `fetch.py` downloads the open-access PDFs listed in the corpus (arXiv and Zenodo) into `lit/pdfs/`.
2. Convert each PDF to page-marked text: `pdftotext -f p -l p -layout file.pdf -` per page, with a line
   `=== PAGE p ===` before each page, into `lit/pages/<key>.txt`.
3. `verify_quotes.py` checks every quote in `lit/extract/*.json` against `lit/pages/` (whitespace and hyphenation
   normalised).
4. `fetch_refs.py` resolves every DOI to CSL-JSON (`lit/refs.json`).
5. `build_tables.py` and `build_v03.py` rebuild the tables and figure data (`WSP_LIT=lit WSP_OUT=out`).

The extraction and coding forms are in `data/EXTRACT_SPEC.md` and `data/CODE2_SPEC.md`.
