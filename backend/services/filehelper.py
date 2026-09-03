import asyncio
import logging
from pathlib import Path
import re
import shutil
from sqlmodel import func, select
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession
from backend.config import ConfigManager
from backend.datamodels import Book, Series, Author, Activity, ActivityStatus
from backend.exceptions import FileError
from backend.services.downloader import BaseDownloader
from backend.services.scrape import strip_pos
from backend.dependencies import get_error_logger, get_logger, get_scorer
import os
from rapidfuzz import process

import shutil
from pathlib import Path
from typing import Optional
import asyncio

def ensure_backup(dst_dir: Path) -> Optional[Path]:
    bak_dir = dst_dir.with_name(f".{dst_dir.name}.bak")
    if bak_dir.exists():
        shutil.rmtree(bak_dir)
    shutil.move(dst_dir, bak_dir)
    get_logger().info(f"Directory {dst_dir} already exists. Will replace.")
    return bak_dir

def compute_template(book: Book, template: str):
    attrs_used = set()
    response = list(template)
    pattern = re.compile(r"{[^{}]*?{([^{}]*?)}[^{}]*?}")
    if book.series_key:
        max_pos = max(b.position or 0 for b in book.series.books)
        padding = len(str(int(max_pos)))
    parts = template.split("/")
    domain = {"author": len(parts)-1, "series": len(parts)-1}
    for idx, s in list(enumerate(parts))[::-1]:
        if "author." not in s and idx >= domain["author"]: domain["author"] -= 1
        if "series." not in s and idx >= domain["series"]: domain["series"] -= 1
    for p in pattern.finditer(template):
        length = p.end() - p.start() -1
        alternatives = p.group(1).replace(" ", "").split("??")
        trees = [alt.split(".") for alt in alternatives]
        for tree in trees:
            if len(tree) > 3 or len(tree) < 1: raise FileError(f"Too few/many levels in template: {p.group(1)} ({len(tree)})")
            if len(tree) == 1 or tree[0] == "book":
                obj = book
            elif hasattr(book, tree[0]):
                obj = getattr(book, tree[0])
            else:
                get_logger().error(f"Template error: {tree[0]} is not a known namespace")
                obj = object()
            if obj is None or hasattr(obj, tree[-1]) and getattr(obj, tree[-1]) is None:
                sl = ""
            elif tree[0] == "series" and book.author.is_series:
                sl = ""
            elif hasattr(obj, tree[-1]):
                if getattr(obj, tree[-1]) is not None:
                    value = str(getattr(obj, tree[-1]))
                    if tree[-1] == "position" and isinstance(obj, Book):
                        if book.position % 1 != 0:
                            value = f"{str(int(book.position)).zfill(padding)}.{str(book.position).split('.')[-1]}"
                        else:
                            value=f"{str(int(book.position)).zfill(padding)}"
                sl = p.group(0)[1:-1].replace("{"+f"{p.group(1)}"+"}", value)
                attrs_used.add(tree[0])
            else:
                get_logger().debug(f"Unknown attribute: {tree[-1]}")
                sl = re.sub(r"[{}]", "", p.group(0))
            if sl: continue
        response[p.start():p.end()] = [sl] + [""] * length
    response = "".join(response)
    resp = {
        attr: "/".join(response.split("/")[:domain[attr]+1]) if attr in domain else response
        for attr in attrs_used
    }
    return Path(response), resp

def get_destination_dir(book: Book, audio: bool, cfg) -> tuple[str, Optional[str], Path]:
    template = cfg.audiobook_template if audio else cfg.book_template
    template = template or "{{author.name}}/{{series.name}}/{{book.position} - }{{book.name}}"
    path_str = cfg.audio_path if audio else cfg.book_path
    if not path_str: raise FileError(status_code=404, detail=f"{'Audio' if audio else 'Book'} path not configured but tried to import.")
    dst_base = Path(cfg.audio_path if audio else cfg.book_path)
    author_dir, series_dir, book_dst = None, None, None
    book_dst, attrs = compute_template(book, template)
    if attrs.get("author"):
        author_dir = str(dst_base/attrs.get("author"))
    if attrs.get("series"):
        series_dir = str(dst_base/attrs.get("series"))
    if book_dst:
        return author_dir, series_dir, dst_base/book_dst

def mark_overwritten_activity(book, audio: bool):
    for act in book.activities:
        if act.audio != audio:
            continue
        if act.status == ActivityStatus.imported:
            act.status = ActivityStatus.overwritten
            return act
    return None

