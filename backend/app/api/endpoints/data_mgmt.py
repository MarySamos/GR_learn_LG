"""Data Management API Endpoints.

提供数据查看、分页、导出等接口
"""
import io
import traceback
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import require_analyst
from app.core.database import engine, get_db
from app.db.models import User
from app.schemas.data_mgmt import DataPage, TableInfo
from app.services.log_service import log_service

router = APIRouter()

# Supported table names
_SUPPORTED_TABLES = {"marketing_data"}

# Supported encodings for CSV import
_CSV_ENCODINGS = ["utf-8", "gbk", "latin1"]

# Pagination defaults
_PAGE_DEFAULT = 1
_PAGE_SIZE_DEFAULT = 50
_PAGE_SIZE_MIN = 10
_PAGE_SIZE_MAX = 200

# Target table for import/export
_TARGET_TABLE = "marketing_data"


@router.get("/tables", response_model=List[TableInfo])
async def get_tables():
    """获取所有数据表信息"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM marketing_data"))
            row_count = result.fetchone()[0]

            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'marketing_data'
                ORDER BY ordinal_position
            """))
            columns = [row[0] for row in result.fetchall()]

        return [TableInfo(name="marketing_data", row_count=row_count, columns=columns)]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/table/{table_name}", response_model=DataPage)
async def get_table_data(
    table_name: str,
    page: int = Query(_PAGE_DEFAULT, ge=1),
    page_size: int = Query(_PAGE_SIZE_DEFAULT, ge=_PAGE_SIZE_MIN, le=_PAGE_SIZE_MAX),
):
    """分页获取表数据"""
    if table_name not in _SUPPORTED_TABLES:
        raise HTTPException(status_code=404, detail="Table not found")

    try:
        offset = (page - 1) * page_size

        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            total = result.fetchone()[0]

            result = conn.execute(text(f"""
                SELECT * FROM {table_name}
                ORDER BY id
                LIMIT {page_size} OFFSET {offset}
            """))
            columns = list(result.keys())
            rows = result.fetchall()

            data = [_row_to_dict(row, columns) for row in rows]

        total_pages = (total + page_size - 1) // page_size

        return DataPage(
            data=data,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            columns=columns,
        )

    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="获取表数据失败")


def _row_to_dict(row, columns: List[str]) -> dict:
    """将数据库行转换为字典，处理特殊类型"""
    row_dict = {}
    for i, col in enumerate(columns):
        val = row[i]
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        row_dict[col] = val
    return row_dict


@router.get("/export/{table_name}")
async def export_table(table_name: str):
    """导出表数据为 CSV"""
    if table_name not in _SUPPORTED_TABLES:
        raise HTTPException(status_code=404, detail="Table not found")

    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", engine)

        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)

        return StreamingResponse(
            iter([csv_buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={table_name}.csv"},
        )

    except Exception:
        raise HTTPException(status_code=500, detail="导出表数据失败")


@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_analyst),
):
    """上传 CSV 文件并导入数据库"""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="只支持 CSV 文件")

    try:
        contents = await file.read()

        df = None
        for encoding in _CSV_ENCODINGS:
            try:
                df = pd.read_csv(io.StringIO(contents.decode(encoding)))
                break
            except Exception:
                continue

        if df is None:
            raise HTTPException(status_code=400, detail="文件编码不支持")

        if df.empty:
            raise HTTPException(status_code=400, detail="文件为空")

        df.to_sql(_TARGET_TABLE, engine, if_exists="append", index=False)
        log_service.log_action(
            db=db,
            user_id=current_user.id,
            action="upload",
            resource="data",
            details=f"CSV import rows={len(df)}",
            status="success",
        )

        return {
            "message": "上传成功",
            "rows_imported": len(df),
            "columns": list(df.columns),
        }

    except HTTPException:
        raise
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="上传文件失败")
