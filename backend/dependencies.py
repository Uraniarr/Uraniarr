import re
import httpx
import langcodes
from sqlmodel.ext.asyncio.session import AsyncSession
from backend.config import ConfigManager
from fastapi import Request
import logging
from rapidfuzz import fuzz
from backend.exceptions import IndexerError

_app_version = None

def _set_app_version(v: str):
    global _app_version
    _app_version = v

def get_app_version() -> str:
    if _app_version is None:
        raise RuntimeError("Application version has not been initialized")
    return _app_version

async def get_session(request: Request):
    async with AsyncSession(request.app.state.engine) as session:
        yield session

def get_cfg_manager(request: Request) -> ConfigManager:
    return request.app.state.cfg_manager

def get_logger() -> logging.Logger:
    return logging.getLogger('uvicorn.error')

def get_error_logger() -> logging.Logger:
    return logging.getLogger('uraniarr.err')

def get_scorer():
    def prepare(s: str) -> str:
        s = s.lower()
        s = re.sub(r"[-–—]", " ", s)       # replace dashes with spaces
        s = re.sub(r"[.:;,_!?()\"']", " ", s)  # remove or space punctuation
        s = re.sub(r"\s+", " ", s).strip() # collapse multiple spaces
        return s
    def smart_ratio(query: str, choice: str,  *args, **kwargs):
        q=prepare(query)
        c=prepare(choice)
        if len(query) < 3 or len(choice) < 3:
            return fuzz.ratio(q, c, *args, **kwargs)
        return fuzz.token_set_ratio(q, c, *args, **kwargs)

    return smart_ratio

async def get_http(url, **kwargs):
    headers = kwargs.pop("headers", {})
    headers = {"User-Agent" : f"Uraniarr/{get_app_version()}", **headers}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, **kwargs)
    except httpx.ConnectError as e:
        raise IndexerError(status_code=404, detail="Could not connect.", exception=e)
    except httpx.TimeoutException as e:
        raise IndexerError(status_code=404, detail="Timed out", exception=e)
    except Exception as e:
                raise IndexerError(status_code=404, detail="Unknown outgoing error", exception=e)
    return response

def get_language(cfg: ConfigManager) -> langcodes.Language:
    value = cfg.language.strip().lower()

    try:
        if langcodes.tag_is_valid(value):
            return langcodes.Language.get(value)
        return langcodes.find(value)
    except (LookupError, ValueError):
        return langcodes.Language.get("de")


def get_language_id(cfg: ConfigManager) -> int:
    mapping = {
        "eng": 1,
        "deu": 3,
        "fra": 2,
        "spa": 84,
        "ita": 88,
        "tur": 975,
        "por": 981,
        "fin": 985,
        "nld": 90,
        "pol": 83,
        "rus": 5,
        "ara": 982,
        "hun": 987,
        "cat": 984,
        "swe": 91,
        "hrv": 1021,
        "hin": 81,
        "ell": 980,
        "ukr": 1016,
        "vie": 976,
        "zho": 7,
    }
    return mapping.get(get_language(cfg).to_alpha3(), 3)


def get_language_name(cfg: ConfigManager) -> str:
    return get_language(cfg).display_name("en").lower()