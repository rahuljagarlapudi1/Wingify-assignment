import json
from typing import Any, Optional

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

import httpx
from pydantic import BaseModel, Field

from config.settings import settings

logger = logging.getLogger(__file__)


class SerperSearchInput(BaseModel):
    """Input schema for Serper search tool."""

    query: str = Field(description="Search query")
    location: Optional[str] = Field(default="India", description="Location for search")
    gl: Optional[str] = Field(default="in", description="Country code")
    hl: Optional[str] = Field(default="en", description="Language code")
    tbs: Optional[str] = Field(
        default=None, description="Time-based search (e.g., 'qdr:w' for past week)"
    )
    page: Optional[int] = Field(default=1, description="Page number for results")


class SerperSearchTool(BaseTool):
    name: str = "serp_search"
    description: str = (
        "Search the web using Serper API with location and time-based filtering"
    )
    args_schema: type[BaseModel] = SerperSearchInput

    def __init__(self):
        super().__init__()

    def _run(self, **kwargs) -> dict[str, Any]:
        try:
            payload = {
                "q": kwargs.get("query"),
                "location": kwargs.get("location", "India"),
                "gl": kwargs.get("gl", "in"),
                "hl": kwargs.get("hl", "en"),
                "page": kwargs.get("page", 1),
                "num": 30,
            }
            if kwargs.get("tbs"):
                payload["tbs"] = kwargs["tbs"]

            headers = {
                "X-API-KEY": settings.SERPER_API_KEY,
                "Content-Type": "application/json",
            }

            base_url = "https://google.serper.dev/search"
            # THIS BLOCK IS FOR REGULATING NUMBER OF RETRIES (DEFAULT is 10)
            session = requests.Session()
            response = session.post(
                base_url, headers=headers, data=json.dumps(payload), timeout=10
            )
            response.raise_for_status()
            raw_data = response.json()
            # logger.info(f"raw results are {raw_data}")
            return raw_data

        except Exception as e:
            logger.error(f"an error {e} occurred in serp-search", exc_info=True)
