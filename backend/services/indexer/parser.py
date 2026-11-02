from backend.services.indexer.base_indexer import BaseIndexer
from backend.services.indexer.lib_indexer import LibService
from backend.services.indexer.newznab_service import NewznabService
from backend.services.indexer.prowlarr_service import ProwlarrService


def create_indexer(indexer, index, audio=False) -> BaseIndexer:
    match indexer["type"]:
        case "newznab":
            return NewznabService(indexer, index)
        case "prowlarr":
            return ProwlarrService(indexer, index)
        case "lib":
            if audio:
                raise ValueError("Indexer of type lib doesn't support audiobooks")
            return LibService(indexer, index)
        case _:
            raise ValueError(f"Unknown indexer type: {indexer['type']}")


def indexer_factory(cfg):
    r = {False: [], True: []}

    for indexer in cfg.indexers:
        for audio in (False, True):
            if not indexer.get("audio" if audio else "book"):
                continue

            instance = create_indexer(indexer, len(r[audio]), audio)
            r[audio].append(instance)

    return r