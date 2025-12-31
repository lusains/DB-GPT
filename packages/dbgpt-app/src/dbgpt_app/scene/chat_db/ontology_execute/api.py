"""REST API for Semantic Dictionary Management.

Provides endpoints for:
- Viewing dictionary entries
- Adding aliases, abbreviations, slang
- Removing entries
- Saving/loading dictionary
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from dbgpt_app.scene.chat_db.ontology_execute.semantic_index import (
    get_semantic_index,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Request/Response Models ====================


class AddAliasRequest(BaseModel):
    """Request to add an alias for a term."""

    canonical: str = Field(..., description="The canonical/standard term (must match rdfs:label)")
    alias: str = Field(..., description="The alias to add")


class AddAbbreviationRequest(BaseModel):
    """Request to add an abbreviation."""

    abbreviation: str = Field(..., description="The abbreviation (e.g., 'PM')")
    expansion: str = Field(..., description="The expanded form (e.g., '项目经理')")
    is_global: bool = Field(False, description="If true, not tied to specific ontology term")


class AddSlangRequest(BaseModel):
    """Request to add a slang/jargon term."""

    slang: str = Field(..., description="The slang term")
    meaning: str = Field(..., description="The canonical meaning")


class RemoveVariantRequest(BaseModel):
    """Request to remove a variant (alias/abbr/slang)."""

    variant: str = Field(..., description="The variant to remove")


class TermMappingResponse(BaseModel):
    """Response containing a term mapping."""

    canonical: str
    property_name: str
    aliases: List[str]
    abbreviations: List[str]
    slang: List[str]
    context_hints: List[str]


class DictionaryStatsResponse(BaseModel):
    """Response containing dictionary statistics."""

    loaded: bool
    canonical_terms: int
    total_variants: int
    global_abbreviations: int


class NormalizeQueryRequest(BaseModel):
    """Request to normalize a query."""

    query: str = Field(..., description="The query to normalize")


class NormalizeQueryResponse(BaseModel):
    """Response with normalized query."""

    original: str
    normalized: str
    changed: bool


# ==================== API Endpoints ====================


@router.get("/dictionary/stats", response_model=DictionaryStatsResponse)
async def get_dictionary_stats():
    """Get semantic dictionary statistics."""
    index = get_semantic_index()
    stats = index.dictionary.get_stats()
    return DictionaryStatsResponse(**stats)


@router.get("/dictionary/terms", response_model=List[TermMappingResponse])
async def list_dictionary_terms():
    """List all term mappings in the dictionary."""
    index = get_semantic_index()
    terms = []
    for canonical in index.dictionary.get_canonical_terms():
        mapping = index.dictionary.get_mapping(canonical)
        if mapping:
            terms.append(TermMappingResponse(
                canonical=mapping.canonical,
                property_name=mapping.property_name,
                aliases=mapping.aliases,
                abbreviations=mapping.abbreviations,
                slang=mapping.slang,
                context_hints=mapping.context_hints,
            ))
    return terms


@router.get("/dictionary/term/{canonical}", response_model=TermMappingResponse)
async def get_term_mapping(canonical: str):
    """Get mapping for a specific canonical term."""
    index = get_semantic_index()
    mapping = index.dictionary.get_mapping(canonical)
    if not mapping:
        raise HTTPException(status_code=404, detail=f"Term not found: {canonical}")

    return TermMappingResponse(
        canonical=mapping.canonical,
        property_name=mapping.property_name,
        aliases=mapping.aliases,
        abbreviations=mapping.abbreviations,
        slang=mapping.slang,
        context_hints=mapping.context_hints,
    )


@router.post("/dictionary/alias")
async def add_alias(request: AddAliasRequest):
    """Add an alias for a canonical term."""
    index = get_semantic_index()
    index.add_alias(request.canonical, request.alias)
    logger.info(f"Added alias: {request.alias} → {request.canonical}")
    return {"success": True, "message": f"Added alias '{request.alias}' for '{request.canonical}'"}


@router.post("/dictionary/abbreviation")
async def add_abbreviation(request: AddAbbreviationRequest):
    """Add an abbreviation mapping."""
    index = get_semantic_index()
    index.add_abbreviation(request.abbreviation, request.expansion, request.is_global)
    logger.info(f"Added abbreviation: {request.abbreviation} → {request.expansion} (global={request.is_global})")
    return {"success": True, "message": f"Added abbreviation '{request.abbreviation}' → '{request.expansion}'"}


@router.post("/dictionary/slang")
async def add_slang(request: AddSlangRequest):
    """Add a slang/jargon term."""
    index = get_semantic_index()
    index.add_slang(request.slang, request.meaning)
    logger.info(f"Added slang: {request.slang} → {request.meaning}")
    return {"success": True, "message": f"Added slang '{request.slang}' → '{request.meaning}'"}


@router.delete("/dictionary/variant")
async def remove_variant(request: RemoveVariantRequest):
    """Remove a variant (alias, abbreviation, or slang) from the dictionary."""
    index = get_semantic_index()
    success = index.dictionary.remove_variant(request.variant)
    if success:
        logger.info(f"Removed variant: {request.variant}")
        return {"success": True, "message": f"Removed variant '{request.variant}'"}
    else:
        raise HTTPException(status_code=404, detail=f"Variant not found: {request.variant}")


@router.post("/dictionary/normalize", response_model=NormalizeQueryResponse)
async def normalize_query(request: NormalizeQueryRequest):
    """Normalize a query by expanding abbreviations and slang."""
    index = get_semantic_index()
    normalized = index.normalize_query(request.query)
    return NormalizeQueryResponse(
        original=request.query,
        normalized=normalized,
        changed=normalized != request.query,
    )


@router.post("/dictionary/save")
async def save_dictionary(path: Optional[str] = None):
    """Save the current dictionary to file.

    Args:
        path: Optional path to save to. If not provided, uses default path.
    """
    from pathlib import Path as PathLib

    index = get_semantic_index()

    if not path:
        # Use default path
        current_file = PathLib(__file__)
        project_root = current_file.parent.parent.parent.parent.parent.parent.parent.parent
        path = str(project_root / "assets" / "schema" / "semantic_dictionary.json")

    success = index.save_dictionary(path)
    if success:
        return {"success": True, "message": f"Dictionary saved to {path}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to save dictionary")


@router.post("/dictionary/reload")
async def reload_dictionary(path: Optional[str] = None):
    """Reload dictionary from file.

    Args:
        path: Optional path to load from. If not provided, uses default path.
    """
    from pathlib import Path as PathLib

    index = get_semantic_index()

    if not path:
        # Use default path
        current_file = PathLib(__file__)
        project_root = current_file.parent.parent.parent.parent.parent.parent.parent.parent
        path = str(project_root / "assets" / "schema" / "semantic_dictionary.json")

    success = index.load_dictionary(path)
    if success:
        stats = index.dictionary.get_stats()
        return {"success": True, "message": f"Dictionary reloaded from {path}", "stats": stats}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to load dictionary from {path}")
