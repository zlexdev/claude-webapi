"""LimitState: per-session rate-limit utilization tracking (5h/7d windows)."""

from __future__ import annotations

from dataclasses import dataclass, field

from claude_ai.models.streaming import MessageLimitInfo


@dataclass(slots=True)
class LimitState:
    utilization_5h: float = 0.0
    utilization_7d: float = 0.0
    resets_5h_at: int | None = None
    resets_7d_at: int | None = None
    representative_claim: str | None = None
    overage_in_use: bool = False
    raw: dict[str, float] = field(default_factory=dict)

    def update(self, info: MessageLimitInfo) -> None:
        windows = info.windows or {}
        h5 = windows.get("5h")
        d7 = windows.get("7d")
        if h5 is not None:
            self.utilization_5h = h5.utilization
            self.resets_5h_at = h5.resets_at
            self.raw["5h"] = h5.utilization
        if d7 is not None:
            self.utilization_7d = d7.utilization
            self.resets_7d_at = d7.resets_at
            self.raw["7d"] = d7.utilization
        self.representative_claim = info.representativeClaim
        self.overage_in_use = info.overageInUse

    def score(self) -> float:
        return max(self.utilization_5h, self.utilization_7d)
