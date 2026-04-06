import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.db.session import get_db
from api.deps import get_current_user
from api.models.alert import Alert
from api.models.product import Product
from api.schemas.alert import AlertCreate, AlertOut, AlertUpdate

router = APIRouter()


@router.post("", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
async def create_alert(
    payload: AlertCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify product exists
    result = await db.execute(select(Product).where(Product.id == payload.product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check for existing alert (upsert pattern)
    result = await db.execute(
        select(Alert).where(
            Alert.user_id == current_user.id,
            Alert.product_id == payload.product_id,
        )
    )
    alert = result.scalar_one_or_none()

    if alert:
        # Update existing
        alert.target_price = payload.target_price
        alert.is_active = True
        alert.notify_on_any_drop = payload.notify_on_any_drop
    else:
        alert = Alert(
            user_id=current_user.id,
            product_id=payload.product_id,
            target_price=payload.target_price,
            notify_on_any_drop=payload.notify_on_any_drop,
        )
        db.add(alert)

    await db.commit()
    await db.refresh(alert)

    # Load product relationship
    result = await db.execute(
        select(Alert)
        .options(selectinload(Alert.product))
        .where(Alert.id == alert.id)
    )
    return result.scalar_one()


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert)
        .options(selectinload(Alert.product))
        .where(Alert.user_id == current_user.id, Alert.is_active == True)  # noqa: E712
    )
    return result.scalars().all()


@router.patch("/{alert_id}", response_model=AlertOut)
async def update_alert(
    alert_id: uuid.UUID,
    payload: AlertUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert)
        .options(selectinload(Alert.product))
        .where(Alert.id == alert_id, Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if payload.target_price is not None:
        alert.target_price = payload.target_price
    if payload.is_active is not None:
        alert.is_active = payload.is_active
    if payload.notify_on_any_drop is not None:
        alert.notify_on_any_drop = payload.notify_on_any_drop

    await db.commit()
    await db.refresh(alert)
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.delete(alert)
    await db.commit()
