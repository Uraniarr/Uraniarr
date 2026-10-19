




import asyncio
import json

from backend.config import ConfigManager
from backend.exceptions import IndexerError
from backend.services.indexer.base_indexer import BaseIndexer


class LibService(BaseIndexer):

    def __init__(self, dwn_cfg, downloaderi_idx):
        super().__init__(dwn_cfg, downloaderi_idx)
        self.url = dwn_cfg["url"]

    async def search(self, q, cfg, audio):
        data = await self.run_cli(["search", q, "-n", "10", "--language", cfg.language], cfg)
        return data

    async def query_manual(self, book, page, cfg, audio):
        base_queries = self.build_queries(book)
        data = await self.search(base_queries[page], cfg=cfg, audio=audio)
        try:
            response = [{
                "name": f'{item["name"]} {" ".join(item["authors"])}.{item["extension"]}',
                "guid": item["id"].split("/")[-1],
                "size": item["size"],
                "download": item["id"],
                "i_idx": self.i_idx,
                "protocol": self.protocol
            } for item in data.get("books", [])]
        except KeyError as e:
            raise IndexerError(status_code=500, detail="Ran into a key error. Are we pointing to prowlarr or newznab?", exception=e)
        return { "query": base_queries[page], "nzbs": response , "pages": len(base_queries) }

    async def query_book(self, book, cfg, audio):
        raise NotImplementedError

    async def grab(self, download, cfg):
        return download

    async def run_cli(self, cmd: list, cfg: ConfigManager):
        proc = await asyncio.create_subprocess_exec(self.url, *cmd, "--json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise IndexerError(f"CLI failed ({proc.returncode}): {stderr.decode()}")
        return json.loads(stdout)

