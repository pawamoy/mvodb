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
import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import tmdbsimple as tmdb
from guessit import guessit
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

tmdb.API_KEY = os.environ.get("TMDB_API_KEY")
LANG = {"English": "eng", "French": "fre"}


class Guess:
    def __init__(self, name):
        self.data = guessit(name)
        self.data["filename"] = name
        self.data["ext"] = name.split(".")[-1]
        self.fetch()

    def __hash__(self):
        if self.is_movie:
            return hash(("movie", self.data["title"], self.data["year"]))
        elif self.is_episode:
            return hash(("movie", self.data["title"], self.data["season"], self.data["episode"]))
        return hash("unknown")

    def __eq__(self, other):
        return hash(self) == hash(other)

    @property
    def is_episode(self):
        return self.data["type"] == "episode"

    @property
    def is_movie(self):
        return self.data["type"] == "movie"

    def fetch(self):
        if self.data["ext"] == "srt":
            try:
                self.data["lang"] = self.data["subtitle_language"].alpha3
            except (KeyError, AttributeError):
                with open(self.data["filename"]) as stream:
                    text = stream.read()
                if text:
                    try:
                        self.data["lang"] = detect(text)
                    except LangDetectException:
                        pass
        if self.is_episode:
            self.data["matches"] = get_episode_matches(self.data["title"], self.data["season"], self.data["episode"])
        elif self.is_movie:
            self.data["matches"] = get_movie_matches(self.data["title"])
        raise ValueError

    def get_new_path(self, match_index=0):
        if self.is_episode:
            return episode_to_path(self.data)
        elif self.is_movie:
            return movie_to_path(self.data)
        raise ValueError


@lru_cache()
def get_episode_matches(title, season_number, episode_number):
    search = tmdb.Search()
    search.tv(query=title)
    results = []
    for tv_show in search.results[:3]:
        episode = tmdb.TV_Episodes(tv_show["id"], season_number, episode_number)
        episode.info()
        results.append({
            "tvshow": tv_show["name"],
            "season": season_number,
            "episode": episode_number,
            "title": episode.name,
        })
    return results


@lru_cache()
def get_movie_matches(title):
    search = tmdb.Search()
    search.movie(query=title)
    results = []
    for movie in search.results[:3]:
        results.append({
            "title": movie["title"],
            "year": movie["release_date"].split("-")[0],
        })
    return results


def episode_to_path(data):
    n = data["tvshow"]
    s = f"{data['season']:02}"
    e = f"{data['episode']:02}"
    t = data["title"]
    x = data["ext"]
    if "lang" in data and data["lang"]:
        x = f"{data['lang']}.{x}"
    return f"series/{n}/Season {s}/{n} - S{s}E{e} - {t}.{x}"


def movie_to_path(data):
    t = data["title"]
    y = data["year"]
    x = data["ext"]
    if "lang" in data and data["lang"]:
        x = f"{data['lang']}.{x}"
    return f"movies/{t} ({y})/{t} ({y}).{x}"


def filter_ext(files, whitelist):
    return [f for f in files if os.path.splitext(f)[1][1:].lower() in whitelist]




def get_parser() -> argparse.ArgumentParser:
    """
    Return the CLI argument parser.

    Returns:
        An argparse parser.
    """
    parser = argparse.ArgumentParser(prog="mvodb")
    parser.add_argument("files", nargs="+", metavar="FILE", help="Files to move/rename.")
    parser.add_argument(
        "-y", "--no-confirm", action="store_true", default=False, dest="no_confirm", help="Do not ask confirmation."
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
    args = parser.parse_args(args=args)

    buffer = []
    for path in args.files:
        path = Path(path)
        if path.is_dir():
            dir_files = list(path.glob("**/*"))
        else:
            dir_files = [path]

        for file in filter_ext(dir_files, ["srt", "mkv", "mp4", "avi"]):
            guess = Guess(str(file))
            new_path = "/media/mybookplex/multimedia/" + guess.get_new_path()
            buffer.append({"original": file, "new": new_path, "answer": True})

    if not args.no_confirm:
        for item in buffer:
            original, new = item["original"], item["new"]
            answer = input(f"mv '{original}' '{new}' [Yn] ")  # nosec
            if answer not in ("", "y", "Y"):
                item["answer"] = False

    for item in [i for i in buffer if i["answer"]]:
        Path(item["new"]).parent.mkdir(parents=True, exist_ok=True)
        os.rename(item["original"], item["new"])

    return 0


# for each file found
#   guess components
#   reduce components to necessary ones only
#   fetch matches online
#   put matches in cache for these components (without extension)
#   append file path, file ext and matches to a list

# if later review
#   print list as json to stdout or specified output file

# if needs confirmation
#   for each item in the list
#       for each match
#           ask user if correct
#           if yes append item file path and ext + match in other list and break

# https://stackoverflow.com/questions/53486744/
# async for each file found
#   get components
#       guess components
#       reduce components
#   async retrieve matches
#   (sort by best match, or put best match on top)
#   build review
#   async review
#       for each match
#           async
