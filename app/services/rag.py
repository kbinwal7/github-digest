from app.core.config import Settings

class ContributionRAGEngine:
    def __init__(self, settings: Settings):
        if not settings.gemini_api_key: raise RuntimeError("GEMINI_API_KEY is not configured.")
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("Install google-genai to enable AI recommendations.") from exc
        self.client=genai.Client(api_key=settings.gemini_api_key)
        self.model=settings.gemini_generation_model

    def generate_recommendation(self, query: str, points: list) -> str:
        from google.genai import types
        if not points:return "No matching open-source contribution opportunities found."
        blocks=[]
        for i,point in enumerate(points,1):
            p=point.payload or {}
            blocks.append(f"ISSUE {i}\nRepository: {p.get('repo')}\nTitle: {p.get('title')}\nURL: {p.get('url')}\nLabels: {', '.join(p.get('labels',[]))}\nContent: {p.get('text','')}")
        prompt=("You are an open-source contribution guide. Use ONLY the issue context below. "
                "Do not invent repository files, setup steps, or URLs. If a first step is not supported, "
                "say what information is missing. Return concise Markdown with a recommendation, "
                "why it matches, a practical first step, and the source issue URL.\n\n"
                f"Developer intent: {query}\n\nRetrieved context:\n" + "\n\n".join(blocks))
        response=self.client.models.generate_content(model=self.model,contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2))
        return response.text or "The model returned an empty recommendation."
