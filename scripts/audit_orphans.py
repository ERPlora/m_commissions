"""
audit_orphans.py — Commissions module orphan staff_id audit.

Lists CommissionTransaction rows whose staff_id has no corresponding StaffMember.
Run this before adding a future hard FK constraint on staff_id.

Note: commissions already uses a nullable FK (staff_staffmember.id SET NULL),
so this script finds rows where staff_id is NOT NULL but the StaffMember is gone.

Usage:
    python -m commissions.scripts.audit_orphans --hub-id <uuid>

Requires DATABASE_URL environment variable.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


async def audit_orphans(hub_id: uuid.UUID | None = None) -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    engine = create_async_engine(db_url)

    async with AsyncSession(engine) as session:
        stmt = text("""
            SELECT
                ar.id,
                ar.hub_id,
                ar.staff_id,
                ar.staff_name,
                ar.transaction_date
            FROM commissions_transaction ar
            WHERE NOT ar.is_deleted
              AND ar.staff_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM staff_staffmember sm
                  WHERE sm.id = ar.staff_id
                    AND NOT sm.is_deleted
              )
            """ + ("AND ar.hub_id = :hub_id" if hub_id else "") + """
            ORDER BY ar.transaction_date DESC
        """)

        params = {"hub_id": hub_id} if hub_id else {}
        result = await session.execute(stmt, params)
        rows = result.fetchall()

    await engine.dispose()

    if not rows:
        print("No orphan commission transactions found.")
        return

    print(f"Found {len(rows)} orphan commission transaction(s):")
    print(f"{'ID':<38} {'Hub':<38} {'staff_id':<38} {'Name':<30} {'Transaction Date'}")
    print("-" * 160)
    for row in rows:
        print(
            f"{row.id!s:<38} {row.hub_id!s:<38} {row.staff_id!s:<38} "
            f"{row.staff_name:<30} {row.transaction_date}"
        )


if __name__ == "__main__":
    _hub_id: uuid.UUID | None = None
    if "--hub-id" in sys.argv:
        idx = sys.argv.index("--hub-id")
        _hub_id = uuid.UUID(sys.argv[idx + 1])

    asyncio.run(audit_orphans(_hub_id))
