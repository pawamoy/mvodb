# Why does this file exist, and why not put this in `__main__`?
#
# You might be tempted to import things from `__main__` later,
# but that will cause problems: the code will get executed twice:
#
# - When you run `python -m mvodb` python will execute
#   `__main__.py` as a script. That means there won't be any
#   `mvodb.__main__` in `sys.modules`.
# - When you import `__main__` it will get executed again (as a module) because
#   there's no `mvodb.__main__` in `sys.modules`.

"""Module that contains the command line application."""

import argparse
import asyncio
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import aiofiles
import httpx
from guessit import guessit
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from loguru import logger

TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
TMDB_API_BASE_URL = "https://api.themoviedb.org/3"
LANGUAGES = {"English": "eng", "French": "fre"}
MVODB_DEST_DIR = Path(os.environ.get("MVODB_DEST_DIR", "."))
EXTENSION_LIST = ["srt", "mkv", "mp4", "avi"]
PLEX_MOVIE_PREFIX = os.environ.get("MVODB_PLEX_MOVIE_PREFIX", "")
PLEX_TVSHOW_PREFIX = os.environ.get("MVODB_PLEX_TVSHOW_PREFIX", "")

logger.disable("mvodb")


def enable_logger(sink=sys.stderr, level="WARNING"):
    """
    Enable the logging of messages.

    Configure the `logger` variable imported from `loguru`.

    Arguments:
        sink: An opened file pointer, or stream handler. Default to standard error.
        level: The log level to use. Possible values are TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL.
            Default to WARNING.
    """
    logger.remove()
    logger.configure(handlers=[{"sink": sink, "level": level}])
    logger.enable("mvodb")


class MismatchError(Exception):
    ...


class ReviewMethods(Enum):
    cli: str = "cli"
    delayed: str = "delayed"


async def ainput(prompt: str = "") -> str:
    with ThreadPoolExecutor(1, "ainput") as executor:
        return await asyncio.get_event_loop().run_in_executor(executor, input, prompt)


async def detect_subtitles_language(file_path):
    async with aiofiles.open(str(file_path)) as fp:
        text = await fp.read()
    try:
        return detect(text)
    except LangDetectException:
        return None


@dataclass
class MovieFile:
    file_name: str
    file_extension: str
    title: str
    year: str
    subtitle_language: Optional[str] = None

    def __hash__(self) -> int:
        return hash((self.title, self.year))

    async def find_candidates(self):
        return await get_movie_candidates(self)


@dataclass
class MovieCandidate:
    title: str
    year: str
    file: MovieFile

    # @lru_cache()
    def format_plex(self, prefix=PLEX_MOVIE_PREFIX):
        title = self.title
        year = self.year
        extension = self.file.file_extension
        if self.file.subtitle_language:
            extension = f"{self.file.subtitle_language}.{extension}"
        return Path(prefix, f"{title} ({year})", f"{title} ({year}).{extension}")


@dataclass
class EpisodeFile:
    file_name: str
    file_extension: str
    tvshow: str
    season: str
    episode: str
    subtitle_language: Optional[str] = None

    def __hash__(self) -> int:
        return hash((self.tvshow, self.season, self.episode))

    async def find_candidates(self):
        return await get_episode_candidates(self)


@dataclass
class EpisodeCandidate:
    tvshow: str
    season: str
    episode: str
    title: str
    file: EpisodeFile

    # @lru_cache()
    def format_plex(self, prefix=PLEX_TVSHOW_PREFIX):
        tvshow = self.tvshow
        season = f"{self.season:02}"
        episode = f"{self.episode:02}"
        title = self.title
        extension = self.file.file_extension
        if self.file.subtitle_language:
            extension = f"{self.file.subtitle_language}.{extension}"
        return Path(prefix, tvshow, f"Season {season}", f"{tvshow} - S{season}E{episode} - {title}.{extension}")


async def build_file(file_name):
    guessed = guessit(file_name)
    logger.debug("\n".join(f"{key}: {value}" for key, value in guessed.items()))
    file_info = {"file_name": file_name, "file_extension": os.path.splitext(file_name)[1][1:]}

    if file_info["file_extension"] == "srt":
        try:
            file_info["subtitle_language"] = guessed["subtitle_language"].alpha3
        except (KeyError, AttributeError):
            file_info["subtitle_language"] = await detect_subtitles_language(file_name)

    if guessed["type"] == "movie":
        kept_keys = {"title", "year"}
        try:
            info = {key: str(guessed[key]) for key in kept_keys}
        except KeyError as error:
            raise MismatchError(f"Probable mismatch for {file_name}: {error}")
        return MovieFile(**file_info, **info)

    kept_keys = {"title", "season", "episode"}
    try:
        info = {"tvshow" if key == "title" else key: str(guessed[key]) for key in kept_keys}
    except KeyError as error:
        raise MismatchError(f"Probable mismatch for {file_name}: {error}")
    return EpisodeFile(**file_info, **info)


