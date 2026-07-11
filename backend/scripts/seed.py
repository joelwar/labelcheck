from __future__ import annotations

import asyncio
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import seed_submissions  # noqa: E402


async def main() -> None:
    created = await seed_submissions()
    print(f"Created {len(created)} seed submissions.")
    for submission in created:
        print(f"- {submission.id}: {submission.status}")


if __name__ == "__main__":
    asyncio.run(main())
