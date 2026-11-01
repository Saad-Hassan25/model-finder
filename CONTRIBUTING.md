# Contributing

Keep model facts live and the skill portable. Do not commit current rankings, real API keys, personal configuration, or bulk provider datasets.

Use Node.js 22+ for the guided installer and Python 3.10+ for the research helper. Python tests need no installed packages. Run:

```bash
npm ci --ignore-scripts
npm test
python -m unittest discover -s tests -v
python scripts/validate.py
python scripts/package.py
```

For Claude plugin changes, also run `claude plugin validate .` if the client is installed. Document the client version used. Authenticated MCP checks are manual; do not add secrets to CI.

Change the shared skill at `skills/model-finder`, not installed copies. Keep the entrypoint concise and put conditional details in its references. Test behavioral changes using synthetic data. For selection changes, cover unknown values and realistic constraint failures as well as happy paths. Do not fuzzy-match benchmark identities or introduce unexplained composite rankings.

If the project-local `.agents/skills/model-finder/` copy exists, refresh it from the canonical directory after a skill change. `scripts/validate.py` checks every file in that copy, including references and scripts, and rejects changed, missing or extra files. It allows LF/CRLF differences in text and ignores Python caches. The local copy is optional in release archives, which ship only `skills/model-finder/`.

When source APIs or client formats change, link the current official documentation in the change and update `docs/setup.md` or the source reference. Keep version values synchronized across package.json, both plugin manifests, the marketplace entry, and the helper. Release archives are generated with `scripts/package.py`; inspect their contents before publishing. Use `npm pack --dry-run` to inspect the separate npx package. No npm publish step is needed for GitHub-based npx installation; the updated files must be pushed to the source repository before remote users can run them.

Describe the problem, observable result, and relevant verification in pull requests. Any proposed paid inference or runtime model switching should define its authorization, data, and budget boundaries explicitly.