def get_release_files(src: Path, cfg):
    files = {True: [], False: []}
    iterator = src.rglob("*") if src.is_dir() else [src]
    for f in iterator:
        if f.is_dir(): continue
        if f.suffix.lower() in cfg.audio_extensions_rating.split(","):
            files[True].append(f)
        elif f.suffix.lower() in cfg.book_extensions.split(","):
            files[False].append(f)
    return files

def move_files(files: list, dst_dir: Path, audio: bool):
    folder = dst_dir if audio else dst_dir.parent
    folder.mkdir(parents=True, exist_ok=True)
    for file in files:
        shutil.move(str(file), str(dst_dir))

def cleanup_source(src: Path, cat_dir: Path, cfg: ConfigManager, was_file: bool = False):
    get_logger().log(5, f"Cleanup called for {src}")
    if (was_file and src.parent.is_dir()
        and src.parent.resolve() != cat_dir.resolve()
        and src.parent.resolve() != Path(cfg.ingest_path or "/").resolve()
        and not list(src.parent.iterdir())):
            shutil.rmtree(src.parent)
    if not src.exists():
        return
    if src.resolve() == cat_dir.resolve():
        get_logger().info(f"The source directory is the same as the category directory. Will not delete. {src}")
        return

    shutil.rmtree(src)

def restore_backup(bak_dir: Optional[Path], dst_dir: Optional[Path]):
    try:
        if bak_dir and dst_dir:
            if dst_dir.exists():
                shutil.rmtree(dst_dir)
            shutil.move(bak_dir, dst_dir)
    except Exception as e:
        get_logger().error(f"Tried restoring {dst_dir} but failed with: {e}")

def cleanup_backup(bak_dir: Optional[Path], dst_dir: Optional[Path]):
    try:
        if bak_dir and dst_dir:
            if dst_dir.exists() and bak_dir.exists():
                shutil.rmtree(bak_dir)
    except Exception as e:
        get_logger().error(f"Final cleanup of {bak_dir} failed with: {e}")

def move_or_restore(files: list, dst_dir: Path, audio: bool):
    bak_dir = ensure_backup(dst_dir) if dst_dir.exists() else None
    try:
        move_files(files, dst_dir, audio)
        cleanup_backup(bak_dir, dst_dir)
        return True
    except Exception as e1:
        get_logger().error(f"Ran into Error while trying to import files:\n    {e1}")
        if bak_dir is None:
            return False
        try:
            shutil.rmtree(dst_dir)
            restore_backup(bak_dir, dst_dir, None)
        except Exception as e2:
            get_logger().error(f"Could not restore backup:\n    {e2}")
    return False

def prepare_destination(book: Book, audio: bool, cfg: ConfigManager):
    wanted = get_destination_dir(book, audio, cfg)
    try:
        extra = get_destination_dir(book, not audio, cfg)
    except FileError:
        extra = (None, None, None)
    return {
        "wanted": wanted,
        "extra": extra
    }

def import_book_files(destinations: dict, audio: bool, src: Path, cat_dir: Path, cfg: ConfigManager, ignore_extra: bool = True):
    was_file = src.is_file()
    files = get_release_files(src, cfg)
    wanted_files = files[audio]
    wanted_autor_dir, wanted_series_dir, wanted_dst_dir = destinations["wanted"]
    extra_autor_dir, extra_series_dir, extra_dst_dir = destinations["extra"]
    extra_valid = False
    if len(wanted_files) == 0:
        get_logger().error(f"Error importing {src}. No {'audio' if audio else 'book'} files found")
        return None #TODO signal so we dont try every X seconds
    extra_files = files[not audio]
    if not extra_dst_dir and extra_files:
        get_logger().info(f"Found a double release but {'Book' if audio else 'Audio'} path is not configured. Ignoring.")
        extra_files = []
    if not audio:
        if len(wanted_files) > 1:
            get_logger().warning(f"Found multiple book files, only 1 is supported. Taking the first of {files[False]}")
            wanted_files = wanted_files[:1]
        wanted_dst_dir = wanted_dst_dir.with_suffix(wanted_files[0].suffix)
    else:
        if extra_files:
            if len(extra_files) > 1:
                get_logger().warning(f"Found multiple book files, only 1 is supported. Taking the first of {files[False]}")
                extra_files = extra_files[:1]
            extra_dst_dir = extra_dst_dir.with_suffix(extra_files[0].suffix)
    wanted_valid = move_or_restore(wanted_files, wanted_dst_dir, audio)
    if extra_files and not ignore_extra:
        extra_valid = move_or_restore(extra_files, extra_dst_dir, not audio)
    cleanup_source(src, cat_dir, was_file)
    return {
        audio: {"valid": wanted_valid, "author_dir": wanted_autor_dir, "series_dir": wanted_series_dir, "dst_dir": wanted_dst_dir},
        not audio: {"valid": extra_valid, "author_dir": extra_autor_dir, "series_dir": extra_series_dir, "dst_dir": extra_dst_dir}
    }

