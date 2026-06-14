# VirSift Public Upload Package - Treadmill Check

This audit was performed before rebuilding the public GitHub merge package.

## Automated results

- Required files missing: **0**
- Broken relative Markdown/HTML links: **0**
- PNG files successfully opened: **21**
- Gallery images verified: **16**
- YAML/CFF files parsed: **4**
- ZIP integrity: checked after packaging

## Corrections applied

- Replaced the architecture diagram with a fitted version that keeps every label inside its box.
- Replaced the unreadable Molecular Timeline screenshot with a readable four-panel full-resolution overview.
- Added an Export screenshot and renumbered Documentation as screenshot 08.
- Rebuilt all README previews and full-resolution screenshot targets.
- Updated translation-key references from 813 to 817.
- Removed unsupported TAR and zip.tar input claims.
- Removed the broken demo-GIF placeholder and added the live Streamlit application link.
- Updated CITATION.cff so the project URL points to https://virsift.streamlit.app/ while repository-code remains GitHub.
- Removed self-contained-package links to case FASTA files that are deliberately not redistributed here.
- Updated the v1.0.0 release checklist to match the 817-key catalogue and current supported uploads.

## Screenshot dimensions

| Type | File | Width | Height | Size (bytes) |
|---|---|---:|---:|---:|
| full | `01-landing.png` | 794 | 2048 | 495844 |
| full | `02-observatory.png` | 3284 | 3019 | 1206016 |
| full | `03-workspace.png` | 3084 | 2253 | 905582 |
| full | `04-sequence-refinery.png` | 3284 | 2021 | 735818 |
| full | `05-molecular-timeline.png` | 3284 | 2071 | 811059 |
| full | `06-analytics.png` | 3284 | 2021 | 390378 |
| full | `07-export.png` | 3284 | 3019 | 934688 |
| full | `08-documentation.png` | 3084 | 4381 | 2089641 |
| preview | `01-landing.png` | 1200 | 760 | 237670 |
| preview | `02-observatory.png` | 1200 | 760 | 209278 |
| preview | `03-workspace.png` | 1200 | 760 | 166864 |
| preview | `04-sequence-refinery.png` | 1200 | 760 | 175153 |
| preview | `05-molecular-timeline.png` | 1200 | 760 | 107987 |
| preview | `06-analytics.png` | 1200 | 760 | 94153 |
| preview | `07-export.png` | 1200 | 760 | 137594 |
| preview | `08-documentation.png` | 1200 | 760 | 197943 |

## Stale-reference scan

| Check | Present after correction? |
|---|---:|
| 813 translation keys | No |
| TAR upload claim | No |
| zip.tar upload claim | No |
| broken demo GIF reference | No |
| misspelled public URL | No |

## Manual release gates

- The GitHub release date and Zenodo DOI remain pending until v1.0.0 is published.
- The public redistribution status of every FASTA file in the live repository's cases/ directory must still be verified.
- Screenshots retain some legacy Vir-Seq-Sift interface wording; recapture them only if the final public interface has changed.
- This is a merge package. It does not replace app.py, pages/, utils/, requirements.txt, or the existing live cases/ files.
