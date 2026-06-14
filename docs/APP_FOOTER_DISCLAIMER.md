# App Footer Disclaimer

## Recommended visible footer

Use this concise sentence at the bottom of all dataset-aware pages:

> **Charts summarize uploaded sequence records only; they do not represent epidemiological case counts, incidence, or prevalence.**

## Recommended expanded tooltip or help text

> VirSift visualizations are descriptive summaries of the active uploaded
> sequence dataset. They may reflect uneven sequencing and submission practices
> and should not be interpreted as a comprehensive population-level surveillance
> summary.

## Streamlit example

```python
import streamlit as st

st.divider()
st.caption(
    "Charts summarize uploaded sequence records only; "
    "they do not represent epidemiological case counts, incidence, or prevalence."
)
```

## Optional sidebar notice

```python
st.sidebar.info(
    "Sequence-based view: dashboard counts reflect the active uploaded FASTA "
    "dataset, not real-world case counts."
)
```

## Optional hosted-deployment notice

```python
st.caption(
    "Data-processing note: local installations process files on the user's "
    "machine; hosted deployments process uploads within the hosting environment."
)
```