@lru_cache()
async def get_movie_candidates(movie_file):
    logger.debug("Getting movie candidates")
    async with httpx.AsyncClient(base_url=TMDB_API_BASE_URL) as client:
        logger.debug("Created async client")
        response = await client.get("/search/movie", params={"api_key": TMDB_API_KEY, "query": movie_file.title})
        logger.debug("Received response")
    logger.debug(response)
    return [
        MovieCandidate(title=candidate["title"], year=candidate.get("release_date", movie_file.year).split("-")[0], file=movie_file)
        for candidate in response.json()["results"]
    ]


@lru_cache()
async def get_episode_candidates(episode_file):
    logger.debug("Getting episode candidates")
    candidates = []
    async with httpx.AsyncClient(base_url=TMDB_API_BASE_URL) as client:
        response = await client.get("/search/tv", params={"api_key": TMDB_API_KEY, "query": episode_file.tvshow})
        logger.debug(response)
        for tv_show in response["results"].json():
            episode_url = f"/tv/{tv_show['id']}/season/{episode_file.season}/episode/{episode_file.episode}"
            episode = await client.get(episode_url, params={"api_key": TMDB_API_KEY})
            logger.debug(episode)
            try:
                episode.raise_for_status()
            except Exception:
                continue
            candidates.append(
                EpisodeCandidate(
                    tvshow=tv_show["name"],
                    season=episode_file.season,
                    episode=episode_file.episode,
                    title=episode["name"],
                    file=episode_file,
                )
            )
    return candidates


def filter_ext(files):
    return [f for f in files if os.path.splitext(f)[1][1:].lower() in EXTENSION_LIST]


async def move(source, destination, chunk_size=2 ** 20):
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(source, mode="rb") as src_fp, aiofiles.open(destination, mode="wb") as dest_fp:
        while await dest_fp.write(await src_fp.read(chunk_size)) > 0:
            ...
    return destination


async def review(file_item, candidates, method):
    if method is ReviewMethods.cli:
        candidate = candidates[0]
        answer = await ainput(f"\nMove '{candidate.file.file_name}' to '{MVODB_DEST_DIR / candidate.format_plex()}'? ")
        if answer not in ("", "y", "Y", "yes"):
            answer = await ainput(
                "\n".join(
                    [
                        f"\nMove '{candidate.file.file_name}' to '{MVODB_DEST_DIR}/...':\n",
                        *[f"  {option}) {candidate.format_plex()}" for option, candidate in enumerate(candidates)],
                        "\n  n) Do not move or rename file (skip).\n",
                        "Answer: ",
                    ]
                )
            )
            if answer == "n":
                return None
            candidate = candidates[int(answer)]
        return await move(file_item.file_name, MVODB_DEST_DIR / candidate.format_plex())


async def process_one(file_path):
    logger.debug(f"Building file object for {file_path}")
    try:
        file_item = await build_file(file_path)
    except MismatchError as error:
        logger.error(error)
        return
    candidates = await file_item.find_candidates()
    logger.debug(f"Candidates: {len(candidates)}")
    logger.debug("Reviewing candidates")
    await review(file_item, candidates, ReviewMethods.cli)


async def amain(opts: argparse.Namespace) -> int:
    """
    Run the main program.

    This function is executed when you type `mvodb` or `python -m mvodb`.

    Arguments:
        opts: Parsed options.

    Returns:
        An exit code.
    """
    all_files = []
    for path in opts.files:
        path = Path(path)
        if path.is_dir():
            all_files.extend(filter_ext(path.glob("**/*")))
        else:
            all_files.extend(filter_ext([path]))

    logger.debug(f"Files: {len(all_files)}")
    await asyncio.gather(*[process_one(file) for file in all_files])
    return 0


def get_parser() -> argparse.ArgumentParser:
    """
    Return the CLI argument parser.

    Returns:
        An argparse parser.
    """
    parser = argparse.ArgumentParser(prog="mvodb")
    parser.add_argument("files", nargs="+", metavar="FILE", help="Files to move/rename.")
    parser.add_argument(
        "-L",
        "--log-level",
        dest="log_level",
        default=None,
        help="Log level to use",
        choices=("TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"),
        type=str.upper,
    )
    parser.add_argument(
        "-P",
        "--log-path",
        dest="log_path",
        default=None,
        help="Log path to use. Can be a directory or a file.",
    )
    return parser


def main(args: Optional[List[str]] = None) -> int:
    """
    Run the main program.

    This function is executed when you type `mvodb` or `python -m mvodb`.

    Arguments:
        args: Arguments passed from the command line.

    Returns:
        An exit code.
    """
    parser = get_parser()
    opts = parser.parse_args(args=args)

    if opts.log_path:
        log_path = Path(opts.log_path)
        if log_path.is_dir():
            log_path = log_path / "mvodb-{time}.log"
        enable_logger(sink=log_path, level=opts.log_level or "WARNING")
    elif opts.log_level:
        enable_logger(sink=sys.stderr, level=opts.log_level)

    logger.debug(opts)

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(amain(opts))
