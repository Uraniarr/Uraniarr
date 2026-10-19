
import json
import os
from pathlib import Path
from tempfile import mkdtemp
from uuid import uuid4

from backend.config import ConfigManager
from backend.dependencies import get_logger
from backend.services.downloader.base_downloader import BaseDownloader
import asyncio


class LibDownloader(BaseDownloader):

    def __init__(self, dwn_cfg, downloaderi_idx):
        super().__init__(dwn_cfg, downloaderi_idx)
        self.url = dwn_cfg["url"]
        self.supported_protocols = ["direct"]

    async def test(self, cfg):
        proc = await asyncio.create_subprocess_exec("command", "-v", self.url)
        return proc.returncode == 0

    async def download(self, nzb, cfg, nzbname):
        tmp = mkdtemp(dir=cfg.lib_downloader_path)
        await self.run_cli(["download", nzb, "--dir", tmp], cfg)
        files = list(Path(tmp).iterdir())
        if len(files) != 1:
            raise RuntimeError("Expected exactly one downloaded file")
        nzo_id = f"lib_{uuid4().hex[:5]}"
        with Path(cfg.config_dir/"lib_downloader.hist").open("a") as f:
            f.write(f"{nzo_id},{nzb},{nzbname},{files[0]}\n")
        return [nzo_id]


    async def get_history(self, cfg):
        txt: str = Path(cfg.config_dir/"lib_downloader.hist").read_text()
        data = [f.split(",") for f in txt.splitlines()]
        r = {_id : {
            "percentage": 100,
            "name": name,
            "status": "Completed",
            "storage": storage
        } for _id, _hash, name, storage in data}
        return r

    async def remove_from_history(self, cfg, nzo_id):
        txt: str = Path(cfg.config_dir/"lib_downloader.hist").read_text()
        data = [f.split(",") for f in txt.splitlines()]
        removed = ""
        for f in data:
            if f[0] == nzo_id: continue
            removed += f"{','.join(f)}\n"
        Path(cfg.config_dir/"lib_downloader.hist").write_text(removed)
        return nzo_id

    async def remove_from_queue(self, cfg, nzo_id):
        return nzo_id

    async def get_queue(self, cfg):
        return {}

    async def get_cat_dir(self, cfg):
        return "/"

    async def run_cli(self, cmd: list, cfg: ConfigManager):
        proc = await asyncio.create_subprocess_exec(self.url, *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(
                f"CLI failed ({proc.returncode}): {stderr.decode()}"
            )

        if stdout: get_logger().debug(stdout.decode())
        if stderr: get_logger().error(stderr.decode())
