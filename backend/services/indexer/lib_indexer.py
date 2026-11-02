




import asyncio
import json

from backend.config import ConfigManager
from backend.dependencies import get_language_name, get_logger, get_scorer
from backend.exceptions import IndexerError
from backend.services.indexer.base_indexer import BaseIndexer


class LibService(BaseIndexer):

    def __init__(self, dwn_cfg, downloaderi_idx):
        super().__init__(dwn_cfg, downloaderi_idx)
        self.url = dwn_cfg["url"]
        self.protocol = "direct"

    async def search(self, q, cfg, audio):
        data = await self.run_cli(["search", q, "-n", "10", "--language", get_language_name(cfg)], cfg)
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
        try:
            base_queries = self.build_queries(book)
            for q in base_queries: #TODO
                data = await self.search(q, cfg=cfg, audio=audio)
                if len(data) == 0: continue
                for item in data:
                    ratio = get_scorer()(book.name, item["name"])
                    get_logger().log(5, f"Testing {item['name']} == {book.name}. {ratio=}")
                    if ratio > cfg.name_ratio: break
                else:
                    continue
                break
            else:
                get_logger().info(f"Could not find a match for {book.name}, try raising your name ratio in the settings.")
                return None, None, None, None
            name = item["name"]
            guid = item["id"].split("/")[-1]
            download = item["id"]
        except KeyError as e:
            raise IndexerError(status_code=500, detail="Ran into a key error. Are we pointing to prowlarr or newznab?", exception=e)
        return name, guid, download, item["protocol"]

    async def grab(self, download, cfg):
        return download

    async def run_cli(self, cmd: list, cfg: ConfigManager):
        proc = await asyncio.create_subprocess_exec(self.url, *cmd, "--json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise IndexerError(500, f"CLI failed ({proc.returncode}): {stderr.decode()}")
        return json.loads(stdout)

    async def test(self, cfg):
        proc = await asyncio.create_subprocess_exec("command", "-v", self.url)
        if not proc.returncode == 0:
            raise IndexerError("Could not connect to Indexer.")
        return True


