from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Status = Literal["match", "review", "fail"]
Mode = Literal["separate", "combined"]


class ExtractedFields(BaseModel):
    brand: str = ""
    classType: str = ""
    abv: str = ""
    netContents: str = ""
    warning: str = ""


class FieldResult(BaseModel):
    key: str
    label: str
    appVal: str
    scanVal: str
    status: Status


class VerifyResponse(BaseModel):
    application_fields: ExtractedFields
    label_fields: ExtractedFields
    results: list[FieldResult]
    overall_status: Status
    processing_time_ms: int = Field(ge=0)
