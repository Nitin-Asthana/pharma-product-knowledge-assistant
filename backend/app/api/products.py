"""Product and category endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..models.product import Product, ProductSummary
from ..services.product_service import product_service

router = APIRouter(prefix="/api")


def _to_summary(p: Product) -> ProductSummary:
    return ProductSummary(
        product_id=p.product_id,
        brand_name=p.brand_name,
        therapeutic_category=p.therapeutic_category,
        composition=p.composition,
        source_id=p.source_id,
        source_name=p.source_name,
        source_url=p.source_url,
    )


@router.get("/products")
def list_products(
    source_id: str | None = Query(default=None),
    category: str | None = Query(default=None),
    ingredient: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Brand name search term"),
) -> dict:
    source_ids = [source_id] if source_id else None

    if ingredient:
        products = product_service.find_by_ingredient(ingredient, source_ids)
    elif category:
        products = product_service.find_by_category(category, source_ids)
    elif q:
        products = product_service.search_by_brand_substring(q, source_ids)
    else:
        products = product_service.all_products(source_ids)

    products = sorted(products, key=lambda p: p.brand_name.lower())
    return {
        "count": len(products),
        "products": [_to_summary(p).model_dump() for p in products],
    }


@router.get("/products/{product_id:path}")
def get_product(product_id: str) -> dict:
    p = product_service.get_product(product_id)
    if p is None:
        raise HTTPException(status_code=404, detail=f"Product not found: {product_id}")
    data = p.model_dump()
    return data


@router.get("/categories")
def list_categories(source_id: str | None = Query(default=None)) -> dict:
    source_ids = [source_id] if source_id else None
    return {"categories": product_service.categories(source_ids)}


@router.get("/ingredients")
def list_ingredients(source_id: str | None = Query(default=None)) -> dict:
    source_ids = [source_id] if source_id else None
    return {"ingredients": product_service.ingredients(source_ids)}
