from typing import List
from pydantic import BaseModel
from openai import OpenAI
from .data_types import TranscriptAnalysis

client = OpenAI()

def analyze_transcript(transcript: str, word_count: dict) -> TranscriptAnalysis:
    # Here you might want to use word_count in some way, for example, to help generate keywords
    completion = client.chat.completions.create(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": (
                "You are a helpful assistant analyzing transcripts. "
                "Given a transcript and word count, return a JSON object with the following fields: "
                "quick_summary (string), bullet_point_highlights (list of strings), "
                "sentiment_analysis (string), keywords (list of strings). "
                "Respond ONLY with a valid JSON object matching this structure."
            )},
            {"role": "user", "content": f"Transcript: {transcript}\nWord Count: {word_count}"},
        ],
        response_format={"type": "json_object"},
    )

    content = completion.choices[0].message.content
    try:
        # Parse the JSON content into the TranscriptAnalysis model
        import json
        data = json.loads(content)
        return TranscriptAnalysis(**data)
    except Exception as e:
        raise ValueError(f"Failed to parse the transcript analysis response: {e}")
