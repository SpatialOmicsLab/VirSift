# VirSift Data and Interpretation Disclaimer

## Sequence data are not case counts

VirSift analyzes sequence records supplied by the user. Counts, curves, charts,
timelines, dashboards, and summaries produced by the application describe only
the records in the active dataset.

They do not measure or estimate:

- Epidemiological case counts
- Incidence or prevalence
- Transmission rates
- Disease burden
- Population immunity
- Population-level representativeness

The uploaded dataset may reflect uneven sequencing, outbreak investigations,
laboratory capacity, submission practices, incomplete metadata, and delays in
data collection or deposition.

Use the phrase:

> VirSift outputs are descriptive summaries of the uploaded sequence dataset,
> not comprehensive epidemiological summaries.

Avoid describing the output as a "fair representation" of a population unless
representativeness has been established through an appropriate sampling design.

## GISAID

VirSift can parse supported GISAID-style influenza FASTA headers. It does not
provide GISAID access, authorize reuse, or supersede GISAID's Database Access
Agreement.

Users are responsible for:

- Accessing GISAID through authorized credentials
- Following applicable acknowledgment and citation requirements
- Complying with use and redistribution restrictions
- Protecting any restricted or sensitive associated metadata

The public software repository should not include GISAID-derived records unless
their redistribution is expressly authorized. Repository maintainers should
verify every bundled FASTA file before publication.

## NCBI and GenBank

VirSift can parse NCBI/GenBank-style records. NCBI generally places no
restrictions on use or distribution of molecular data, but record submitters or
countries of origin may assert patent, copyright, or other rights. Users should
preserve accession numbers and provenance and review any applicable notices.

## Local and hosted processing

When VirSift is run locally, uploaded files are processed on the user's machine.
In a hosted deployment, uploaded files are processed within the hosting
environment. Users should not submit restricted, confidential, or sensitive
datasets to a hosted instance without confirming that its security and
data-handling arrangements are suitable.

## No warranty

VirSift is provided under the MIT License without warranty. Users remain
responsible for validating the software, interpreting outputs, and confirming
that their use of sequence data complies with applicable agreements, policies,
laws, and institutional requirements.
