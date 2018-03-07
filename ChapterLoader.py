# urls:
# xxx.fm
# xxx.001   [++]
# xxx.bm

# "9783446453005"

# Caution: Seems to cause HANSER-eLibrary to block your IP if used excessively

# TODO
#	--Funktional:	
#	else in while to signal end of chapters
#
#	--Refactoring:
# 	better constants?
#

# Python Packages
from timeit import default_timer as timer  # used to time individual segments
import pathlib  # used to join paths independent of OS (not used) and make directories
import tempfile
import shutil

# External Packages
import requests  # web requests
from PyPDF2 import PdfFileMerger  # merge pdfs

# ------- CONSTANTS ---------

source_url = "http://www.hanser-elibrary.com/doi/pdf/10.3139/"
max_chapters = 100


# ---------- FUNCTIONS --------

def load_file(url, file_name, history=None):
    """"loads individual generic PDFs from a url to a local file. Can be appended to a download-history."""

    r = requests.get(url)  # "stream=True" to prevent hogging memory

    if r.status_code != 200:
        print("Error Code {}, file {} not loaded".format(r.status_code, file_name))
        r.close()
        raise FileNotFoundError("Code" + str(r.status_code))

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
        print("Can't load Intro, URL wrong?\nURL: " + url)
        exit(404)
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
        print("Can't load Outro, you have probably been blocked")
        exit(403)


def bind(file_list, target_file):
    """binds multiple pdf segments into one big pdf. Warning: Takes ridiculously long"""

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

    folder = input("Insert folder to load PDFs into:\n>U:\\ChapterLoader<\n> ")

    while True:     # broken through "exit()"

        book_id = input("Insert Book-ID:\n>.../book/10.3139/XXXXXX<\n> ")

        if folder == "" or book_id == "":
            print("well if you don't want to play, I won't play either!")
            exit(1)

        temp_path = tempfile.gettempdir()

        path = temp_path + "\\" + book_id + "\\"
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)

        pathlib.Path(folder + "\\").mkdir(parents=True, exist_ok=True)
        
        t_start = timer()
        history = []

        print("Starting download...")

        load_book(book_id, path, history)

        t_download = timer()
        print("...Download done, time: {} sec".format(t_download - t_start))

        # bind PDFs to book
        print("Starting to bind chapter PDFs to one book...")
        # print (history)

        bind_target = temp_path + "\\" + book_id + ".pdf"  # TODO: change to temp path
        bind(history, bind_target)

        t_binding = timer()
        print("...Binding done, time: {} sec".format(t_binding - t_download))

        # finishing
        print("Cleaning up...")

        # TODO: Delete tmp

        # copy to destination folder
        target_file = folder + "\\" + book_id + ".pdf"
        print ("Moving {} to {}".format(bind_target, target_file))
        shutil.move(bind_target, target_file)       # makes dir if not existent

        t_finishing = timer()
        print("...Cleanup done, time: {} sec".format(t_finishing - t_binding))

        print("All done, overall time: {} sec".format(t_binding - t_start))

    # end of repeatition here

# end of main

# ------

# start main if used independently

if __name__ == "__main__":
    main()

