from __future__ import annotations

from pydantic import BaseModel, Field


class IntentClassificationResult(BaseModel):
    intent: str = Field(..., description="Classified intent identifier")
    category: str = Field(..., description="Associated domain category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence score between 0.0 and 1.0")
    requires_knowledge_search: bool = Field(default=True, description="Whether this query needs knowledge base retrieval")
    requires_human: bool = Field(default=False, description="Whether this query immediately requires human escalation")
