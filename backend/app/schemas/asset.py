"""Request and response schemas for equipment management."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AssetStatus


def _required_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Value cannot be blank.")
    return value


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return _required_text(value)


class AssetCreate(BaseModel):
    asset_code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=1, max_length=160)
    serial_number: str | None = Field(default=None, max_length=160)
    manufacturer: str | None = Field(default=None, max_length=160)
    model: str | None = Field(default=None, max_length=160)
    description: str | None = None

    _validate_asset_code = field_validator("asset_code")(_required_text)
    _validate_name = field_validator("name")(_required_text)
    _validate_category = field_validator("category")(_required_text)
    _validate_location = field_validator("location")(_required_text)
    _validate_serial_number = field_validator("serial_number")(_optional_text)
    _validate_manufacturer = field_validator("manufacturer")(_optional_text)
    _validate_model = field_validator("model")(_optional_text)


class AssetUpdate(BaseModel):
    asset_code: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    category: str | None = Field(default=None, min_length=1, max_length=120)
    location: str | None = Field(default=None, min_length=1, max_length=160)
    serial_number: str | None = Field(default=None, max_length=160)
    manufacturer: str | None = Field(default=None, max_length=160)
    model: str | None = Field(default=None, max_length=160)
    description: str | None = None

    _validate_asset_code = field_validator("asset_code")(_optional_text)
    _validate_name = field_validator("name")(_optional_text)
    _validate_category = field_validator("category")(_optional_text)
    _validate_location = field_validator("location")(_optional_text)
    _validate_serial_number = field_validator("serial_number")(_optional_text)
    _validate_manufacturer = field_validator("manufacturer")(_optional_text)
    _validate_model = field_validator("model")(_optional_text)


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_code: str
    name: str
    category: str
    serial_number: str | None
    manufacturer: str | None
    model: str | None
    location: str
    description: str | None
    status: AssetStatus
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class AssetListResponse(BaseModel):
    items: list[AssetResponse]
    total: int
    skip: int
    limit: int
