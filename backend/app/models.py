from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Mode = Literal["separate", "combined"]
FieldStatus = Literal["match", "mismatch"]
SubmissionStatus = Literal["approved", "needs_correction", "to_review"]
DecidedBy = Literal["system", "agent_confirmed", "agent_override", "agent_manual"]
DecisionAction = Literal["confirm", "override", "manual_decision"]


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
    status: FieldStatus


class SubmissionSummary(BaseModel):
    id: str
    brand: str
    submitted_at: str
    status: SubmissionStatus
    decided_by: DecidedBy


class SubmissionDetail(BaseModel):
    id: str
    submitted_at: str
    status: SubmissionStatus
    decided_by: DecidedBy
    override_reason: str | None = None
    decided_at: str | None = None
    extraction_ok: bool
    extraction_error: str | None = None
    application_fields: ExtractedFields
    label_fields: ExtractedFields
    field_results: list[FieldResult]
    application_file_url: str
    label_file_url: str
    processing_time_ms: int = Field(ge=0)


class DecisionRequest(BaseModel):
    action: DecisionAction
    new_status: SubmissionStatus | None = None
    reason: str | None = None
