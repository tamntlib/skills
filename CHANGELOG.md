# Changelog

## 1.0.0

- Package `translator` as a Claude Code plugin.
- Add marketplace metadata for command-based installation.
- Support translating from one source language into one or more target languages in a single request.
- Store glossary memory in `./proper-nouns.tsv` in the working folder so it can be committed to git.
- Keep lazy glossary creation so the file appears only when the first new term must be remembered.
- Use a multilingual TSV schema with one dynamic language-code column per language plus trailing `type` and `notes` columns.
- Update docs and evals for the current multilingual translator behavior.
