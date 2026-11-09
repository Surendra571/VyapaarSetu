import base64
import uuid
from typing import Tuple, List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import require_retailer
from app.models.user import User
from app.models.retailer import Retailer
from app.models.catalog import Product, SKUAlias
from app.models.ai_capture import AICapture, AICaptureLine
from app.schemas.ai_capture import (
    AICandidateAlternative,
    AICaptureTextRequest,
    AICaptureMediaUploadRequest,
    AICaptureResponse,
    AICaptureLineResponse,
    AICaptureLinePatchRequest,
    AICaptureConfirmResponse,
    RetailerAliasCreateRequest,
    RetailerAliasResponse,
)
from app.services.ai_capture_service import AICaptureService
from app.core.rate_limiter import ai_rate_limiter

router = APIRouter()


def _serialize_line(line: AICaptureLine) -> AICaptureLineResponse:
    score = line.confidence_score or Decimal("0.00")
    if score >= Decimal("0.85"):
        level = "HIGH"
    elif score >= Decimal("0.50"):
        level = "MEDIUM"
    else:
        level = "LOW"

    meta = line.alternatives_json or {}
    raw_alts = meta.get("alternatives", []) if isinstance(meta, dict) else (meta if isinstance(meta, list) else [])
    alts = [AICandidateAlternative(**a) for a in raw_alts]

    language = meta.get("language", "Hinglish") if isinstance(meta, dict) else "Hinglish"
    unit_clarification = meta.get("unit_clarification_needed", False) if isinstance(meta, dict) else False
    clarification_prompt = meta.get("clarification_prompt") if isinstance(meta, dict) else line.resolution_note
    saved_as_alias = meta.get("saved_as_alias", False) if isinstance(meta, dict) else False

    return AICaptureLineResponse(
        id=line.id,
        line_number=line.line_number,
        raw_line_text=line.raw_line_text,
        parsed_item_name=line.parsed_item_name,
        parsed_quantity=line.parsed_quantity,
        parsed_uom=line.parsed_uom,
        language=language,
        unit_clarification_needed=unit_clarification,
        clarification_prompt=clarification_prompt or line.resolution_note,
        matched_product_id=line.matched_product.id if line.matched_product else None,
        matched_sku_code=line.matched_product.sku_code if line.matched_product else None,
        matched_product_name=line.matched_product.name if line.matched_product else None,
        confidence_score=score,
        confidence_level=level,
        is_uncertain=line.is_uncertain,
        alternatives=alts,
        resolved_product_id=line.resolved_product.id if line.resolved_product else None,
        resolved_product_name=line.resolved_product.name if line.resolved_product else None,
        resolved_quantity=line.resolved_quantity,
        is_confirmed=line.is_confirmed,
        saved_as_alias=saved_as_alias,
    )


def _serialize_capture(capture: AICapture) -> AICaptureResponse:
    lines = [_serialize_line(line) for line in sorted(capture.lines, key=lambda x: x.line_number)]
    has_unconfirmed = any(not l.is_confirmed for l in lines)

    # Check fallback status from first line metadata or model_version string
    is_fallback = "fallback" in (capture.model_version or "").lower()
    service_msg = None
    if capture.lines and isinstance(capture.lines[0].alternatives_json, dict):
        service_msg = capture.lines[0].alternatives_json.get("service_message")

    return AICaptureResponse(
        id=capture.id,
        retailer_id=capture.retailer_id,
        raw_text=capture.raw_text,
        status=capture.status,
        model_version=capture.model_version,
        lines=lines,
        has_unconfirmed_lines=has_unconfirmed,
        is_ai_fallback=is_fallback,
        ai_service_message=service_msg,
    )


@router.post(
    "/text",
    response_model=AICaptureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Parse raw WhatsApp or unformatted text into candidate order lines",
)
async def capture_order_text(
    payload: AICaptureTextRequest,
    current_user_and_retailer: Tuple[User, Retailer] = Depends(require_retailer),
    db: AsyncSession = Depends(get_db),
):
    _, retailer = current_user_and_retailer
    # Enforce sliding-window rate limit on AI endpoint
    ai_rate_limiter.check_rate_limit(f"retailer:{retailer.id}")
    capture = await AICaptureService.process_text_capture(
        session=db,
        retailer=retailer,
        raw_text=payload.raw_text,
    )
    full_capture = await AICaptureService.get_capture_by_id(db, capture.id, retailer.id)
    if not full_capture:
        raise HTTPException(status_code=500, detail="Failed to retrieve saved AI capture session.")
    return _serialize_capture(full_capture)


ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

