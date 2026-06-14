
import aiohttp
import logging
import asyncio

logger = logging.getLogger(__name__)


async def fox():
    """Асинхронное получение фото лисы"""
    url = "https://randomfox.ca/floof/"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('image')
                else:
                    logger.warning(f"Fox API returned status {response.status}")
                    return None
    except asyncio.TimeoutError:
        logger.error("Timeout while fetching fox picture")
        return None
    except Exception as e:
        logger.error(f"Error fetching fox picture: {e}")
        return None


