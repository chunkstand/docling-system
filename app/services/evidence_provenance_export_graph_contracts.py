from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.evidence_provenance import (
    add_prov_activity as _prov_activity,
)
from app.services.evidence_provenance import (
    add_prov_entity as _prov_entity,
)
from app.services.evidence_provenance import (
    add_prov_relation as _prov_relation,
)

JsonDict = dict[str, Any]


@dataclass(frozen=True)
class ProvenanceGraphContext:
    manifest: JsonDict
    trace: JsonDict
    report_trace: JsonDict
    retrieval_evaluation: JsonDict
    context_pack_audit: JsonDict
    release_readiness_db_gate: JsonDict
    release_readiness_db_gate_record: JsonDict
    release_readiness_db_gate_entity_id: str | None
    manifest_entity_id: str | None
    trace_entity_id: str | None
    harness_activity_id: str | None
    verification_activity_id: str | None


@dataclass
class ProvenanceGraphState:
    entities: dict[str, JsonDict] = field(default_factory=dict)
    activities: dict[str, JsonDict] = field(default_factory=dict)
    agents: dict[str, JsonDict] = field(default_factory=dict)
    was_generated_by: dict[str, JsonDict] = field(default_factory=dict)
    used: dict[str, JsonDict] = field(default_factory=dict)
    was_derived_from: dict[str, JsonDict] = field(default_factory=dict)
    was_associated_with: dict[str, JsonDict] = field(default_factory=dict)
    was_attributed_to: dict[str, JsonDict] = field(default_factory=dict)

    @classmethod
    def new(cls) -> ProvenanceGraphState:
        return cls(
            agents={
                "docling:agent/docling-system": {
                    "prov:type": "prov:SoftwareAgent",
                    "prov:label": "Docling System",
                },
                "docling:agent/technical-report-gate": {
                    "prov:type": "prov:SoftwareAgent",
                    "prov:label": "Technical report verification gate",
                },
                "docling:agent/context-pack-gate": {
                    "prov:type": "prov:SoftwareAgent",
                    "prov:label": "Document generation context-pack gate",
                },
            }
        )

    def add_entity(
        self, entity_id: str | None, *, label: str, entity_type: str, **attrs: Any
    ) -> None:
        _prov_entity(self.entities, entity_id, label=label, entity_type=entity_type, **attrs)

    def add_activity(
        self,
        activity_id: str | None,
        *,
        label: str,
        activity_type: str,
        started_at: Any = None,
        ended_at: Any = None,
        **attrs: Any,
    ) -> None:
        _prov_activity(
            self.activities,
            activity_id,
            label=label,
            activity_type=activity_type,
            started_at=started_at,
            ended_at=ended_at,
            **attrs,
        )

    def add_generated(self, *, entity: str | None, activity: str | None, **attrs: Any) -> None:
        self._add_relation(
            self.was_generated_by,
            "was-generated-by",
            **{"prov:entity": entity, "prov:activity": activity, **attrs},
        )

    def add_used(self, *, activity: str | None, entity: str | None, **attrs: Any) -> None:
        self._add_relation(
            self.used,
            "used",
            **{"prov:activity": activity, "prov:entity": entity, **attrs},
        )

    def add_derived(
        self,
        *,
        generated_entity: str | None,
        used_entity: str | None,
        **attrs: Any,
    ) -> None:
        self._add_relation(
            self.was_derived_from,
            "was-derived-from",
            **{
                "prov:generatedEntity": generated_entity,
                "prov:usedEntity": used_entity,
                **attrs,
            },
        )

    def add_associated(self, *, activity: str | None, agent: str | None, **attrs: Any) -> None:
        self._add_relation(
            self.was_associated_with,
            "was-associated-with",
            **{"prov:activity": activity, "prov:agent": agent, **attrs},
        )

    def add_attributed(self, *, entity: str | None, agent: str | None, **attrs: Any) -> None:
        self._add_relation(
            self.was_attributed_to,
            "was-attributed-to",
            **{"prov:entity": entity, "prov:agent": agent, **attrs},
        )

    def _add_relation(
        self, relations: dict[str, JsonDict], relation_prefix: str, **attrs: Any
    ) -> None:
        _prov_relation(relations, relation_prefix, sequence=len(relations) + 1, **attrs)
