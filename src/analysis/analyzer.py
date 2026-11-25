import os
from typing import List
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

        # Call Gemini 2.5 Flash for fast synthesis
        response = self.gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2  # Low temperature for strict factual alignment
            )
        )
        return response.text