ALLOWED_AUDIO_MIMES = {
    "audio/webm", "audio/mp3", "audio/wav", "audio/ogg",
    "audio/m4a", "audio/mpeg", "audio/x-m4a", "audio/mp4",
    "audio/wave", "audio/x-wav",
}
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25MB


@router.post(
    "/photo",
    response_model=AICaptureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Capture order from handwritten list photo",
    description="Accepts an image file or base64 JSON payload of a handwritten grocery slip and parses into candidate order lines.",
)
async def capture_order_photo(
    file: Optional[UploadFile] = File(None),
    payload: Optional[AICaptureMediaUploadRequest] = None,
    current_user_and_retailer: Tuple[User, Retailer] = Depends(require_retailer),
    db: AsyncSession = Depends(get_db),
):
    _, retailer = current_user_and_retailer
    ai_rate_limiter.check_rate_limit(f"retailer:{retailer.id}")

    image_bytes = b""
    mime_type = "image/jpeg"
    filename = "photo_order.jpg"

    if file:
        image_bytes = await file.read()
        mime_type = file.content_type or "image/jpeg"
        filename = file.filename or filename
    elif payload and payload.media_base64:
        try:
            image_bytes = base64.b64decode(payload.media_base64.split(",")[-1])
            mime_type = payload.mime_type or "image/jpeg"
            filename = payload.filename or filename
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid base64 image data.")

    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image data received. Please upload an image file or base64 image payload.",
        )

    # Validate image format
    normalized_mime = mime_type.lower().split(";")[0].strip()
    if normalized_mime not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image format '{mime_type}'. Supported formats: JPEG, PNG, WEBP.",
        )

    # Validate file size
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image size ({len(image_bytes)} bytes) exceeds the maximum allowed limit of 10MB.",
        )

    try:
        capture = await AICaptureService.process_photo_order(
            session=db,
            retailer=retailer,
            image_bytes=image_bytes,
            mime_type=normalized_mime,
            filename=filename,
        )
        full_capture = await AICaptureService.get_capture_by_id(db, capture.id, retailer.id)
        if not full_capture:
            raise HTTPException(status_code=500, detail="Failed to retrieve saved AI capture session.")
        return _serialize_capture(full_capture)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not detect legible grocery order items in this photo. Please upload a clear photo of your handwritten grocery order slip.",
        )


@router.post(
    "/voice",
    response_model=AICaptureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Capture order from Hindi / Hinglish voice note",
    description="Accepts audio file or base64 audio and transcribes into candidate order lines with clarification prompts.",
)
async def capture_order_voice(
    file: Optional[UploadFile] = File(None),
    payload: Optional[AICaptureMediaUploadRequest] = None,
    current_user_and_retailer: Tuple[User, Retailer] = Depends(require_retailer),
    db: AsyncSession = Depends(get_db),
):
    _, retailer = current_user_and_retailer
    ai_rate_limiter.check_rate_limit(f"retailer:{retailer.id}")

    audio_bytes = b""
    mime_type = "audio/webm"
    filename = "voice_note.webm"

    if file:
        audio_bytes = await file.read()
        mime_type = file.content_type or "audio/webm"
        filename = file.filename or filename
    elif payload and payload.media_base64:
        try:
            audio_bytes = base64.b64decode(payload.media_base64.split(",")[-1])
            mime_type = payload.mime_type or "audio/webm"
            filename = payload.filename or filename
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid base64 audio data.")

    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No audio data received. Please upload an audio file or base64 audio payload.",
        )

    # Validate audio format
    normalized_mime = mime_type.lower().split(";")[0].strip()
    if normalized_mime not in ALLOWED_AUDIO_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format '{mime_type}'. Supported formats: WEBM, MP3, WAV, OGG, M4A.",
        )

    # Validate audio size
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio recording size ({len(audio_bytes)} bytes) exceeds the maximum allowed limit of 25MB.",
        )

    try:
        capture = await AICaptureService.process_voice_order(
            session=db,
            retailer=retailer,
            audio_bytes=audio_bytes,
            mime_type=normalized_mime,
            filename=filename,
        )
        full_capture = await AICaptureService.get_capture_by_id(db, capture.id, retailer.id)
        if not full_capture:
            raise HTTPException(status_code=500, detail="Failed to retrieve saved AI capture session.")
        return _serialize_capture(full_capture)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not understand the voice note clearly. Please upload or record a clear audio note with product names and quantities.",
        )