def preview_retag(book: Book, cfg: ConfigManager):
    prv = {
        "book": book.key,
        "name": book.name,
        "retag": {
            "old_audio": None,
            "old_book": None,
            "new_audio": None,
            "new_book": None,
            "author_audio": None,
            "series_audio": None,
            "author_book": None,
            "series_book": None
        }
    }
    if book.a_dl_loc:
        prv["retag"]["old_audio"] = book.a_dl_loc
        old = Path(book.a_dl_loc).resolve()
        author, series, new = get_destination_dir(book, True, cfg)
        prv["retag"]["author_audio"] = author
        prv["retag"]["series_audio"] = series
        new = new.resolve()
        get_logger().log(5, f"{old} == {new}: {old == new}")
        if old != new:
            prv["retag"]["new_audio"] = new

    if book.b_dl_loc:
        prv["retag"]["old_book"] = book.b_dl_loc
        old = Path(book.b_dl_loc).resolve()
        author, series, new = get_destination_dir(book, False, cfg)
        prv["retag"]["author_book"] = author
        prv["retag"]["series_book"] = series
        if old.is_file():
            new = new.with_suffix(old.suffix)
        new = new.resolve()
        get_logger().log(5, f"{old} == {new}: {old == new}")
        if old != new:
            prv["retag"]["new_book"] = new
    return prv

async def retag_book(book: Book, cfg: ConfigManager):
    moved = []
    prv = preview_retag(book, cfg)
    if book.a_dl_loc and prv["retag"]["new_audio"]:
        a = Path(book.a_dl_loc)
        destinations = prepare_destination(book, True, cfg)
        moved.append(asyncio.to_thread(import_book_files, destinations, True, a, a.parent, cfg, True))
    if book.b_dl_loc and prv["retag"]["new_book"]:
        b = Path(book.b_dl_loc)
        destinations = prepare_destination(book, False, cfg)
        moved.append(asyncio.to_thread(import_book_files, destinations, False, b, b.parent, cfg, True))
    r = await asyncio.gather(*moved)
    return r

async def delete_audio_book(book_id: str, session: AsyncSession):
    book = await session.get(Book, book_id)
    if not book or not book.a_dl_loc:
        raise FileError(status_code=404, detail=f"Book '{book_id}' not found or not downloaded")
    await asyncio.to_thread(shutil.rmtree, book.a_dl_loc)
    book.a_dl_loc = None
    await session.commit()

async def delete_audio_series(series_id: str, session: AsyncSession):
    series = await session.get(Series, series_id)
    if not series or not series.a_dl_loc:
        raise FileError(status_code=404, detail=f"Series '{series_id}' not found or not downloaded")
    await asyncio.to_thread(shutil.rmtree, series.a_dl_loc)
    series.a_dl_loc = None
    await session.commit()

async def delete_audio_author(author_id: str, session: AsyncSession):
    author = await session.get(Author, author_id)
    if not author or not author.a_dl_loc:
        raise FileError(status_code=404, detail=f"Author '{author_id}' not found or not downloaded")
    await asyncio.to_thread(shutil.rmtree, author.a_dl_loc)
    author.a_dl_loc = None
    await session.commit()

async def get_files_of_book(book: Book):
    p_a = await asyncio.to_thread(get_files_from_disk, book.a_dl_loc)
    p_b = [Path(book.b_dl_loc)] if book.b_dl_loc else None
    try:
        a, b = await asyncio.gather(get_file_stats(p_a), get_file_stats(p_b))
    except Exception as e:
        raise FileError(status_code=404, detail=f"Error while getting files of book '{book.name}'", exception=e)
    return {
        "audio": a,
        "book": b
    }

def get_files_from_disk(path: str | None):
    if path is None: return []
    path = Path(path)
    try:
        return sorted([p for p in path.iterdir() if p.is_file()])
    except Exception as e:
        return None

