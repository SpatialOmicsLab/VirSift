# Contributing to VirSift

Thank you for helping improve VirSift.

All contributors must follow the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Contributions may include bug fixes,
documentation, tests, translation updates, accessibility improvements,
visualization enhancements, and new reproducible surveillance workflows.

## Before You Begin

- Search existing issues and pull requests before opening a new one.
- Use only public, synthetic, or redistribution-safe FASTA examples.
- Never post restricted GISAID data, personal information, credentials,
  private accession lists, or sensitive surveillance metadata in an issue.
- Keep changes focused. Large architectural changes should begin with an issue.

## Local Development

```bash
git clone https://github.com/SpatialOmicsLab/virsift.git
cd virsift

python -m venv .venv
```

Activate the environment:

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

### macOS or Linux

```bash
source .venv/bin/activate
```

Install dependencies and launch the app:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

## Branches and Commits

Create a focused branch:

```bash
git checkout -b fix/clear-description
# or
git checkout -b feature/clear-description
```

Use concise commit messages, for example:

```text
Fix MD5 deduplication scope handling
Add French labels for export controls
Document RSV-B filtering example
```

## Coding Guidelines

- Keep processing logic separate from Streamlit presentation where practical.
- Avoid hardcoded interface strings. Use the project translation helper,
  such as `T("translation_key")`.
- Preserve the distinction between the immutable original dataset and the
  mutable current dataset.
- Avoid silent data loss. Filtering, sampling, and export actions should be
  inspectable and, where applicable, recorded in the session log.
- Add comments only where they clarify non-obvious scientific or technical logic.
- Do not commit secrets, tokens, private URLs, or local environment files.

## Translation Updates

Translation files are stored under:

```text
assets/translations/
├── ar.json
├── en.json
├── es.json
├── fr.json
├── ru.json
└── zh.json
```

When adding a user-facing string:

1. Add the English key and text.
2. Add the same key to the other language files when translations are available.
3. Confirm that English fallback still works for any untranslated entry.
4. Check Arabic layout and text direction where the change affects presentation.
5. Keep placeholders and formatting tokens identical across languages.

## Tests and Formatting

Use a synthetic, authorized, or independently redistributable FASTA file for manual testing. Do not commit or attach restricted GISAID records.


Before opening a pull request:

```bash
black --check .
pytest
```

If the repository does not yet contain automated tests for the affected area,
describe the manual verification steps in the pull request.

## Documentation and Screenshots

Update `README.md`, in-app documentation, use cases, and screenshots whenever a
change affects behavior visible to users. Screenshots must not expose restricted
sequence data or private metadata.

## Questions, Suggestions, and Communication

For general questions, improvement ideas, or scientific workflow suggestions:

- Open a GitHub issue for public, trackable discussions.
- Use the feature-request template for proposed enhancements.
- Email **Ayanfeoluwa Alabetutu** at
  [ayanfe4luv@gmail.com](mailto:ayanfe4luv@gmail.com) when the matter should not
  be discussed publicly.

Do not send restricted GISAID sequences, credentials, personal information, or
sensitive surveillance metadata through a public issue. Contact the maintainer
privately first when a suggestion depends on non-public material.

## Pull Requests

A pull request should:

- Explain the problem and the proposed solution.
- Reference the related issue when one exists.
- State how the change was tested.
- Include screenshots for visible interface changes.
- Update translation keys, tests, and documentation as applicable.
- Remain limited to one coherent change.

Submission of a contribution does not automatically confer authorship on a
software paper or publication. Publication credit should follow the contribution
and authorship policies agreed by the project maintainers.
