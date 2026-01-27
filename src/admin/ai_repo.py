from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.admin.ai_utils import AIUtils


ai_utils = AIUtils()


class ai_repo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db


    async def get_view_columns(self, view_name: str):
        query = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :view_name
            ORDER BY ordinal_position;
        """)
        result = await self.db.execute(query, {"view_name": view_name})
        return result.scalars().all()
    
    
    async def run_ai_sql(
        self,
        sql: str,
        mode: str,
        params: Optional[Dict[str, Any]] = None,
        *,
        default_limit: int = 200,
        timeout_ms: int = 10_000,
    ) :

        raw = sql
        print (f"Raw AI SQL:\n{raw}")
        sql = AIUtils._normalize_enum_literals(raw)
        sql = AIUtils._normalize_sql(sql)
        sql = AIUtils._ensure_readonly(sql)
        if mode == "preview":
            sql = AIUtils._apply_default_limit(sql, default_limit)
        print (f"Normalized AI SQL:\n{sql}")

        # statement timeout per query (Postgres)
        # must be set inside transaction/session
        await self.db.execute(text(f"SET LOCAL statement_timeout = {int(timeout_ms)}"))
        result = await self.db.execute(text(sql), params or {})
        rows = result.fetchall()
        columns = list(result.keys())
        # Convert to JSON-friendly structure
        data_rows: List[Dict[str, Any]] = [dict(zip(columns, row)) for row in rows]
        print(f"Executed AI SQL:\n{sql}\nRows fetched: {data_rows}")
        print(f"Mode: {mode}")

        if mode == "count":
            return {"row_count": data_rows}
        
        if mode == "preview":
            return {
                "columns": columns,
                "rows": data_rows,
                "row_count": len(data_rows),
            }
        
        if mode == "csv":
            # use data_rows to generate CSV and return link/id
            return await AIUtils._export_csv(self.db, sql, params=params)


    