async def get_file_stats(paths: list[Path] | None):
    if paths is None: return
    coros = [asyncio.to_thread(lambda p: {"path": p, "size": p.stat().st_size}, p) for p in paths]
    return await asyncio.gather(*coros)

def check_missing_paths(model_instance, fields: list[str]):
    missing = []
    for field in fields:
        path_str = getattr(model_instance, field, None)
        if not path_str:
            continue
        try:
            if not Path(path_str).exists():
                missing.append(field)
        except Exception:
            missing.append(field)
    return missing

def get_dirs_of_ext(base_paths, exts):
    audio_dirs = set()
    paths = [p for p in base_paths if p is not None]
    get_logger().log(5, f"Trying reimport audibooks with: {paths}")
    for base_path in map(Path, paths):
        if not base_path.exists():
            continue
        for root, dirs, files in os.walk(base_path):
            # normalize extensions for comparison
            if any(Path(f).suffix.lower() in exts for f in files):
                audio_dirs.add(Path(root))
    return audio_dirs

def get_files_of_ext(base_paths, exts):
    book_dirs = set()
    paths = [p for p in base_paths if p is not None]
    get_logger().log(5, f"Trying reimport books with: {paths}")
    for base_path in map(Path, paths):
        if not base_path.exists():
            continue
        for ext in exts:
            book_dirs.update(set(base_path.rglob(f"*{ext}")))
    return book_dirs

async def scan_and_import_files(state):
    cfg = state.cfg_manager
    # downloaders: list[BaseDownloader] = state.downloaders[True] + state.downloaders[False]
    activities: list[Activity] = []
    moves = []
    dl_loc = { True: "a_dl_loc", False: "b_dl_loc" }
    nzo_to_dl: dict[str, BaseDownloader] = {}
    async with AsyncSession(state.engine) as session:
        for dl_audio, downloaders in state.downloaders.items():
            for downloader in downloaders:
                hist, cat_dir = await asyncio.gather(downloader.get_history(cfg), downloader.get_cat_dir(cfg))
                for key, slot in hist.items():
                    if not slot["status"] == "Completed": continue
                    activity = await session.get(Activity, key, options=[
                        selectinload(Activity.book).selectinload(Book.author),
                        selectinload(Activity.book).selectinload(Book.series).selectinload(Series.books),
                        selectinload(Activity.book).selectinload(Book.activities)
                    ])
                    if dl_audio != activity.audio: continue
                    nzo_to_dl[key] = downloader
                    src = Path(slot["storage"])
                    if os.getenv("DEV"):
                        src = Path(os.getenv("DEV")) / str(slot["storage"])[1:] # DEV
                    # if not activity: # move to ingst
                    if activity.status == ActivityStatus.failed: continue
                    activities.append(activity)
                    ignore_extra = bool(getattr(activity.book, dl_loc[not activity.audio]))
                    moves.append(asyncio.to_thread(import_book_files, prepare_destination(activity.book, activity.audio, cfg), activity.audio, src, Path(cat_dir), cfg, ignore_extra))

        import_data = await asyncio.gather(*moves, return_exceptions=True)
        for activity, data in zip(activities, import_data):
            if isinstance(data, Exception) or not data[activity.audio]["valid"]:
                get_logger().debug(f"Import Failed! {data} {activity.model_dump()}")
                activity.status = ActivityStatus.failed
                continue
            wanted, extra = data[activity.audio], data[not activity.audio]
            wanted_loc, extra_loc = dl_loc[activity.audio], dl_loc[not activity.audio]
            setattr(activity.book, dl_loc[activity.audio], str(wanted["dst_dir"]))
            if getattr(activity.book.author, wanted_loc) is None:
                setattr(activity.book.author, wanted_loc, wanted["author_dir"])
            if getattr(activity.book.series, wanted_loc) is None:
                setattr(activity.book.series, wanted_loc, wanted["series_dir"])
            if extra["valid"]:
                setattr(activity.book, extra_loc, str(extra["dst_dir"]))
                if getattr(activity.book.author, extra_loc) is None:
                    setattr(activity.book.author, extra_loc, extra["author_dir"])
                if getattr(activity.book.series, extra_loc) is None:
                    setattr(activity.book.series, extra_loc, extra["series_dir"])
            mark_overwritten_activity(activity.book, activity.audio)
            activity.status = ActivityStatus.imported
        await asyncio.gather(*[downloader.remove_from_history(cfg, nzo_id) for nzo_id, downloader in nzo_to_dl.items()], return_exceptions=True)
        await session.commit()

