from __future__ import annotations

import base64
import asyncio
import json
import os
from typing import Any, Literal

from google import genai

from app.models import ExtractedFields


MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

FIELD_SCHEMA = {
    "type": "object",
    "properties": {
        "brand": {"type": "string"},
        "classType": {"type": "string"},
        "abv": {"type": "string"},
        "netContents": {"type": "string"},
        "warning": {"type": "string"},
    },
    "required": ["brand", "classType", "abv", "netContents", "warning"],
}

COMBINED_SCHEMA = {
    "type": "object",
    "properties": {
        "application_fields": FIELD_SCHEMA,
        "label_fields": FIELD_SCHEMA,
    },
    "required": ["application_fields", "label_fields"],
}


def _prompt(kind: Literal["application", "label", "combined"]) -> str:
    if kind == "combined":
        source = (
            "This document contains both a submitted application form and label artwork. "
            "Identify which content belongs to the application form and which content belongs "
            "to the label artwork."
        )
        schema = (
            '{"application_fields":{"brand":"","classType":"","abv":"","netContents":"","warning":""},'
            '"label_fields":{"brand":"","classType":"","abv":"","netContents":"","warning":""}}'
        )
    else:
        source = (
            "Extract fields from the submitted application form."
            if kind == "application"
            else "Extract fields from the label artwork that will appear on the bottle."
        )
        schema = '{"brand":"","classType":"","abv":"","netContents":"","warning":""}'

    return f"""{source}

You extract alcohol beverage label compliance fields for TTB review.

Extract these fields:
- brand: brand name
- classType: class/type designation
- abv: alcohol content / alcohol by volume
- netContents: net contents
- warning: the government warning statement

For warning, transcribe the statement exactly as it visually appears, preserving capitalization,
punctuation, line breaks as spaces, and wording. Do not paraphrase or normalize case. If a field
is missing or illegible, return an empty string for that field rather than guessing.

Return only JSON matching this schema:
{schema}"""


def _input_block(data: bytes, media_type: str) -> dict[str, Any]:
    if media_type == "text/plain":
        return {"type": "text", "text": data.decode("utf-8", errors="replace")}

    block_type = "document" if media_type == "application/pdf" else "image"
    return {
        "type": block_type,
        "data": base64.b64encode(data).decode("utf-8"),
        "mime_type": media_type,
    }


def _client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=api_key)


def _coerce_fields(payload: dict[str, Any]) -> ExtractedFields:
    return ExtractedFields(
        brand=str(payload.get("brand") or ""),
        classType=str(payload.get("classType") or ""),
        abv=str(payload.get("abv") or ""),
        netContents=str(payload.get("netContents") or ""),
        warning=str(payload.get("warning") or ""),
    )


def _json_from_text(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise RuntimeError("Gemini did not return valid JSON.")


def _create_interaction(
    data: bytes,
    media_type: str,
    prompt: str,
    schema: dict[str, Any],
    max_output_tokens: int,
) -> dict[str, Any]:
    interaction = _client().interactions.create(
        model=MODEL,
        store=False,
        input=[
            {"type": "text", "text": prompt},
            _input_block(data, media_type),
        ],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": schema,
        },
        generation_config={
            "temperature": 0,
            "max_output_tokens": max_output_tokens,
        },
    )
    return _json_from_text(interaction.output_text)


async def extract_fields(
    data: bytes, media_type: str, kind: Literal["application", "label"]
) -> ExtractedFields:
    payload = await asyncio.to_thread(
        _create_interaction,
        data,
        media_type,
        _prompt(kind),
        FIELD_SCHEMA,
        800,
    )
    return _coerce_fields(payload)


async def extract_combined_fields(data: bytes, media_type: str) -> tuple[ExtractedFields, ExtractedFields]:
    payload = await asyncio.to_thread(
        _create_interaction,
        data,
        media_type,
        _prompt("combined"),
        COMBINED_SCHEMA,
        1200,
    )
    return _coerce_fields(payload.get("application_fields") or {}), _coerce_fields(
        payload.get("label_fields") or {}
    )
