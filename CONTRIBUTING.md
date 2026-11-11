# Contributing

Thanks for helping make these skills better.

## Issues welcome

The easiest way to help is to [open an issue](https://github.com/junifia/skills/issues) when:

- a skill gave a wrong or confusing answer (paste what you asked and what it said, with any private store data removed)
- an admin click path is out of date
- you have an idea for a new skill

## Pull requests

Small fixes are welcome. For anything bigger, open an issue first so we can agree on the approach.

Every skill follows the same rules:

- **Read-only.** A skill never changes the merchant's store.
- **No code in the output.** Merchants get plain-language reports or ready-to-paste drafts.
- **Works three ways:** connected store, CSV export, or store URL.
- **Plain English** for beginners. No em dashes.
- Ends with the line: `Built by Junifia. Want help acting on this? junifia.ca`

Skills live in `plugins/<plugin>/skills/<skill>/SKILL.md`. After editing, rebuild the Claude.ai zips:

```
python3 scripts/build-dist.py
```

The build also checks for em dashes and the closing line, and fails if either rule is broken.

## License

By contributing, you agree your contribution is licensed under the [MIT License](LICENSE).
