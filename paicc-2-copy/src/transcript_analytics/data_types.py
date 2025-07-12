from pydantic import BaseModel
from typing import List

class TranscriptAnalysis(BaseModel):
    quick_summary: str
    bullet_point_highlights: List[str]
    sentiment_analysis: str
    keywords: List[str]
