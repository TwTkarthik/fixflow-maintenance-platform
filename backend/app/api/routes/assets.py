"""Authenticated equipment-management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models import Asset, AssetStatus, User, UserRole
from app.schemas.asset import AssetCreate, AssetListResponse, AssetResponse, AssetUpdate


router = APIRouter(prefix="/api/assets", tags=["assets"])
ManagerOrAdministrator = Annotated[
    User,
    Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.MANAGER)),
]


def _asset_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Asset not found.")


def _duplicate_asset_code() -> HTTPException:
    return HTTPException(status_code=409, detail="An asset with that asset code already exists.")


def _commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if "asset_code" in str(error.orig).lower() or "uq_assets_asset_code" in str(error.orig):
            raise _duplicate_asset_code() from error
        raise


@router.get("", response_model=AssetListResponse)
def list_assets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, max_length=160),
    category: str | None = Query(default=None, max_length=120),
    location: str | None = Query(default=None, max_length=160),
    asset_status: AssetStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> AssetListResponse:
    """List assets with deterministic id ordering and bounded pagination."""

    del current_user
    filters = []
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        filters.append(or_(Asset.asset_code.ilike(pattern), Asset.name.ilike(pattern)))
    if category and category.strip():
        filters.append(Asset.category.ilike(category.strip()))
    if location and location.strip():
        filters.append(Asset.location.ilike(location.strip()))
    if asset_status is not None:
        filters.append(Asset.status == asset_status)

    where_clause = tuple(filters)
    total = db.scalar(select(func.count(Asset.id)).where(*where_clause)) or 0
    assets = db.scalars(
        select(Asset)
        .where(*where_clause)
        .order_by(Asset.id)
        .offset(skip)
        .limit(limit)
    ).all()
    return AssetListResponse(
        items=[AssetResponse.model_validate(asset) for asset in assets],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: AssetCreate,
    current_user: ManagerOrAdministrator,
    db: Session = Depends(get_db),
) -> AssetResponse:
    """Create an active asset for an administrator or manager."""

    asset = Asset(
        **payload.model_dump(),
        status=AssetStatus.ACTIVE,
        created_by_id=current_user.id,
    )
    db.add(asset)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        if "asset_code" in str(error.orig).lower() or "uq_assets_asset_code" in str(error.orig):
            raise _duplicate_asset_code() from error
        raise
    db.refresh(asset)
    _commit_or_conflict(db)
    return AssetResponse.model_validate(asset)


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(
    asset_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssetResponse:
    """Retrieve an asset, including deactivated historical records."""

    del current_user
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise _asset_not_found()
    return AssetResponse.model_validate(asset)


@router.patch("/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: int,
    payload: AssetUpdate,
    current_user: ManagerOrAdministrator,
    db: Session = Depends(get_db),
) -> AssetResponse:
    """Apply a partial update to editable asset fields."""

    asset = db.get(Asset, asset_id)
    if asset is None:
        raise _asset_not_found()
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one editable field is required.")
    for field_name, value in changes.items():
        setattr(asset, field_name, value)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        if "asset_code" in str(error.orig).lower() or "uq_assets_asset_code" in str(error.orig):
            raise _duplicate_asset_code() from error
        raise
    db.refresh(asset)
    _commit_or_conflict(db)
    return AssetResponse.model_validate(asset)


@router.post("/{asset_id}/deactivate", response_model=AssetResponse)
def deactivate_asset(
    asset_id: int,
    current_user: ManagerOrAdministrator,
    db: Session = Depends(get_db),
) -> AssetResponse:
    """Deactivate an asset without deleting its historical record."""

    asset = db.get(Asset, asset_id)
    if asset is None:
        raise _asset_not_found()
    if asset.status != AssetStatus.DEACTIVATED:
        asset.status = AssetStatus.DEACTIVATED
        db.flush()
        db.refresh(asset)
        _commit_or_conflict(db)
    return AssetResponse.model_validate(asset)
