# VirSift Example and Test Cases

The `cases/` directory contains repository-based FASTA inputs and usage notes
for testing upload, parsing, activation, filtering, visualization, and export.

Expected repository files include:

- `All H3N2_20250918_070704.fasta`
- `HA_test_copy1.fasta`
- `RSV-B_for_filtration.fasta`
- `usecase.md`

Before publishing or redistributing a FASTA file, confirm:

- Its source and provenance
- Whether public redistribution is permitted
- Whether source acknowledgements or accession identifiers must be retained
- Whether it contains sensitive or restricted metadata
- Its expected sequence count, subtype count, segment count, and date range

Do not create a duplicate `examples/` directory unless it serves a clearly
different purpose. VirSift already uses `cases/` for test and demonstration data.

## Mandatory provenance record

Before a public release, complete this table for every FASTA file:

| Filename | Source | Synthetic or accession(s) | Redistribution basis | Created/retrieved | Expected sequences | Maintainer |
|---|---|---|---|---|---:|---|
| `All H3N2_20250918_070704.fasta` | To verify | To verify | To verify | To verify | To verify | To assign |
| `HA_test_copy1.fasta` | To verify | To verify | To verify | To verify | To verify | To assign |
| `RSV-B_for_filtration.fasta` | To verify | To verify | To verify | To verify | To verify | To assign |

> **Release gate:** If a file was obtained from GISAID and public
> redistribution has not been expressly authorized, remove it from the public
> repository and replace it with synthetic or independently redistributable test
> data.

