import re, uuid, csv
from typing import Any, Dict, Optional
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.admin.utils import build_enum_map_from_python




EXPORT_DIR = Path("storage/exports")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


class UnsafeSQL(Exception):
    pass


class AIUtils:
    ENUM_MAP = build_enum_map_from_python()


    _BLOCKED_KEYWORDS = {
        "insert", "update", "delete", "drop", "alter", "create", "truncate",
        "grant", "revoke", "comment", "vacuum", "analyze", "refresh",
        "call", "do", "execute", "copy", "lock", "reindex",
    }

    @staticmethod
    def _normalize_sql(sql: str) -> str:
        sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
        sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
        return sql.strip()
    
    @staticmethod
    def _normalize_enum_literals(sql: str) -> str:  #type: ignore
        def repl(m: re.Match) -> str:
            val = m.group(1)
            key = val.lower()
            if key in AIUtils.ENUM_MAP:
                return f"'{AIUtils.ENUM_MAP[key]}'"
            return f"'{val}'"
        
        return re.sub(r"'([^']+)'", repl, sql)
    
    
    @staticmethod
    def _ensure_readonly(sql: str) -> str:
        if not sql:
            raise UnsafeSQL("Empty SQL")

        lower = sql.lower().strip()

        if not (lower.startswith("select") or lower.startswith("with")):
            raise UnsafeSQL("Only SELECT queries are allowed")

        tokens = set(re.findall(r"[a-zA-Z_]+", lower))
        if tokens.intersection(AIUtils._BLOCKED_KEYWORDS):
            raise UnsafeSQL(f"Blocked keyword(s): {sorted(tokens.intersection(AIUtils._BLOCKED_KEYWORDS))}")

        return sql

    @staticmethod
    def _apply_default_limit(sql: str, default_limit: int) -> str:
        if re.search(r"\blimit\b", sql, flags=re.IGNORECASE):
            return sql

        return f"{sql}\nLIMIT {int(default_limit)}"
    


    @staticmethod
    async def _export_csv(db: AsyncSession, sql: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        file_id = str(uuid.uuid4())
        print(f"Exporting CSV to file_id: {file_id}")
        file_path = EXPORT_DIR / f"{file_id}.csv"
        print(f"Export file path: {file_path}")

        # stream rows without loading all
        stream_result = await db.stream(text(sql), params or {})
        columns = list(stream_result.keys())

        row_count = 0
        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(columns)

            async for row in stream_result:
                writer.writerow(["" if v is None else str(v) for v in row])
                row_count += 1

        return {
            "row_count": row_count,
            "columns": columns,
            "export": {
                "type": "csv",
                "file_id": file_id,
                "file_name": f"{file_id}.csv",
                "download_url": f"/ai/exports/{file_id}",
            },
            "truncated_in_ai": True,  
        }
