import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.session import get_db
from api.deps import get_current_user
from api.models.price_record import PriceRecord
from api.models.product import Product
from api.schemas.price import PriceHistoryOut, PriceRecordOut

router = APIRouter()


@router.get("/{product_id}/history", response_model=PriceHistoryOut)
async def get_price_history(
    product_id: uuid.UUID,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify product exists
    result = await db.execute(select(Product).where(Product.id == product_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")

    # Count total records
    count_result = await db.execute(
        select(func.count()).where(PriceRecord.product_id == product_id)
    )
    total = count_result.scalar_one()

    # Fetch paginated records
    records_result = await db.execute(
        select(PriceRecord)
        .where(PriceRecord.product_id == product_id)
        .order_by(PriceRecord.scraped_at.desc())
        .limit(limit)
        .offset(offset)
    )
    records = records_result.scalars().all()

    return PriceHistoryOut(
        product_id=product_id,
        records=[PriceRecordOut.model_validate(r) for r in records],
        total=total,
    )
