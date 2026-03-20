# tamnt-skills

Claude Code marketplace repository for installable skills published by tamnt.

## Install from GitHub

Add this marketplace, then install the plugin you want:

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

## Included plugins

- [`translator`](skills/translator/README.md) — translate from one source language into one or more target languages with stable proper-noun glossary memory

## Development

Validate the plugin marketplace:

```bash
claude plugin validate .
```

Load it directly during development:

```bash
claude --plugin-dir .
```
