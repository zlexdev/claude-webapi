"""FileCookieStorage: JSON-file cookie storage with aiofiles + asyncio.to_thread fallback."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

try:
    import aiofiles
except ImportError:
    aiofiles = None  # type: ignore[assignment]

from claude_ai.storage.cookies.base import BaseCookieStorage


class FileCookieStorage(BaseCookieStorage):
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = asyncio.Lock()

    async def _read(self) -> dict[str, dict[str, str]]:
        if not self._path.exists():
            return {}
        if aiofiles is not None:
            async with aiofiles.open(self._path, "r", encoding="utf-8") as f:
                text = await f.read()
        else:
            text = await asyncio.to_thread(self._path.read_text, encoding="utf-8")
        return json.loads(text) if text.strip() else {}

    async def _write(self, data: dict[str, dict[str, str]]) -> None:
        text = json.dumps(data, ensure_ascii=False, indent=2)
        if aiofiles is not None:
            async with aiofiles.open(self._path, "w", encoding="utf-8") as f:
                await f.write(text)
        else:
            await asyncio.to_thread(self._path.write_text, text, encoding="utf-8")

    async def load(self, account_id: str) -> dict[str, str]:
        async with self._lock:
            data = await self._read()
            return dict(data.get(account_id, {}))

    async def save(self, account_id: str, cookies: dict[str, str]) -> None:
        async with self._lock:
            data = await self._read()
            data[account_id] = dict(cookies)
            await self._write(data)

    async def update(self, account_id: str, cookies: dict[str, str]) -> None:
        async with self._lock:
            data = await self._read()
            entry = data.setdefault(account_id, {})
            entry.update(cookies)
            await self._write(data)

    async def delete(self, account_id: str) -> None:
        async with self._lock:
            data = await self._read()
            if data.pop(account_id, None) is not None:
                await self._write(data)

    async def list_accounts(self) -> list[str]:
        async with self._lock:
            data = await self._read()
            return list(data.keys())

    @classmethod
    async def from_netscape(
        cls, path: str | Path, account_id: str
    ) -> "FileCookieStorage":
        cookies: dict[str, str] = {}
        if aiofiles is not None:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                text = await f.read()
        else:
            text = await asyncio.to_thread(Path(path).read_text, encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                cookies[parts[5]] = parts[6]
        store = cls(path=Path(path).with_suffix(".cookies.json"))
        await store.save(account_id, cookies)
        return store