async def rescan_files(state):
    async with AsyncSession(state.engine) as session:
        targets = [
            (Book, ["a_dl_loc", "b_dl_loc"]),
            (Author, ["a_dl_loc", "b_dl_loc"]),
            (Series, ["a_dl_loc", "b_dl_loc"]),
        ]
        for model, fields in targets:
            result = await session.exec(select(model))
            instances = result.all()
            coros = [asyncio.to_thread(check_missing_paths, instance, fields) for instance in instances]
            missing_results = await asyncio.gather(*coros)

            for instance, missing_fields in zip(instances, missing_results):
                if missing_fields:
                    for f in missing_fields:
                        setattr(instance, f, None)

        query = await session.exec(select(Activity).join(Activity.book).where(Activity.status == ActivityStatus.imported, (
            (Activity.audio.is_(True) & Book.a_dl_loc.is_(None)) |
            (Activity.audio.is_(False) & Book.b_dl_loc.is_(None))
        )))
        for a in query.all():
            a.status = ActivityStatus.deleted
        await session.commit()

async def reimport_files(state):
    cfg = state.cfg_manager
    downloaders: list[BaseDownloader]= state.downloaders[True] + state.downloaders[False]
    async with AsyncSession(state.engine) as session:
        query = await session.exec(select(Book).where(Book.blocked.is_(False)).options(
            selectinload(Book.author),
            selectinload(Book.series).selectinload(Series.books),
            selectinload(Book.activities)
        ).order_by(func.length(Book.name).desc()))
        books: list[Book] = query.all()
        if len(books) == 0: return
        audio_paths = [cfg.audio_path]
        book_paths = [cfg.book_path]
        if cfg.ingest_path:
            audio_paths.append(cfg.ingest_path)
            book_paths.append(cfg.ingest_path)
        get_logger().log(5, f"Also checking reimport with: {cfg.ingest_path}")
        a_paths, b_paths = await asyncio.gather(
            asyncio.to_thread(get_dirs_of_ext, audio_paths, cfg.audio_extensions_rating.strip().split(",")),
            asyncio.to_thread(get_files_of_ext, book_paths, cfg.book_extensions.strip().split(",")),
        )

        book_names = [b.name for b in books]
        ai_idx, bi_idx = [], []
        a_fuzz_coros = [asyncio.to_thread(process.extractOne, p.name, book_names, scorer=get_scorer()) for p in a_paths]
        b_fuzz_coros = [asyncio.to_thread(process.extractOne, p.name, book_names, scorer=get_scorer()) for p in b_paths]
        a_results, b_results = await asyncio.gather(
            asyncio.gather(*a_fuzz_coros),
            asyncio.gather(*b_fuzz_coros)
        )
        ai_idx = [(p, index, score) for p, (name, score, index) in zip(a_paths, a_results) if score > 80]
        bi_idx = [(p, index, score) for p, (name, score, index) in zip(b_paths, b_results) if score > 80]
        # moved = []
        for p, idx, score in ai_idx:
            if Path(books[idx].a_dl_loc or "").resolve() == p.resolve(): continue
            get_logger().info(f"Found {books[idx].name} at {p} with {score=}")
            mark_overwritten_activity(books[idx], True)
            activity = Activity(release_title=f"_local_unknown_{books[idx].name}", book=books[idx], audio=True, status=ActivityStatus.imported)
            session.add(activity)
            # moved.append(asyncio.to_thread(move_file, activity, activity.book, activity.audio, p, cat_dir=cat_dir, cfg=cfg))
            books[idx].a_dl_loc = str(p)
        for p, idx, score in bi_idx:
            if Path(books[idx].b_dl_loc or "").resolve() == p.resolve(): continue
            get_logger().info(f"Found {books[idx].name} at {p} with {score=}")
            mark_overwritten_activity(books[idx], False)
            activity = Activity(release_title=f"_local_unknown_{books[idx].name}", book=books[idx], audio=False, status=ActivityStatus.imported)
            session.add(activity)
            # moved.append(asyncio.to_thread(move_file, activity, activity.book, activity.audio, p, cat_dir=cat_dir, cfg=cfg))
            books[idx].b_dl_loc = str(p)
        # await asyncio.gather(*moved) #TODO log
        await session.commit()