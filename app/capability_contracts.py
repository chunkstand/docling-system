from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.core.files import repo_root

CAPABILITY_CONTRACT_MAP_SCHEMA_NAME = "capability_contract_map"
CAPABILITY_CONTRACT_SCHEMA_VERSION = "1.0"
DEFAULT_CAPABILITY_CONTRACT_MAP_PATH = Path("docs") / "capability_contract_map.json"
CAPABILITY_FACADES = (
    "run_lifecycle",
    "retrieval",
    "evaluation",
    "semantics",
    "agent_orchestration",
)
WRITE_PREFIXES = (
    "approve_",
    "create_",
    "ingest_",
    "record_",
    "refresh_",
    "reject_",
    "reprocess_",
    "review_",
)
ORCHESTRATION_PREFIXES = (
    "answer_",
    "compare_",
    "evaluate_",
    "execute_",
    "export_",
    "explain_",
    "process_",
    "replay_",
    "run_",
)


@dataclass(frozen=True, slots=True)
class CapabilityContractIssue:
    contract: str
    field: str
    message: str
    relative_path: str | None = None
    lineno: int | None = None
    symbol: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _capability_map_path(project_root: Path, path: str | Path | None = None) -> Path:
    raw_path = Path(path) if path is not None else DEFAULT_CAPABILITY_CONTRACT_MAP_PATH
    return raw_path if raw_path.is_absolute() else project_root / raw_path


def _facade_module_path(project_root: Path, facade_name: str) -> Path:
    return project_root / "app" / "services" / "capabilities" / f"{facade_name}.py"


def _facade_class_prefix(facade_name: str) -> str:
    return "".join(part.capitalize() for part in facade_name.split("_"))


def _annotation(node: ast.AST | None) -> str | None:
    return ast.unparse(node) if node is not None else None


def _method_parameters(node: ast.FunctionDef) -> list[dict[str, object]]:
    parameters: list[dict[str, object]] = []
    positional = [*node.args.posonlyargs, *node.args.args]
    positional_defaults = [None] * (len(positional) - len(node.args.defaults))
    positional_defaults.extend(node.args.defaults)
    kinds = ["positional_only"] * len(node.args.posonlyargs)
    kinds.extend(["positional_or_keyword"] * len(node.args.args))

    for arg, default, kind in zip(positional, positional_defaults, kinds, strict=True):
        if arg.arg == "self":
            continue
        parameters.append(
            {
                "name": arg.arg,
                "kind": kind,
                "annotation": _annotation(arg.annotation),
                "default": _annotation(default),
                "required": default is None,
            }
        )

    if node.args.vararg is not None:
        parameters.append(
            {
                "name": node.args.vararg.arg,
                "kind": "var_positional",
                "annotation": _annotation(node.args.vararg.annotation),
                "default": None,
                "required": False,
            }
        )

    for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True):
        parameters.append(
            {
                "name": arg.arg,
                "kind": "keyword_only",
                "annotation": _annotation(arg.annotation),
                "default": _annotation(default),
                "required": default is None,
            }
        )

    if node.args.kwarg is not None:
        parameters.append(
            {
                "name": node.args.kwarg.arg,
                "kind": "var_keyword",
                "annotation": _annotation(node.args.kwarg.annotation),
                "default": None,
                "required": False,
            }
        )
    return parameters


def _operation_kind(function_name: str) -> str:
    if function_name.startswith(WRITE_PREFIXES):
        return "write"
    if function_name.startswith(ORCHESTRATION_PREFIXES):
        return "orchestration"
    return "read"


def _class_def(tree: ast.Module, class_name: str) -> ast.ClassDef | None:
    return next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        ),
        None,
    )


def _public_methods(class_node: ast.ClassDef | None) -> dict[str, ast.FunctionDef]:
    if class_node is None:
        return {}
    return {
        node.name: node
        for node in class_node.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }


def _owner_imports(tree: ast.Module) -> dict[str, str]:
    owner_imports: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module != "app.services":
            continue
        for alias in node.names:
            local_name = alias.asname or alias.name
            owner_imports[local_name] = f"app.services.{alias.name}"
    return owner_imports


