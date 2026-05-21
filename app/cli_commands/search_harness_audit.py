from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.cli_commands.common import lazy_service_attr
from app.db.session import get_session_factory
from app.schemas.search import (
    AuditBundleValidationReceiptRequest,
    RetrievalTrainingRunAuditBundleRequest,
    SearchHarnessReleaseAuditBundleRequest,
)
from app.services.storage import StorageService


def run_search_harness_release_audit_bundle(
    *,
    session_factory_func=get_session_factory,
    storage_service_factory=StorageService,
    create_search_harness_release_audit_bundle_func=None,
) -> None:
    if create_search_harness_release_audit_bundle_func is None:
        create_search_harness_release_audit_bundle_func = lazy_service_attr(
            "app.services.audit_bundles",
            "create_search_harness_release_audit_bundle",
        )
    parser = argparse.ArgumentParser(
        description="Export a signed immutable audit bundle for one search harness release gate."
    )
    parser.add_argument("release_id", help="Search harness release UUID.")
    parser.add_argument("--created-by", default=None, help="Optional bundle creator identifier.")
    args = parser.parse_args()

    session_factory = session_factory_func()
    storage_service = storage_service_factory()
    with session_factory() as session:
        bundle = create_search_harness_release_audit_bundle_func(
            session,
            UUID(args.release_id),
            SearchHarnessReleaseAuditBundleRequest(created_by=args.created_by),
            storage_service=storage_service,
        )
        session.commit()
    print(json.dumps(bundle.model_dump(mode="json")))


def run_retrieval_training_run_audit_bundle(
    *,
    session_factory_func=get_session_factory,
    storage_service_factory=StorageService,
    create_retrieval_training_run_audit_bundle_func=None,
) -> None:
    if create_retrieval_training_run_audit_bundle_func is None:
        create_retrieval_training_run_audit_bundle_func = lazy_service_attr(
            "app.services.audit_bundles",
            "create_retrieval_training_run_audit_bundle",
        )
    parser = argparse.ArgumentParser(
        description="Export a signed immutable audit bundle for one retrieval training run."
    )
    parser.add_argument("training_run_id", help="Retrieval training run UUID.")
    parser.add_argument("--created-by", default=None, help="Optional bundle creator identifier.")
    args = parser.parse_args()

    session_factory = session_factory_func()
    storage_service = storage_service_factory()
    with session_factory() as session:
        bundle = create_retrieval_training_run_audit_bundle_func(
            session,
            UUID(args.training_run_id),
            RetrievalTrainingRunAuditBundleRequest(created_by=args.created_by),
            storage_service=storage_service,
        )
        session.commit()
    print(json.dumps(bundle.model_dump(mode="json")))


def run_audit_bundle_validation_receipt(
    *,
    session_factory_func=get_session_factory,
    storage_service_factory=StorageService,
    create_audit_bundle_validation_receipt_func=None,
) -> None:
    if create_audit_bundle_validation_receipt_func is None:
        create_audit_bundle_validation_receipt_func = lazy_service_attr(
            "app.services.audit_bundles",
            "create_audit_bundle_validation_receipt",
        )
    parser = argparse.ArgumentParser(
        description="Validate a signed audit bundle and export a signed receipt."
    )
    parser.add_argument("bundle_id", help="Audit bundle export UUID.")
    parser.add_argument(
        "--created-by",
        default=None,
        help="Optional receipt creator identifier.",
    )
    args = parser.parse_args()

    session_factory = session_factory_func()
    storage_service = storage_service_factory()
    with session_factory() as session:
        receipt = create_audit_bundle_validation_receipt_func(
            session,
            UUID(args.bundle_id),
            AuditBundleValidationReceiptRequest(created_by=args.created_by),
            storage_service=storage_service,
        )
        session.commit()
    print(json.dumps(receipt.model_dump(mode="json")))
