"""MethodDocGenerator: render the discovered method specs as JSON or Markdown."""

from __future__ import annotations

import json

from gateway.base.service import BaseService
from gateway.features.methods.registry import MethodRegistry
from gateway.features.methods.schemas.dtos import MethodList


class MethodDocGenerator(BaseService):
    def __init__(self, registry: MethodRegistry) -> None:
        self._registry = registry

    def as_list(self) -> MethodList:
        return MethodList(data=self._registry.all_specs())

    def as_markdown(self) -> str:
        lines = [
            "# SDK Methods — generic dispatch reference",
            "",
            "Auto-generated from the `claude_ai.methods` classes. Call any method via:",
            "",
            "```",
            "POST /v1/methods/invoke",
            '{ "method": "<name>", "account_id": "<acc>", "params": { ... } }',
            "```",
            "",
        ]
        current_group = None
        for spec in self._registry.all_specs():
            if spec.group != current_group:
                current_group = spec.group
                lines.append(f"## {current_group}")
                lines.append("")
            stream = " · stream" if spec.is_stream else ""
            multipart = " · multipart (not dispatchable)" if spec.is_multipart else ""
            lines.append(f"### {spec.name}{stream}{multipart}")
            lines.append(f"- `{spec.http_method} {spec.endpoint}` → `{spec.result_model}`")
            lines.append(f"- style: `{spec.style.value}`")
            props = spec.param_schema.get("properties", {})
            if props:
                lines.append(f"- params: `{json.dumps(sorted(props), ensure_ascii=False)}`")
            lines.append("")
        return "\n".join(lines)