def _exports_instance(tree: ast.Module, facade_name: str, protocol_name: str) -> bool:
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id != facade_name:
                continue
            return _annotation(node.annotation) == protocol_name
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == facade_name:
                    return True
    return False


def _owner_call(
    method_node: ast.FunctionDef | None,
    owner_imports: dict[str, str],
) -> tuple[str | None, str | None]:
    if method_node is None:
        return None, None
    for node in ast.walk(method_node):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        owner_module = owner_imports.get(node.func.value.id)
        if owner_module is not None:
            return owner_module, node.func.attr
    return None, None


def _facade_contract(project_root: Path, facade_name: str) -> dict[str, object]:
    source_path = _facade_module_path(project_root, facade_name)
    tree = ast.parse(source_path.read_text(), filename=str(source_path))
    class_prefix = _facade_class_prefix(facade_name)
    protocol_name = f"{class_prefix}Capability"
    implementation_name = f"Services{class_prefix}Capability"
    protocol_methods = _public_methods(_class_def(tree, protocol_name))
    implementation_methods = _public_methods(_class_def(tree, implementation_name))
    owner_imports = _owner_imports(tree)

    functions = []
    for method_name, protocol_method in sorted(protocol_methods.items()):
        implementation_method = implementation_methods.get(method_name)
        owner_module, owner_symbol = _owner_call(implementation_method, owner_imports)
        functions.append(
            {
                "name": method_name,
                "operation_kind": _operation_kind(method_name),
                "parameters": _method_parameters(protocol_method),
                "returns": _annotation(protocol_method.returns),
                "owner_module": owner_module,
                "owner_symbol": owner_symbol,
                "source_lineno": protocol_method.lineno,
            }
        )

    relative_source = source_path.resolve().relative_to(project_root.resolve()).as_posix()
    return {
        "name": facade_name,
        "module": f"app.services.capabilities.{facade_name}",
        "source": relative_source,
        "protocol": protocol_name,
        "implementation": implementation_name,
        "exported_instance": facade_name,
        "owner_modules": sorted(set(owner_imports.values())),
        "function_count": len(functions),
        "functions": functions,
    }


def build_capability_contract_map(project_root: Path | None = None) -> dict[str, Any]:
    root = project_root or repo_root()
    facades = [_facade_contract(root, facade_name) for facade_name in CAPABILITY_FACADES]
    return {
        "schema_name": CAPABILITY_CONTRACT_MAP_SCHEMA_NAME,
        "schema_version": CAPABILITY_CONTRACT_SCHEMA_VERSION,
        "facade_count": len(facades),
        "function_count": sum(int(facade["function_count"]) for facade in facades),
        "facades": facades,
    }


