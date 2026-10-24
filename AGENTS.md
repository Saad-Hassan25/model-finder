# Working on Model Finder

If asked to install this repository, follow [INSTALL.md](INSTALL.md). Use the `npx` installer with explicit `--agent`, `--scope`, `--yes`, and `--json`; default to the user's current project unless global scope was requested. Report pending authentication separately from successful file installation.

- The canonical skill is `skills/model-finder/`. The root is also a Claude/Codex compatibility plugin.
- Keep `Initial Work/` local; do not depend on it, stage it, or include it in archives.
- Use current official documentation when changing client install formats or provider API contracts.
- No paid inference in repository tests or ordinary model research. Never commit credentials or real provider datasets.
- Preserve explicit model identity mapping and unknown benchmark/capability values. Catalog eligibility is not task viability.
- The research helper and legacy copy script target Python 3.10+ with the standard library only. The guided installer uses Node.js 22+; dependencies are pinned in package-lock.json.
- For code changes run `python -m unittest discover -s tests -v` and `python scripts/validate.py`. For packaging changes also run `python scripts/package.py`.
- For guided-installer changes run `npm ci --ignore-scripts` and `npm test`. Exercise npm packaging without touching the real user config; tests inject temporary home/project directories.
- Do not commit, push, or create a remote unless the user asks.
