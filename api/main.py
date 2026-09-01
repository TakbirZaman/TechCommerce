"""
FastAPI application (spec section 19).

Two endpoints:
  POST /api/v1/recommendations  — stateless: full requirement in, ranked products out.
  POST /api/v1/advisor/message  — stateful (session_id): incremental conversation
                                   that builds a requirement turn by turn (spec 21/22).

The advisor's session store here is an in-memory dict — fine for local
running/demo, but NOT safe for a multi-instance deployment. Swap
_SESSIONS for a Redis-backed store (keyed by session_id, short TTL) before
running this behind more than one API process.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import ProductRepository, get_product_repository
from ml.data.schemas import Category, RecommendationResponse, UseCase, UserRequirement
from ml.inference.advisor import AdvisorState, advance_conversation
from ml.inference.nl_extraction import extract_requirement
from ml.inference.pipeline import recommend

app = FastAPI(title="Product Intelligence API", version="0.1.0")

_SESSIONS: dict[str, AdvisorState] = {}  # see module docstring re: production replacement


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# POST /api/v1/recommendations  (spec section 19)
# ---------------------------------------------------------------------------

class RecommendationRequest(BaseModel):
    category: Category
    budget: float | None = Field(default=None, description="Treated as budget_max.")
    budget_min: float | None = None
    use_cases: list[UseCase] = Field(default_factory=list)
    query: str | None = Field(
        default=None,
        description="Optional free-text query. If provided, it is parsed via "
        "the NL extractor and merged with the explicit fields above.",
    )
    top_n: int = 10


@app.post("/api/v1/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    request: RecommendationRequest,
    repository: ProductRepository = Depends(get_product_repository),
) -> RecommendationResponse:
    requirement_kwargs: dict = {
        "category": request.category,
        "budget_max": request.budget,
        "budget_min": request.budget_min,
        "use_cases": request.use_cases,
    }

    if request.query:
        extracted, _missing = extract_requirement(request.query)
        if extracted is not None:
            # explicit fields win over parsed ones when both are present
            merged = extracted.model_dump()
            merged.update({k: v for k, v in requirement_kwargs.items() if v not in (None, [])})
            requirement_kwargs = merged

    requirement = UserRequirement(**requirement_kwargs)

    products = repository.get_by_category(requirement.category)
    if not products:
        raise HTTPException(status_code=404, detail=f"No products found for category '{requirement.category}'")

    return recommend(products, requirement, top_n=request.top_n)


# ---------------------------------------------------------------------------
# POST /api/v1/advisor/message  (spec sections 21 & 22)
# ---------------------------------------------------------------------------

class AdvisorMessageRequest(BaseModel):
    session_id: str | None = None
    message: str


class AdvisorMessageResponse(BaseModel):
    session_id: str
    follow_up_question: str | None = None
    requirement: UserRequirement | None = None
    recommendations: RecommendationResponse | None = None


@app.post("/api/v1/advisor/message", response_model=AdvisorMessageResponse)
def advisor_message(
    request: AdvisorMessageRequest,
    repository: ProductRepository = Depends(get_product_repository),
) -> AdvisorMessageResponse:
    session_id = request.session_id or str(uuid.uuid4())
    state = _SESSIONS.setdefault(session_id, AdvisorState())

    state, question, requirement = advance_conversation(state, request.message)
    _SESSIONS[session_id] = state

    recommendations = None
    if requirement is not None:
        products = repository.get_by_category(requirement.category)
        recommendations = recommend(products, requirement, top_n=5) if products else None

    return AdvisorMessageResponse(
        session_id=session_id,
        follow_up_question=question,
        requirement=requirement,
        recommendations=recommendations,
    )
