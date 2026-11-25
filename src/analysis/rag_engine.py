import os
import time
from typing import Any, List

from google import genai
from google.genai import types


class ContributionRAGEngine:
    def __init__(self):
        self.gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def generate_recommendation(self, user_query: str, retrieved_points: List[Any]) -> str:
        if not retrieved_points:
            return "No matching open-source contribution opportunities found."

        # Compile issue payloads into formatted context
        context_blocks = []
        for i, point in enumerate(retrieved_points, 1):
            p = point.payload
            context_blocks.append(
                f"--- ISSUE #{i} ---\n"
                f"Repo: {p.get('repo')}\n"
                f"URL: {p.get('url')}\n"
                f"Labels: {', '.join(p.get('labels', []))}\n"
                f"Content:\n{p.get('text')}\n"
            )

        combined_context = "\n\n".join(context_blocks)

        prompt = f"""You are an Open Source Maintainer and Developer Advocate.
Analyze the following retrieved GitHub issues and recommend the best task for the developer based on their search intent.

DEVELOPER SEARCH INTENT:
"{user_query}"

RETRIEVED ISSUES CONTEXT:
{combined_context}

INSTRUCTIONS:
1. Recommend the top matching issue(s) based on the developer's intent.
2. Provide a 2-sentence summary explaining WHAT needs to be fixed/built.
3. Provide a practical "First Step" tip (e.g., suggested directory/file types to check or setup prerequisites).
4. Include the direct Markdown URL to the GitHub issue. Format cleanly using Markdown bullet points.
"""

        # Call Gemini for fast synthesis. Retry on transient overload (503)
        # or rate-limit (429) errors rather than failing the whole search -
        # these are usually temporary demand spikes, not something a
        # different model would avoid.
        max_retries = 5
        delay_seconds = 2
        for attempt in range(max_retries):
            try:
                response = self.gemini.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2  # Low temperature for strict factual alignment
                    ),
                )
                return response.text
            except Exception as exc:
                is_transient = any(
                    marker in str(exc)
                    for marker in ("RESOURCE_EXHAUSTED", "429", "UNAVAILABLE", "503")
                )
                if not is_transient or attempt == max_retries - 1:
                    raise
                time.sleep(delay_seconds)
                delay_seconds *= 2