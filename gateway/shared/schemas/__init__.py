"""Cross-feature shared DTOs: only truly-shared envelopes live here."""

from gateway.shared.schemas.pagination import (
    Page,
    PageParams,
    decode_cursor,
    encode_cursor,
)

__all__ = ["Page", "PageParams", "decode_cursor", "encode_cursor"]
