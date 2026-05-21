# Ontology Contract Report

- Contract: `portable_upper_ontology`
- Version: `portable-upper-ontology-v1`
- Upper ontology version: `portable-upper-ontology-v1`
- Valid: `True`
- Strict mode: `True`

## Layers

| Layer | Kind | Version | Legacy | Entities | Categories | Concepts | Relations |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| portable_upper_core | upper_ontology | portable-upper-ontology-v1 | yes | 3 | 0 | 0 | 4 |
| docling_application | application_ontology | docling-application-ontology-v1 | no | 11 | 0 | 0 | 4 |
| domain_overlay_baseline | domain_overlay | domain-overlay-baseline-v1 | no | 1 | 0 | 0 | 2 |
| report_semantics_baseline | report_semantics | report-semantics-baseline-v1 | no | 0 | 0 | 0 | 7 |
| evaluation_coverage_baseline | evaluation_coverage | evaluation-coverage-baseline-v1 | no | 4 | 0 | 0 | 3 |

## Slices

| Slice | Status | Layers | Entities | Relations |
| --- | --- | --- | ---: | ---: |
| core | active | portable_upper_core | 3 | 4 |
| application_semantics | active | portable_upper_core, docling_application | 12 | 4 |
| domain_overlays | active | portable_upper_core, domain_overlay_baseline | 3 | 2 |
| report_semantics | active | portable_upper_core, docling_application, report_semantics_baseline | 10 | 7 |
| evaluation_coverage | active | evaluation_coverage_baseline | 4 | 3 |

## Competency Families

| Family | Status | Slices |
| --- | --- | --- |
| claim_support | active | application_semantics, report_semantics, evaluation_coverage |
| measurement_or_unit | active | application_semantics, report_semantics, evaluation_coverage |
| actor_or_obligation | active | application_semantics, report_semantics, evaluation_coverage |
| document_or_source_linkage | active | core, application_semantics, domain_overlays, report_semantics, evaluation_coverage |

## Legacy Views

| View | Path | Exists | In Sync | Entities | Categories | Concepts | Relations |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| upper_ontology_yaml | `config/upper_ontology.yaml` | True | True | 3 | 0 | 0 | 4 |
| semantic_registry_yaml | `config/semantic_registry.yaml` | True | True | 3 | 0 | 0 | 4 |

## Semantic Evaluation Corpus

- Path: `docs/semantic_evaluation_corpus.yaml`
- Exists: `True`
- Corpus name: `semantic_foundation_ontology_contract`
- Document count: `0`
- Query count: `0`
- Ontology slice expectation count: `5`
- Ontology competency family expectation count: `4`
- Ontology competency question count: `8`