@router.get(
    "/{id}",
    response_model=AICaptureResponse,
    summary="Get AI capture session with candidate SKU matches and alternatives",
)
async def get_ai_capture_session(
    id: uuid.UUID,
    current_user_and_retailer: Tuple[User, Retailer] = Depends(require_retailer),
    db: AsyncSession = Depends(get_db),
):
    _, retailer = current_user_and_retailer
    capture = await AICaptureService.get_capture_by_id(db, id, retailer.id)
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI capture session not found or does not belong to current retailer.",
        )
    return _serialize_capture(capture)


@router.patch(
    "/{id}/lines/{line_id}",
    response_model=AICaptureLineResponse,
    summary="Manually resolve or confirm an uncertain AI parsed line item (with optional alias saving)",
)
async def patch_ai_capture_line(
    id: uuid.UUID,
    line_id: uuid.UUID,
    payload: AICaptureLinePatchRequest,
    current_user_and_retailer: Tuple[User, Retailer] = Depends(require_retailer),
    db: AsyncSession = Depends(get_db),
):
    _, retailer = current_user_and_retailer
    line = await AICaptureService.patch_capture_line(
        session=db,
        capture_id=id,
        line_id=line_id,
        retailer_id=retailer.id,
        resolved_product_id=payload.resolved_product_id,
        resolved_quantity=payload.resolved_quantity,
        resolved_uom=payload.resolved_uom,
        is_confirmed=payload.is_confirmed,
        note=payload.resolution_note,
        save_as_retailer_alias=payload.save_as_retailer_alias,
        alias_phrase=payload.alias_phrase,
    )
    return _serialize_line(line)


@router.post(
    "/{id}/confirm",
    response_model=AICaptureConfirmResponse,
    summary="Transfer all confirmed AI items into a shopping cart / order preview",
)
async def confirm_ai_capture_session(
    id: uuid.UUID,
    current_user_and_retailer: Tuple[User, Retailer] = Depends(require_retailer),
    db: AsyncSession = Depends(get_db),
):
    _, retailer = current_user_and_retailer
    return await AICaptureService.confirm_and_generate_preview(
        session=db,
        capture_id=id,
        retailer=retailer,
    )


# ---------------------------------------------------------------------------
# Part F: Retailer Aliases Management Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/aliases",
    response_model=RetailerAliasResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a custom retailer-specific phrase alias for a product SKU",
)
async def create_retailer_alias(
    payload: RetailerAliasCreateRequest,
    current_user_and_retailer: Tuple[User, Retailer] = Depends(require_retailer),
    db: AsyncSession = Depends(get_db),
):
    _, retailer = current_user_and_retailer

    # Verify product exists
    prod_stmt = select(Product).where(Product.id == payload.product_id, Product.is_active == True)
    prod_res = await db.execute(prod_stmt)
    product = prod_res.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product SKU not found in active catalogue.",
        )

    alias_obj = await AICaptureService.save_retailer_alias(
        session=db,
        retailer_id=retailer.id,
        product_id=product.id,
        alias_text=payload.alias_text,
        notes=payload.notes,
    )
    await db.commit()
    await db.refresh(alias_obj)

    return RetailerAliasResponse(
        id=alias_obj.id,
        product_id=product.id,
        sku_code=product.sku_code,
        product_name=product.name,
        alias_text=alias_obj.alias_text,
        retailer_id=retailer.id,
        is_retailer_specific=True,
    )


@router.get(
    "/aliases",
    response_model=List[RetailerAliasResponse],
    summary="List all retailer-specific and global aliases visible to this retailer",
)
async def list_retailer_aliases(
    current_user_and_retailer: Tuple[User, Retailer] = Depends(require_retailer),
    db: AsyncSession = Depends(get_db),
):
    _, retailer = current_user_and_retailer
    stmt = (
        select(SKUAlias)
        .where(
            or_(SKUAlias.retailer_id == retailer.id, SKUAlias.retailer_id.is_(None))
        )
        .options(selectinload(SKUAlias.product))
        .order_by(SKUAlias.created_at.desc())
    )
    res = await db.execute(stmt)
    aliases = res.scalars().all()

    return [
        RetailerAliasResponse(
            id=al.id,
            product_id=al.product.id,
            sku_code=al.product.sku_code,
            product_name=al.product.name,
            alias_text=al.alias_text,
            retailer_id=al.retailer_id,
            is_retailer_specific=(al.retailer_id == retailer.id),
        )
        for al in aliases
    ]
