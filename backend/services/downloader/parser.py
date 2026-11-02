from backend.services.downloader.base_downloader import BaseDownloader
from backend.services.downloader.lib_downloader import LibDownloader
from backend.services.downloader.sab_service import SABDownloader

def create_downloader(downloader, index, audio=False) -> BaseDownloader:
    match downloader["type"]:
        case "sab":
            return SABDownloader(downloader, index)
        case "lib":
            if audio:
                raise ValueError("Downloader of type lib doesn't support audiobooks")
            return LibDownloader(downloader, index)
        case _:
            raise ValueError(f"Unknown downloader type: {downloader['type']}")


def downloader_factory(cfg):
    r = {False: [], True: []}

    for downloader in cfg.downloaders:
        for audio in (False, True):
            if not downloader.get("audio" if audio else "book"):
                continue

            instance = create_downloader(downloader, len(r[audio]), audio)
            r[audio].append(instance)

    return r