import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ExportBatchCreateRequest(BaseModel):
    """Trigger Tally CSV export generation."""
    order_ids: Optional[List[uuid.UUID]] = Field(
        None,
        description="Explicit order IDs to export. If omitted, all approved unexported orders are included.",
    )


class ExportBatchResponse(BaseModel):
    """Generated Tally export batch summary."""
    id: uuid.UUID
    batch_number: str
    order_count: int
    total_amount_excl_gst: Decimal
    file_name: str
    file_format: str
    download_url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExportBatchDetailResponse(ExportBatchResponse):
    """Export batch with included order numbers and CSV header preview."""
    order_numbers: List[str] = []
    csv_preview_sample: str
