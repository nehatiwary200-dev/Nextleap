"""Run the web app locally."""

import uvicorn

from src.config import HOST, PORT


if __name__ == "__main__":
    uvicorn.run("src.server:app", host=HOST, port=PORT, reload=False)
