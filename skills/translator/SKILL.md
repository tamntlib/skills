---
name: translator
description: Translate from one source language into one or more target languages with stable proper-noun mapping. Use this skill whenever the user asks for translation, bilingual or multilingual copy adaptation, glossary harmonization, or wants names, brands, teams, products, projects, and place names translated the same way across repeated requests. Also use it when the user asks to remember preferred translations for future multilingual work.
allowed-tools: Read, Write, Edit, Glob, Grep
version: 1.2.0
---

# Translator

Translate from one source language into one or more target languages while keeping proper nouns stable across future translations.

The main job of this skill is not only to translate well, but also to stop naming drift. A person, product, team, brand, project, location, program, or document title should not be translated one way today and a different way later unless the user explicitly asks for a change.

## Glossary memory

Use one writable glossary file in the working folder:
- `./proper-nouns.tsv`

The glossary starts empty. Do not assume the file already exists.

Create `proper-nouns.tsv` only when a new proper noun or preferred rendering must be persisted for the first time.

The TSV schema is dynamic:
- one column per language, named by normalized short code such as `ja`, `en`, `vi`, `fr`
- fixed metadata columns at the end:
  - `type`
  - `notes`

Example header:
- `ja`
- `vi`
- `en`
- `type`
- `notes`

Each row represents one entity or concept.
- A populated language cell stores the preferred rendering in that language.
- A blank language cell means that rendering is not known yet.
- The same row can accumulate more language columns over time.

## When this skill should act

Use this workflow when the user asks to:
- translate from one language into one or more other languages
- keep terminology or names consistent across messages
- build or maintain a bilingual or multilingual glossary
- reuse previous translations for names, products, brands, teams, screens, or document titles

## Workflow

### 1. Resolve the source language and target languages

Detect whether the request clearly specifies:
- source language
- one or more target languages
- mixed / bilingual cleanup

Accept either full language names or common codes such as `Japanese` / `ja`, `Vietnamese` / `vi`, `English` / `en`, `French` / `fr`.

Accept requests like:
- `ja -> vi`
- `ja -> vi,en`
- `translate from Japanese to Vietnamese and English`

If the source language is unclear, ask once before translating.
If the target language list is unclear, ask once before translating.

### 2. Read the glossary if it exists

Before translating, try to read `./proper-nouns.tsv`.

If the file does not exist yet:
- continue translating normally
- do not create the file unless a new term must be saved

If the file exists:
- treat each row as one multilingual entity record
- match using the source language column for the current request
- for each requested target language, reuse the existing target-language cell when it is populated

### 3. Identify proper nouns before translating

Scan the source for entities that should stay stable across requests, especially:
- person names
- company / brand names
- product names
- project names
- team names
- place names
- event names
- feature names
- document or feature names used like titles

Do this before drafting the translations so the translations and glossary stay aligned.

### 4. Apply existing mappings exactly

If a row matches the source entity in the current source-language column:
- reuse each populated target-language cell exactly for the requested targets
- keep it consistent everywhere in that target output
- do not invent a second rendering for the same entity in that target output

Normalize only minor whitespace differences when matching. Do not silently replace one stored entity with a different one just because it sounds more natural in the moment.

### 5. Handle unseen proper nouns

If an entity is missing from the glossary, or an existing row lacks one of the requested target-language cells:
1. infer the best target-language form from the source and context
2. use that form consistently in the translation
3. after translating, persist it in `./proper-nouns.tsv`

Persistence rules:
- if the file does not exist yet, create it only now
- initialize the header with the source language, all requested target languages, then `type` and `notes`
- if a later request introduces a new language, append that language column before `type` and `notes`
- if a matching row already exists, fill the missing target-language cell in that row
- if no matching row exists, create one new row and populate the source-language cell plus all requested target-language cells that were learned in this request
- one multi-target request should update one shared multilingual row per entity, not one row per target direction

Prefer official or already-obvious public forms when they are clear from the text. If there is no obvious official form, choose the most defensible natural rendering and make it canonical.

### 6. Update the glossary carefully

When adding or revising entries:
- keep the header row intact
- keep `type` and `notes` as the last columns
- avoid duplicate rows for the same entity
- preserve existing renderings unless the user explicitly asks to rename something
- rewrite the file in a clean, normalized state if needed instead of appending messy duplicates
- keep notes short and useful

Only change an existing rendering when one of these is true:
- the user explicitly requests a new preferred translation for that language
- the stored rendering is clearly wrong for the same entity

When updating one language for an entity, do not overwrite other populated language cells for that row.

### 7. Default output

If exactly one target language is requested, return only the translated text by default.

If multiple target languages are requested, return labeled sections in the same order requested by the user, for example:

```markdown
## vi
<translated Vietnamese text>

## en
<translated English text>
```

Do not add commentary, glossary dumps, or translation notes unless:
- the user asks for them, or
- there is a genuine ambiguity that could change meaning materially

If there is a serious ambiguity, keep the note short and specific.

## Translation guidance

- Keep meaning, tone, and intent intact.
- Prefer natural target-language phrasing for the sentence body.
- Keep proper nouns stable even when the surrounding sentence is heavily rewritten for fluency.
- Preserve honorific or register nuance only when it matters to meaning or tone.
- Do not over-literalize source-language sentence structure into the target language.
- Preserve the order of requested target languages in multi-target output.
- Treat each row as a shared multilingual record: adding a new language should extend the row, not duplicate it.

## Conflict handling

If the source text suggests two different entities with very similar names:
- do not merge them into one glossary row
- keep separate multilingual rows
- ask a clarification question only when the distinction is necessary to avoid a likely mistake

If the user asks to override a stored name for a specific document only, follow the request for that document and mention the glossary should be updated only if they want the new form to become the default.

## Suggested response shapes

### Single-target translation

Return only the translated text.

### Multi-target translation

Use this format:

```markdown
## <target_lang>
<translated text>

## <target_lang>
<translated text>
```

### If the user asks for glossary visibility

Use this format:

```markdown
## <target_lang>
<translated text>

### Proper nouns used
- <source_lang>: <source_value> → <target_lang>: <target_value>
- <source_lang>: <source_value> → <target_lang>: <target_value>
```

## Example

**Example 1**

Input:
Translate from Japanese to Vietnamese and English: `PhoenixチームはAsteria Pulse Reviewの検証を開始しました。`

Output:

```markdown
## vi
Đội Phoenix đã bắt đầu xác minh Asteria Pulse Review.

## en
The Phoenix team has started validating Asteria Pulse Review.
```

If the glossary file does not exist yet and `Phoenixチーム` or `Asteria Pulse Review` needs to be remembered, create `./proper-nouns.tsv` in the working folder and add one multilingual row per entity with `ja`, `vi`, `en`, `type`, and `notes` columns.
