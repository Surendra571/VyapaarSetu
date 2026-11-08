import math
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.audit import ExportBatch
from app.schemas.export import ExportBatchCreateRequest, ExportBatchResponse
from app.schemas.common import PaginatedResponse
from app.api.deps import require_order_desk
from app.services.export_service import ExportService

router = APIRouter()


def _serialize_batch(batch: ExportBatch) -> ExportBatchResponse:
    return ExportBatchResponse(
        id=batch.id,
        batch_number=batch.batch_number,
        order_count=batch.order_count,
        total_amount_excl_gst=batch.total_amount_excl_gst,
        file_name=batch.file_name,
        file_format=batch.file_format,
        download_url=f"/api/v1/desk/exports/{batch.id}/download",
        created_at=batch.created_at,
    )


@router.post(
    "/exports",
    response_model=ExportBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Tally CSV Export Batch",
    description="Compiles approved orders into a standard Tally CSV voucher export file and transitions orders to EXPORTED.",
)
async def create_export_batch(
    payload: ExportBatchCreateRequest,
    current_user: User = Depends(require_order_desk),
    db: AsyncSession = Depends(get_db),
) -> ExportBatchResponse:
    batch, _ = await ExportService.create_tally_export_batch(
        session=db,
        operator=current_user,
        order_ids=payload.order_ids,
    )
    return _serialize_batch(batch)


@router.get(
    "/exports",
    response_model=PaginatedResponse[ExportBatchResponse],
    summary="List Tally Export Batches",
    description="Paginated list of previous accounting exports with download links and totals.",
)
async def list_export_batches(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_order_desk),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ExportBatchResponse]:
    count_stmt = select(func.count(ExportBatch.id))
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (page - 1) * page_size
    stmt = (
        select(ExportBatch)
        .order_by(ExportBatch.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    batches = result.scalars().all()

    items = [_serialize_batch(b) for b in batches]
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/exports/{id}/download",
    summary="Download Tally Export CSV File",
    description="Streams the raw CSV payload of the generated batch with attachment headers.",
)
async def download_export_batch(
    id: uuid.UUID,
    current_user: User = Depends(require_order_desk),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ExportBatch).where(ExportBatch.id == id)
    res = await db.execute(stmt)
    batch = res.scalar_one_or_none()

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export batch not found.",
        )

    return Response(
        content=batch.csv_payload,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{batch.file_name}"',
        },
    )

