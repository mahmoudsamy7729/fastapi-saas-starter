from typing import Any, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select


async def paginate(
    db: AsyncSession,
    query: Select,
    *,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    # total after filters
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # page
    page_query = query.limit(limit).offset(offset)
    items = (await db.execute(page_query)).scalars().all()

    has_next = (offset + limit) < total
    next_offset = (offset + limit) if has_next else None
    prev_offset = (offset - limit) if (offset - limit) >= 0 else None

    return {
        "data": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_next": has_next,
        "next_offset": next_offset,
        "prev_offset": prev_offset,
    }