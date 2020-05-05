# Hello there traveller, nice to see you here.

# Caution: Seems to cause HANSER-eLibrary to block your IP if used excessively

# TODO
# --Generic:
# find out why Hanser blocks while having human-like access structure
#
# --Funktional:
#
# replace pdfrw with functionality from PyPDF2 to limit requirements
# check header of file to validate PDF (fixes "Login to download" bug)
# http://www.easymetadata.com/2014/11/fun-with-python-extracting-pdf-metadata/
#
#
# Known Bugs:
#
# occasionally the connection is refused without being blocked
# downloading without eduroam loads HTML with "Login to download"
# get(pdf) can cause a timeout with large documents -> temp fix: t = 30
# 

import argparse
import shutil
import tempfile
from pathlib import Path  # used to join paths independent of OS (not used) and make directories
from timeit import default_timer as timer  # used to time individual segments
# External Packages
from typing import Tuple, List, Union

import requests  # web requests
import urllib3
from PyPDF2 import PdfFileMerger, utils, PdfFileReader  # merge pdfs

# ------- CONSTANTS ---------

source_url = "https://www.hanser-elibrary.com/doi/pdf/10.3139/"

headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) \
Chrome/53.0.2785.143 Safari/537.36'}
timeout = 30  # seems to only get a response with the whole pdf, extend timeout accordingly


# ---------- FUNCTIONS --------

# command line arguments
def setup_args() -> Tuple[str, Path, int]:
    # "http://www.hanser-elibrary.com/doi/pdf/10.3139/"
    parser = argparse.ArgumentParser(description='Download books from hanser e library as a combined PDF')
    parser.add_argument("-b", "--book", required=True, help="/book/10.3139/XXXXXX")
    parser.add_argument("-d", "--dir", default=Path("./books"), type=Path)
    parser.add_argument("-m", "--max_chapters", default=999, type=int)

    # read args
    args = parser.parse_args()

    if args.book == "":
        raise AttributeError("Missing URL")
    if args.dir == "":
        raise AttributeError("Missing directory")
    # 999 is syntactic end due to 3-digit url
    if args.max_chapters <= 0 or args.max_chapters > 999:
        raise AttributeError("invalid max_chapters")

    return str(args.book), Path(args.dir), int(args.max_chapters)


def load_file(url: str, file_name: Path, history: Union[List, None]):
    """"loads individual generic PDFs from a url to a local file. Can be appended to a download-history."""

    # Fake header to obscure access
    r = requests.get(url, timeout=timeout, headers=headers)  # "stream=True" possible to prevent memory hogging

    if r.status_code != 200:
        print("Error Code {}, file {} not loaded".format(r.status_code, file_name))
        r.close()
        if r.status_code == 404:
            raise FileNotFoundError()

        if r.status_code == 403:
            raise ConnectionRefusedError()

    with file_name.open('wb+') as f:
        f.write(r.content)
        # f.close()  # clean up managed by "with"
    if history is not None:
        history.append(file_name)

    r.close()


def load_book(book_id: str, path: Path, max_chapters: int, history: Union[List, None]):
    """starts downloading the provided book.  """

    print(f"Downloading book with ID {book_id}\ninto folder {path} ...")
    book_url = source_url + book_id
    # try intro (.fm), if not cancel
    print("Loading Intro")
    intro_url = book_url + '.fm?download=true'
    intro_pdf = path / 'intro.pdf'
    try:
        load_file(intro_url, intro_pdf, history)

    except FileNotFoundError:
        print(f"Can't load Intro, URL wrong?\nURL: {intro_url}")
        raise

    # extract title from intro to name final document
    with intro_pdf.open("rb") as intro:
        pdf_reader = PdfFileReader(intro)
        title = pdf_reader.documentInfo.title
    print("Extracted Title: " + title)

    # load numbers until 404
    print("Successful, now loading all possible Chapters")
    for i in range(1, max_chapters):  # do until error -> "for" nur als timeout
        chapter = str(i).rjust(3, '0')  # 007

        print(f"Loading Chapter {chapter}")

        # https://www.hanser-elibrary.com/doi/pdf/10.3139/9783446441118.001
        # https://www.hanser-elibrary.com/doi/pdf/10.3139/9783446441118.005?download=true
        chapter_url = book_url + "." + chapter + "?download=true"  # http:// ... /0123123.007
        try:
            load_file(chapter_url, path / (chapter + '.pdf'), history)  # U:\PDF\007.pdf

        except FileNotFoundError:
            print("End of Chapters found.")
            break

    # load outro (.bm)
    print("Loading Outro")
    outro_url = book_url + '.bm?download=true'

    try:
        load_file(outro_url, path / 'outro.pdf', history)

    except FileNotFoundError:
        print("Can't load Outro, that's a weird one.")
    except:
        print("Loading Outro failed")
        raise

    return title


def bind(file_list: List[Path], target_file: Path):
    """binds multiple pdf segments into one big pdf."""

    print(f"Binding chapters into {target_file}")
    merger = PdfFileMerger()

    for pdf in file_list:
        merger.append(str(pdf.resolve()))

    merger.write(str(target_file.resolve()))
    merger.close()


def get_book(book_id: str, dest_dir: Path, temp_dir: Path, max_chapters):
    t_start = timer()
    history = []

    temp_book_dir = temp_dir / book_id
    Path(temp_book_dir).mkdir(parents=True, exist_ok=True)  # temporary work dir

    print("Starting download...")
    title = load_book(book_id, temp_book_dir, max_chapters, history)
    t_download = timer()
    print("...Download done, time: {} sec".format(t_download - t_start))

    print("Starting to bind chapter PDFs into a book...")
    temp_bind_file = temp_dir / (book_id + ".pdf")
    bind(history, temp_bind_file)
    t_binding = timer()
    print(f"...Binding done, time: {t_binding - t_download} sec")

    dest_file = dest_dir / (title + ".pdf")
    print(f"Moving {temp_bind_file} to {dest_file}")
    temp_bind_file.replace(dest_file)

    print("Cleaning up...")
    shutil.rmtree(temp_book_dir)
    t_finishing = timer()
    print(f"...Cleanup done, time: {t_finishing - t_binding} sec")

    print(f"{book_id} is done, overall time: {t_binding - t_start} sec")


# -- MAIN --

def main():
    print("\nWelcome to ChapterLoader, usage is at own risk.")
    print("If this tool stops working, chances are you have been blocked by Hanser")

    book_id, folder, max_chapters = setup_args()

    # ensure that target folder exists
    Path(folder).mkdir(parents=True, exist_ok=True)

    temp_path = Path(tempfile.gettempdir())  # used to speed up binding & make cleanup easier

    get_book(book_id, folder, temp_path, max_chapters)


# ------

# start main if used independently

if __name__ == "__main__":
    try:
        main()
    except ConnectionRefusedError:
        print("You have been blocked, try in 2 hours")
    except urllib3.exceptions.ConnectTimeoutError:
        print("Connection has timed out, is your timeout too small?")
    except utils.PdfReadError as e:
        print("An Error occurred during binding of the book:" + str(e))
