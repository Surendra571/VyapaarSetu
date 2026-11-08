import uuid
from decimal import Decimal
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.order import OrderPreviewResponse


# ---------------------------------------------------------------------------
# OpenAI Structured Output Validation Schemas
# ---------------------------------------------------------------------------

class OpenAILineExtraction(BaseModel):
    """Pydantic schema to validate structured extraction directly from OpenAI."""
    original_phrase: str = Field(description="Exact snippet from input text for this item")
    product_description: str = Field(description="Cleaned product name or description, e.g. 'biscuit chhota', 'washing powder 1 kilo'")
    quantity: Optional[int] = Field(default=None, description="Extracted numerical quantity")
    unit: Optional[str] = Field(default=None, description="Unit mentioned in input, e.g. 'peti', 'case', 'carton', 'packet', 'kilo', 'piece', or 'unclear'")
    language: str = Field(default="Hinglish", description="Detected language, e.g. 'Hinglish', 'Hindi', 'English'")
    possible_product_mapping: Optional[str] = Field(default=None, description="Suggested product candidate or category")
    unit_clarification_needed: bool = Field(default=False, description="True if quantity unit is missing or ambiguous (e.g., case vs piece)")


class OpenAIExtractionPayload(BaseModel):
    """Container schema for OpenAI structured extraction."""
    lines: List[OpenAILineExtraction] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API Request / Response Schemas
# ---------------------------------------------------------------------------

class AICaptureTextRequest(BaseModel):
    """Raw natural language text/WhatsApp paste."""
    raw_text: str = Field(
        ...,
        min_length=3,
        description="Unstructured text order (e.g., 'bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo, chai patti 250 wala 1 peti')",
        examples=["bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo, chai patti 250 wala 1 peti"],
    )


class AICaptureMediaUploadRequest(BaseModel):
    """Base64 media payload for handwritten photo or audio voice note order capture."""
    media_base64: Optional[str] = Field(None, description="Base64 encoded image or audio bytes")
    media_type: Literal["image", "audio"] = Field("image", description="Media category")
    mime_type: Optional[str] = Field("image/jpeg", description="MIME type (e.g. image/jpeg, audio/webm)")
    filename: Optional[str] = None


class AICandidateAlternative(BaseModel):
    """Suggested SKU alternative when confidence is below cutoff."""
    product_id: uuid.UUID
    sku_code: str
    product_name: str
    pack_size: str
    confidence: Decimal


class AICaptureLinePatchRequest(BaseModel):
    """Manual retailer disambiguation or correction of an AI parsed line."""
    resolved_product_id: Optional[uuid.UUID] = Field(None, description="Correct SKU selected by user")
    resolved_quantity: Optional[int] = Field(None, ge=1, description="Quantity confirmed by user")
    resolved_uom: Optional[Literal["CASE", "PIECE"]] = Field(
        None,
        description="Explicitly confirmed order unit; piece orders are not currently supported at checkout.",
    )
    is_confirmed: bool = Field(True, description="Mark line as confirmed")
    resolution_note: Optional[str] = None
    save_as_retailer_alias: bool = Field(
        False,
        description="Save the corrected phrase as a custom retailer alias in the database",
    )
    alias_phrase: Optional[str] = Field(
        None,
        description="Custom phrase to save as alias. If omitted, uses line's parsed_item_name",
    )


class RetailerAliasCreateRequest(BaseModel):
    """Explicitly save a retailer-specific phrase alias for a product SKU."""
    product_id: uuid.UUID
    alias_text: str = Field(..., min_length=2, max_length=200)
    notes: Optional[str] = None


class RetailerAliasResponse(BaseModel):
    """Saved SKU alias representation."""
    id: uuid.UUID
    product_id: uuid.UUID
    sku_code: str
    product_name: str
    alias_text: str
    retailer_id: Optional[uuid.UUID] = None
    is_retailer_specific: bool = True

    model_config = ConfigDict(from_attributes=True)


class AICaptureLineResponse(BaseModel):
    """Parsed line item with confidence rating, clarification prompt, and candidate alternatives."""
    id: uuid.UUID
    line_number: int
    raw_line_text: str
    parsed_item_name: str
    parsed_quantity: int
    parsed_uom: str
    language: str = "Hinglish"
    unit_clarification_needed: bool = False
    clarification_prompt: Optional[str] = None
    matched_product_id: Optional[uuid.UUID] = None
    matched_sku_code: Optional[str] = None
    matched_product_name: Optional[str] = None
    confidence_score: Decimal
    confidence_level: str = Field(description="HIGH (>=0.85) | MEDIUM (0.50-0.84) | LOW (<0.50)")
    is_uncertain: bool = Field(description="Must be resolved by human if true")
    alternatives: List[AICandidateAlternative] = []
    resolved_product_id: Optional[uuid.UUID] = None
    resolved_product_name: Optional[str] = None
    resolved_quantity: Optional[int] = None
    is_confirmed: bool
    saved_as_alias: bool = False

    model_config = ConfigDict(from_attributes=True)


class AICaptureResponse(BaseModel):
    """AI extraction session with parsed lines and confidence metadata."""
    id: uuid.UUID
    retailer_id: uuid.UUID
    raw_text: str
    status: str
    model_version: str
    lines: List[AICaptureLineResponse] = []
    has_unconfirmed_lines: bool
    is_ai_fallback: bool = False
    ai_service_message: Optional[str] = None
    notice: str = "AI cannot place orders automatically. Review and confirm all lines before checkout."

    model_config = ConfigDict(from_attributes=True)


class AICaptureConfirmResponse(BaseModel):
    """Transfer of confirmed AI items into order preview."""
    session_id: uuid.UUID
    confirmed_lines_count: int
    order_preview: OrderPreviewResponse
