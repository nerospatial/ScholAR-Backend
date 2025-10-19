from fastapi import FastAPI

# Create FastAPI instance at package-level
app = FastAPI(
    title="ScholAR Backend",
    version="0.1.0",
    description="Backend for ScholAR Smart Glasses AI Assistant"
)


__all__ = ["app"]
