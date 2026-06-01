"""GetModelConfig: per-model configuration available to an org."""

from dataclasses import dataclass
from typing import Any

from claude_ai.methods.base import BaseMethod
from claude_ai.models.organization import ModelConfig


@dataclass(slots=True)
class GetModelConfigParams:
    org_uuid: str
    model_id: str


class GetModelConfig(BaseMethod[GetModelConfigParams, ModelConfig]):
    __endpoint__ = "/api/organizations/{org_uuid}/model_configs/{model_id}"
    __http_method__ = "GET"
    __model__ = ModelConfig

    def build_params(self, params: GetModelConfigParams) -> dict[str, Any]:
        return {
            "path": {"org_uuid": params.org_uuid, "model_id": params.model_id},
        }
