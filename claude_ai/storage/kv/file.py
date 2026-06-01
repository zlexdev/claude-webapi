"""FileStorage: JSON-file state store with aiofiles + asyncio.to_thread fallback."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

try:
    import aiofiles
except ImportError:
    aiofiles = None  # type: ignore[assignment]

from claude_ai.storage.kv.base import BaseStorage, StorageNamespace


class FileStorage(BaseStorage):
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = asyncio.Lock()

    async def _read(self) -> dict[str, dict[str, Any]]:
        if not self._path.exists():
            return {}
        if aiofiles is not None:
            async with aiofiles.open(self._path, "r", encoding="utf-8") as f:
                text = await f.read()
        else:
            text = await asyncio.to_thread(self._path.read_text, encoding="utf-8")
        return json.loads(text) if text.strip() else {}

    async def _write(self, data: dict[str, dict[str, Any]]) -> None:
        text = json.dumps(data, ensure_ascii=False, indent=2)
        if aiofiles is not None:
            async with aiofiles.open(self._path, "w", encoding="utf-8") as f:
                await f.write(text)
        else:
            await asyncio.to_thread(self._path.write_text, text, encoding="utf-8")

    async def get(self, namespace: StorageNamespace | str, key: str) -> Any | None:
        async with self._lock:
            data = await self._read()
            return data.get(str(namespace), {}).get(key)

    async def set(
        self, namespace: StorageNamespace | str, key: str, value: Any
    ) -> None:
        async with self._lock:
            data = await self._read()
            data.setdefault(str(namespace), {})[key] = value
            await self._write(data)

    async def delete(self, namespace: StorageNamespace | str, key: str) -> None:
        async with self._lock:
            data = await self._read()
            if data.get(str(namespace), {}).pop(key, None) is not None:
                await self._write(data)

    async def items(self, namespace: StorageNamespace | str) -> dict[str, Any]:
        async with self._lock:
            data = await self._read()
            return dict(data.get(str(namespace), {}))
