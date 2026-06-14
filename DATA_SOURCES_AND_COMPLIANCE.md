# Data Sources and Compliance

This document explains how VirSift relates to common sequence-data sources and
how users should interpret data processed by the application.

## 1. User-supplied data

VirSift does not provide an embedded epidemiological database. Users upload
FASTA files or supported archives and activate a selected or merged dataset.

All calculations are therefore conditional on:

- The records selected by the user
- The completeness and quality of their metadata
- The filters and sampling strategies applied
- The active file scope
- The current software version and configuration

## 2. Epidemiological interpretation

Sequence counts are not case counts.

A rise in uploaded or submitted sequences may result from increased sequencing,
targeted outbreak investigation, retrospective deposition, or changes in
laboratory capacity. It must not automatically be interpreted as an increase in
disease incidence.

Recommended wording:

> VirSift visualizations describe the uploaded sequence dataset and should not
> be interpreted as estimates of epidemiological incidence, prevalence, or
> population-level burden.

## 3. GISAID data

VirSift supports common GISAID influenza FASTA header patterns. GISAID data use
is governed by the applicable GISAID Database Access Agreement and related
policies.

VirSift:

- Does not create a GISAID account
- Does not grant access to GISAID data
- Does not replace GISAID acknowledgment requirements
- Does not authorize public redistribution
- Does not determine whether a particular record may be shared

Users must obtain data through appropriate authorized access and comply with
the terms that apply to those data.

### Repository rule

Do not commit or publish GISAID-derived sequence records unless redistribution
has been expressly authorized. Replace uncertain files with synthetic examples
or independently redistributable public records.

## 4. NCBI and GenBank data

NCBI molecular databases are designed to encourage scientific access and NCBI
generally places no restrictions on use or distribution of the molecular data.
However, NCBI notes that submitters or countries of origin may assert
intellectual-property rights in particular records.

Recommended practice:

- Preserve accession identifiers
- Record retrieval dates
- Document the database and query used
- Retain source metadata when permitted
- Review record-level notices
- Cite the relevant database and original studies

## 5. Example datasets

Every file under `cases/` should have a provenance record containing:

| Field | Required information |
|---|---|
| Filename | Exact repository filename |
| Purpose | Parser, filter, analytics, or timeline test |
| Source | Synthetic, GenBank accession set, or other source |
| Redistribution status | Why the file may be publicly shared |
| Retrieval or creation date | ISO date |
| Expected sequence count | Parser validation value |
| Expected metadata summary | Subtypes, segments, hosts, date range |
| Transformations | Trimming, anonymization, header changes, or subsampling |
| Maintainer | Person responsible for verification |

## 6. Privacy and hosted deployments

A browser interface does not necessarily mean processing occurs only on the
local computer.

- Local execution: files are processed on the user's machine.
- Hosted execution: files are processed in the configured hosting environment.

Do not upload restricted, confidential, identifiable, or sensitive surveillance
data to a hosted deployment without an appropriate security and governance
review.

## 7. User responsibility

Users are responsible for:

- Confirming permission to access and process their data
- Complying with database agreements and institutional rules
- Validating filters and sampling strategies
- Interpreting outputs in context
- Retaining provenance, acknowledgments, and accession information
- Avoiding claims that sequence submissions equal epidemiological incidence
