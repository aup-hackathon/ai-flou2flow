"""Flou2Flow — Transform fuzzy business needs into executable workflows."""

import uvicorn
from flou2flow.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "flou2flow.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
