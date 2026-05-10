from __future__ import annotations


def lazy_service_attr(module_path: str, name: str):
    module = __import__(module_path, fromlist=[name])
    return getattr(module, name)
