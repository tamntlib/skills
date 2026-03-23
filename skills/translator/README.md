# translator

Claude Code plugin for translating from one source language into one or more target languages with stable glossary memory for proper nouns and special terms.

## Install from marketplace

```bash
claude plugin marketplace add tamntlib/skills
claude plugin install translator@tamnt-skills --scope user
```

Reload plugins in an active Claude Code session:

```text
/reload-plugins
```

## Install as a repo-local skill

If your team prefers repo-local skills instead of plugin installation, copy the skill into your project like this:

```text
your-project/
  .claude/
    skills/
      translator/
        SKILL.md
```

Then reload plugins in Claude Code:

```text
/reload-plugins
```

## Use

Invoke the skill by name:

```text
/translator:translator
```

Examples:
- Translate from Japanese to Vietnamese while keeping names and special terms stable
- Translate from Japanese to Vietnamese and English in one request
- Translate from Vietnamese to Japanese using previous glossary choices
- Translate from English to French and German while keeping target outputs separate

If the source language or target languages are not clear, the skill should ask once.

## Glossary behavior

The glossary starts empty and is stored in the working folder at:

- `./translator-glossary.tsv`

The file is created automatically only when the first new proper noun, special term, or preferred rendering needs to be remembered.

Glossary schema:
- one dynamic column per language code, such as `ja`, `en`, `vi`, `fr`
- fixed trailing columns:
  - `type`
  - `notes`

Each row is one multilingual glossary record for a proper noun or special term. New languages are added as new columns over time.

Because the file lives in the working folder, you can commit it to git if you want shared project terminology for proper nouns and special terms.

If you want one glossary per repository, run Claude from the repo root so the skill uses one repo-local `./translator-glossary.tsv` file.

## Output behavior

- Single target: returns only the translated text by default
- Multiple targets: returns labeled sections in the order requested, such as `## vi` and `## en`
