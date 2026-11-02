from typing import Literal, Optional

from pydantic import BaseModel

class SeriesAuthor(BaseModel):
    name: str
    entry_id: str

class UnionSeries(BaseModel):
    series_id: str
    series_ids: list[str]

class ManualGUIDDownload(BaseModel):
    book_key: str
    guid: str = None
    name: str
    download: str = None
    i_idx: int
    protocol: str

class BookNzb(BaseModel):
  name: str
  guid: str
  size: str | int
  i_idx: int

class ReturnInteractiveSearch(BaseModel):
    query: str
    nzbs: list[BookNzb]

class KindleRequest(BaseModel):
    book_id: str
    kindle_idx: int = -1

class IndexerRequest(BaseModel):
    name: str
    url: str
    apikey: Optional[str]
    type: str
    book: bool
    audio: bool
    audio_categories: str
    book_categories: str
    usenet: bool
    torrent: bool


class DownloaderRequest(BaseModel):
    name: str
    url: str
    apikey: str
    type: str
    audio: bool
    book: bool
    download_categories: str
