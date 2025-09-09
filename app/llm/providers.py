from app.llm.gemini.live import GeminiAdapter
# from app.llm.openai.live import OpenAIAdapter  # example

PROVIDERS = {
    "gemini": GeminiAdapter,
    # "openai": OpenAIAdapter,
}

def get_adapter_cls(name: str):
    key = (name or "").lower()
    try:
        return PROVIDERS[key]
    except KeyError:
        raise RuntimeError(f"Unknown LLM_PROVIDER={name}. Known: {list(PROVIDERS)}")
