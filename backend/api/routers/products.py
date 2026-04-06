import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.session import get_db
from api.deps import get_current_user
from api.models.alert import Alert
from api.models.product import Product
from api.schemas.product import ProductOut, ProductSubmit
from api.services.product_service import canonicalize_url

router = APIRouter()


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def submit_product(
    payload: ProductSubmit,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a product URL for tracking. Returns existing product if URL already known."""
    try:
        canonical_url, site = canonicalize_url(payload.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check if product already exists (deduplication)
    result = await db.execute(select(Product).where(Product.canonical_url == canonical_url))
    product = result.scalar_one_or_none()

    if not product:
        product = Product(
            canonical_url=canonical_url,
            original_url=payload.url,
            site=site,
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)

        # Trigger an immediate first scrape via Celery
        try:
            from worker.tasks.scrape_tasks import scrape_product
            scrape_product.apply_async(args=[str(product.id)], queue="scrape_normal")
        except Exception:
            pass  # Don't fail the API call if Celery is unavailable

    return product


@router.get("", response_model=list[ProductOut])
async def list_products(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all products the current user is tracking."""
    result = await db.execute(
        select(Product)
        .join(Alert, Alert.product_id == Product.id)
        .where(Alert.user_id == current_user.id, Alert.is_active == True)  # noqa: E712
    )
    products = result.scalars().all()
    return products


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.delete("/{product_id}/untrack", status_code=status.HTTP_204_NO_CONTENT)
async def untrack_product(
    product_id: uuid.UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate the user's alert for this product (does not delete the product)."""
    result = await db.execute(
        select(Alert).where(
            Alert.user_id == current_user.id,
            Alert.product_id == product_id,
        )
    )
    alert = result.scalar_one_or_none()
    if alert:
        alert.is_active = False
        db.add(alert)
        await db.commit()
