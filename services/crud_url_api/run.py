import uvicorn
import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("CRUD_URL_HOST", "0.0.0.0"),
        port=int(os.getenv("CRUD_URL_PORT", 8000)),
        reload=True if os.getenv("ENV") == "dev" else False,
    )
