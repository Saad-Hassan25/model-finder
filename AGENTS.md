# Working on Model Finder

- The canonical skill is `skills/model-finder/`. The root is also a Claude/Codex compatibility plugin.
- Keep `Initial Work/` local; do not depend on it, stage it, or include it in archives.
- Use current official documentation when changing client install formats or provider API contracts.
- No paid inference in repository tests or ordinary model research. Never commit credentials or real provider datasets.
- Preserve explicit model identity mapping and unknown benchmark/capability values. Catalog eligibility is not task viability.
- The Python helper and installer target Python 3.10+ with the standard library only.
- For code changes run `python -m unittest discover -s tests -v` and `python scripts/validate.py`. For packaging changes also run `python scripts/package.py`.
- Do not commit, push, or create a remote unless the user asks.
