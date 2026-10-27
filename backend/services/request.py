import logging
from pathlib import Path
from pickle import dump, load
from time import time
import os
from urllib.parse import urlencode
from backend.config import ConfigManager
import asyncio
from backend.dependencies import get_error_logger, get_logger
from backend.exceptions import ScrapeError
from contextlib import suppress
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from cloudscraper import AsyncCloudScraper

try:
    cache_dir = os.getenv("CONFIG_DIR", "/config")
    if os.getenv("DEV"):
        cache_dir = Path(os.getenv("DEV")) / cache_dir[1:]
    cache_dir = Path(cache_dir) / "cache"
except Exception as exc:
    get_logger().error(f"Failed to get cache directory")
    get_error_logger().exception(exc)
scraper = None

try: _cache = load(cache_dir.open("rb"))
except FileNotFoundError: _cache = {}
except Exception as e:
    get_logger().error(f"Failed to load cache: {e}")
    _cache = {}


async def reload_scraper(state):
    global scraper
    get_logger().debug("Reloading scraper...")
    with suppress(Exception):
        await state.browser.close()
    with suppress(Exception):
        await state.playwright.stop()
    if state.cfg_manager.playwright:
        if os.name == "nt":
            state.cfg_manager.playwright = False
            raise ScrapeError(status_code=500, detail="Playwright is not supported on Windows")
        state.playwright = await Stealth().use_async(async_playwright()).__aenter__()
        state.browser = await state.playwright.chromium.launch(headless=True)
    else:
        state.browser = await AsyncCloudScraper().__aenter__()
    scraper = state.browser


async def fetch(cfg: ConfigManager, url: str, params: dict, xhr: bool) -> dict:
    target = f"{url}?{urlencode(params)}" if params else url
    if isinstance(scraper, AsyncCloudScraper):
        get_logger().log(5, f"Using cloudscraper to GET {target}")
        response = await scraper.get(target)
        if response.status != 200:
            err = await response.text()
            if "Sicherheits-Check" in err or "verweigert" in err:
                err = "CloudFlare Error - Try to enable Playwright or try again"
                raise ScrapeError(status_code=response.status, detail=err)
        data = await response.read()
    else:
        page = await scraper.new_page()
        try:
            response = await page.goto(target, wait_until="load")
            if response is None:
                raise ScrapeError(status_code=500, detail="No response received")
            if response.status != 200:
                err = await response.text()
                if "Sicherheits-Check" in err or "verweigert" in err:
                    err = "CloudFlare Error - Try try again"
                raise ScrapeError(status_code=response.status, detail=err)
            if xhr:
                data = await response.body()  # Raw JSON bytes
            else:
                data = await page.content()
        finally:
            await page.close()
    if not data:
        raise ScrapeError(status_code=response.status_code, detail=response.text)
    return data

async def fetch_or_cached(cfg: ConfigManager, url: str, params: dict = {}, xhr: bool = True):
    key = (url, tuple(sorted(params.items())))
    now = time()
    if not cfg.skip_cache and key in _cache and now - _cache[key]["time"] < 5*24*3600:
        get_logger().log(5, f"Using cache for {url} with {params}")
        data = _cache[key]["data"]
    else:
        data = await fetch(cfg, url, params, xhr)
        _cache[key] = {"time": now, "data": data}
        dump(_cache, cache_dir.open("wb"))
    return data