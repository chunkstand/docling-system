from __future__ import annotations

from app.hotspot_prevention import POLICY_SCHEMA_NAME, build_hotspot_policy


def _diff_for(path: str, added_lines: list[str], *, deleted_lines: list[str] | None = None) -> str:
    deleted = deleted_lines or []
    lines = [
        f"diff --git a/{path} b/{path}",
        f"--- a/{path}",
        f"+++ b/{path}",
        f"@@ -1,{max(len(deleted), 1)} +1,{max(len(added_lines), 1)} @@",
    ]
    lines.extend(f"-{line}" for line in deleted)
    lines.extend(f"+{line}" for line in added_lines)
    return "\n".join(lines) + "\n"


def _policy_for(path: str, *, exceptions: list[dict] | None = None):
    return build_hotspot_policy(
        {
            "schema_name": POLICY_SCHEMA_NAME,
            "schema_version": "1.0",
            "known_hotspots": {
                path: {
                    "target_role": "compatibility facade",
                    "preferred_owner_modules": ["app/owner/"],
                    "block_new": [
                        "orm_class",
                        "private_helper",
                        "command_implementation",
                        "executor_implementation",
                        "ranking_logic",
                        "broad_new_test_group",
                        "broad_helper",
                        "artifact_assembly",
                    ],
                    "allow": [
                        "import_forwarder",
                        "alias_forwarder",
                        "explicit_forwarding_function",
                        "parser_registration",
                        "compatibility_assertion",
                        "deletion",
                    ],
                    "exceptions": exceptions or [],
                }
            },
        }
    )