def write_capability_contract_map(
    path: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> Path:
    root = project_root or repo_root()
    resolved_path = _capability_map_path(root, path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(
        json.dumps(build_capability_contract_map(root), indent=2, sort_keys=True) + "\n"
    )
    return resolved_path


def _validate_facade_contract(
    project_root: Path,
    facade_name: str,
) -> list[CapabilityContractIssue]:
    source_path = _facade_module_path(project_root, facade_name)
    relative_source = source_path.resolve().relative_to(project_root.resolve()).as_posix()
    tree = ast.parse(source_path.read_text(), filename=str(source_path))
    class_prefix = _facade_class_prefix(facade_name)
    protocol_name = f"{class_prefix}Capability"
    implementation_name = f"Services{class_prefix}Capability"
    protocol_class = _class_def(tree, protocol_name)
    implementation_class = _class_def(tree, implementation_name)
    protocol_methods = _public_methods(protocol_class)
    implementation_methods = _public_methods(implementation_class)
    issues: list[CapabilityContractIssue] = []

    if protocol_class is None:
        issues.append(
            CapabilityContractIssue(
                contract="capability_surface_contracts",
                field="protocol",
                relative_path=relative_source,
                symbol=protocol_name,
                message="Capability facade is missing its public Protocol class.",
            )
        )
    if implementation_class is None:
        issues.append(
            CapabilityContractIssue(
                contract="capability_surface_contracts",
                field="implementation",
                relative_path=relative_source,
                symbol=implementation_name,
                message="Capability facade is missing its Services implementation class.",
            )
        )
    if not _exports_instance(tree, facade_name, protocol_name):
        issues.append(
            CapabilityContractIssue(
                contract="capability_surface_contracts",
                field="exported_instance",
                relative_path=relative_source,
                symbol=facade_name,
                message="Capability facade must export an instance annotated with its Protocol.",
            )
        )
    for method_name, protocol_method in protocol_methods.items():
        if protocol_method.returns is None:
            issues.append(
                CapabilityContractIssue(
                    contract="capability_surface_contracts",
                    field="return_annotation",
                    relative_path=relative_source,
                    lineno=protocol_method.lineno,
                    symbol=method_name,
                    message="Capability protocol methods must declare return annotations.",
                )
            )
        for parameter in _method_parameters(protocol_method):
            if parameter["annotation"] is None:
                issues.append(
                    CapabilityContractIssue(
                        contract="capability_surface_contracts",
                        field="parameter_annotation",
                        relative_path=relative_source,
                        lineno=protocol_method.lineno,
                        symbol=f"{method_name}.{parameter['name']}",
                        message="Capability protocol parameters must declare annotations.",
                    )
                )
        if method_name not in implementation_methods:
            issues.append(
                CapabilityContractIssue(
                    contract="capability_surface_contracts",
                    field="implementation_method",
                    relative_path=relative_source,
                    lineno=protocol_method.lineno,
                    symbol=method_name,
                    message="Capability implementation is missing a protocol method.",
                )
            )

    for method_name, implementation_method in implementation_methods.items():
        if method_name not in protocol_methods:
            issues.append(
                CapabilityContractIssue(
                    contract="capability_surface_contracts",
                    field="extra_implementation_method",
                    relative_path=relative_source,
                    lineno=implementation_method.lineno,
                    symbol=method_name,
                    message=(
                        "Capability implementation exposes a public method outside "
                        "the Protocol."
                    ),
                )
            )
    return issues


def validate_capability_contracts(
    project_root: Path | None = None,
    *,
    map_path: str | Path | None = None,
) -> list[CapabilityContractIssue]:
    root = project_root or repo_root()
    issues = [
        issue
        for facade_name in CAPABILITY_FACADES
        for issue in _validate_facade_contract(root, facade_name)
    ]
    resolved_path = _capability_map_path(root, map_path)
    try:
        relative_map_path = resolved_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        relative_map_path = resolved_path.as_posix()
    if not resolved_path.exists():
        issues.append(
            CapabilityContractIssue(
                contract="capability_contract_map",
                field="persisted_map",
                relative_path=relative_map_path,
                message=(
                    "Committed capability contract map is missing; run "
                    "`uv run docling-system-capability-contracts --write-map`."
                ),
            )
        )
        return issues
    if json.loads(resolved_path.read_text()) != build_capability_contract_map(root):
        issues.append(
            CapabilityContractIssue(
                contract="capability_contract_map",
                field="persisted_map",
                relative_path=relative_map_path,
                message=(
                    "Committed capability contract map is stale; run "
                    "`uv run docling-system-capability-contracts --write-map`."
                ),
            )
        )
    return issues


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect service capability facade contracts.")
    parser.add_argument("--write-map", action="store_true")
    parser.add_argument(
        "--map-path",
        default=str(DEFAULT_CAPABILITY_CONTRACT_MAP_PATH),
        help="Path to the persisted capability contract map.",
    )
    args = parser.parse_args(argv)

    if args.write_map:
        path = write_capability_contract_map(args.map_path)
        try:
            display_path = path.relative_to(repo_root()).as_posix()
        except ValueError:
            display_path = path.as_posix()
        print(
            json.dumps(
                {
                    "schema_name": "capability_contract_map_write",
                    "schema_version": CAPABILITY_CONTRACT_SCHEMA_VERSION,
                    "path": display_path,
                },
                sort_keys=True,
            )
        )
        return 0

    payload = build_capability_contract_map()
    issues = validate_capability_contracts()
    payload["valid"] = not issues
    payload["issues"] = [issue.to_dict() for issue in issues]
    print(json.dumps(payload, sort_keys=True))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(run())
