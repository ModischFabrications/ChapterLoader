#! python3.6

# urls:
# xxx.fm
# xxx.001   [++]
# xxx.bm

# U:\PDF
# 9783446453005

# Caution: Seems to cause HANSER-eLibrary to block your IP if used excessively

# TODO
# --Generic:
# find out why Hanser blocks while having human-like access structure
#
# --Funktional:
# improve error handling with special cases
#
# replace pdfrw with functionality from PyPDF2 to limit requirements
# check header of file to validate PDF (fixes "Login to download" bug)
# http://www.easymetadata.com/2014/11/fun-with-python-extracting-pdf-metadata/
#
# check inputs
# format input paths to allow trailing "\"
#
# --Refactoring:
#  better constants?
#

# Known Bugs:
#
# occasionally the connection is refused without being blocked
# downloading without eduroam loads HTML with "Login to download"
# get(pdf) can cause a timeout with large documents -> temp fix: t = 30
# 

# Python Packages
import pathlib  # used to join paths independent of OS (not used) and make directories
import shutil
import tempfile
from timeit import default_timer as timer  # used to time individual segments

# External Packages
import requests  # web requests
import urllib3
from PyPDF2 import PdfFileMerger, utils  # merge pdfs
from pdfrw import PdfReader     # used to determine title from intro

# ------- CONSTANTS ---------

source_url = "http://www.hanser-elibrary.com/doi/pdf/10.3139/"
max_chapters = 999  # syntactic end due to 3-digit url

headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) \
Chrome/53.0.2785.143 Safari/537.36'}
timeout = 30  # seems to only get a response with the whole pdf, extend timeout accordingly


# ---------- FUNCTIONS --------

def load_file(url, file_name, history=None):
    """"loads individual generic PDFs from a url to a local file. Can be appended to a download-history."""

    # TODO: Fake header to obscure access
    r = requests.get(url, timeout=timeout)  # "stream=True" possible to prevent memory hogging

    if r.status_code != 200:
        print("Error Code {}, file {} not loaded".format(r.status_code, file_name))
        r.close()
        if r.status_code == 404:
            raise FileNotFoundError()

        if r.status_code == 403:
            raise ConnectionRefusedError()

    with open(file_name, 'wb+') as f:
        f.write(r.content)
        # f.close()  # clean up managed by "with"
        if history is not None:
            history.append(file_name)

    r.close()


# end


def load_book(book_id, path, history):
    """starts downloading the provided book. """

    print("Downloading book with ID {}\ninto folder {} ...".format(book_id, path))
    book_url = source_url + book_id
    # try intro (.fm), if not cancel
    print("Loading Intro")
    url = book_url + '.fm'
    try:
        load_file(url, path + 'intro.pdf', history)

    except FileNotFoundError:
        print("Can't load Intro, URL wrong?\nURL: {}".format(url))
        raise

    # extract title from intro to name final document
    title = str(PdfReader(path + 'intro.pdf').Info.Title)
    title = title.strip('()')   # cut off Brackets surrounding titles
    print("Extracted Title: " + title)
    
    # load numbers until 404
    print("Successful, now loading all possible Chapters")
    for i in range(1, max_chapters):  # do until error -> "for" nur als timeout
        chapter = str(i).rjust(3, '0')  # 007

        print("Loading Chapter: " + chapter)

        url = book_url + "." + chapter  # http:// ... /0123123.007
        try:
            load_file(url, path + chapter + '.pdf', history)  # U:\PDF\007.pdf

        except FileNotFoundError:
            print("End of Chapters found.")
            break

    # load outro (.bm)
    print("Loading Outro")
    url = book_url + '.bm'

    try:
        load_file(url, path + 'outro.pdf', history)

    except FileNotFoundError:
        print("Can't load Outro, that's a weird one.")
    except:
        print("Loading Outro failed")
        raise

    return title

def bind(file_list, target_file):
    """binds multiple pdf segments into one big pdf."""

    print("Binding to " + target_file)
    merger = PdfFileMerger()

    for pdf in file_list:
        merger.append(pdf)

    merger.write(target_file)
    merger.close()


# -- MAIN --

def main():
    """main program, used because zero-indentation is stupid"""

    print("\nWelcome to ChapterLoader, usage is at own risk.\n \
    Don't try to challenge it, it is challenged enough on it's own.\n\n")
    print("If this tool stops working, chances are you have been blocked by Hanser")

    # if you load into different folders, you only have yourself to blame
    folder = input("Insert folder to load PDFs into:\n>U:\\ChapterLoader<\n> ")

    while True:  # broken through "exit()"

        book_id = input("Insert Book-ID:\n>.../book/10.3139/XXXXXX<\n> ")

        if folder == "" or book_id == "":
            print("well if you don't want to play, I won't play either!")
            return

        temp_path = tempfile.gettempdir()  # used to speed up binding & make cleanup easier

        path = temp_path + "\\" + book_id + "\\"
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)  # temporary work dir

        pathlib.Path(folder + "\\").mkdir(parents=True, exist_ok=True)  # final target folder

        t_start = timer()
        history = []

        print("Starting download...")

        title = load_book(book_id, path, history)

        t_download = timer()
        print("...Download done, time: {} sec".format(t_download - t_start))

        # bind PDFs to book
        print("Starting to bind chapter PDFs to one book...")

        bind_target = temp_path + "\\" + book_id + ".pdf"
        bind(history, bind_target)

        t_binding = timer()
        print("...Binding done, time: {} sec".format(t_binding - t_download))

        # finishing
        print("Cleaning up...")

        # TODO: Delete tmp

        # copy to destination folder
        target_file = folder + "\\" + title + ".pdf"
        print("Moving {} to {}".format(bind_target, target_file))
        shutil.move(bind_target, target_file)  # can't make dir

        t_finishing = timer()
        print("...Cleanup done, time: {} sec".format(t_finishing - t_binding))

        print("All done, overall time: {} sec".format(t_binding - t_start))

    # end of repeatition here


# end of main

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
        print("An Error occured during binding of the book:" + str(e))
