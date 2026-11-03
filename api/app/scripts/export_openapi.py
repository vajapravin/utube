"""Export OpenAPI 3.1 JSON schema."""

import json

from app.main import app

if __name__ == "__main__":
    print(json.dumps(app.openapi(), indent=2))
