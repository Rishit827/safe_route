import asyncio
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

async def fetch_text(url: str, params=None, headers=None, attempts: int = 3) -> str:
    """Async HTTP helper with timeout and exponential retries."""
    last_error = None
    for attempt in range(attempts):
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds, follow_redirects=True) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.text
        except (httpx.HTTPError, OSError) as exc:
            last_error = exc
            logger.warning("Collector request failed (%s/%s): %s", attempt+1, attempts, exc)
            if attempt + 1 < attempts:
                await asyncio.sleep(0.4 * (2 ** attempt))
    raise RuntimeError(f"Could not fetch {url}: {last_error}")
