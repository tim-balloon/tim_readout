# ============================================================================ #
# clean_io.py
# Provides functionality to clean files.
# James Burgoyne jburgoyne@phas.ubc.ca 
# CCAT Prime 2025
# ============================================================================ #


import os
import re
import datetime

try: from config import board as cfg_b
except ImportError: cfg_b = None  

import base_io
import alcove_commands.board_io as board_io
import queen_commands.control_io as control_io




# ============================================================================ #
# _datetimeOfFile
def _dateFromFilename(file_path):
    """Extracts a datetime object from a filename in expected base_io format.

    filepath (str): The path to the file.

    Returns: datetime or None.
    """

    # timestamp extraction should be centralized to base_io
    match = re.search(r"_(\d{8}T\d{6}Z)\.", os.path.basename(file_path))
    if match:
        datetime_str = match.group(1)
        try: # to make into datetime object and return
            return datetime.strptime(datetime_str, "%Y%m%dT%H%M%SZ")
        except ValueError: pass

    return None


# ============================================================================ #
# _getFileDate
def _getFileDate(file_path):
    """Get the date of a file.

    filepath (str): The path to the file.
    
    Notes:
        Will try to get from filename in standard format first,
        otherwise will use ctime of file.
        Note that ctime might mean creation or modified time.
    """

    # try to get date from filename
    date = _dateFromFilename(file_path)

    # otherwise get from ctime
    if date is None:
        date = datetime.datetime.fromtimestamp(os.path.getctime(file_path))

    return date


# ============================================================================ #
# _isFileOlderThanDate
def _isFileOlderThanDate(file_path, older_than_date):
    """Check if file is older than given date.
    
    file_path: (str) File path.
    olderThanDate: (str) YYYY-mm-dd.
    """

    delete_date = datetime.datetime.strptime(older_than_date, "%Y-%m-%d")

    return (_getFileDate(file_path) < delete_date)



# ============================================================================ #
# _isFileOlderThanDaysAgo
def _isFileOlderThanDaysAgo(file_path, older_than_days_ago):
    """Check if file ctime is older than some number of days ago.

    file_path: (str) File path.
    olderThanDaysAgo: (int) Number of days.
    """

    delta = datetime.timedelta(days=int(older_than_days_ago))
    current_time = datetime.datetime.now()

    return ((current_time - _getFileDate(file_path)) > delta)


# ============================================================================ #
# _isFilelargerThanMB
def _isFilelargerThanMB(file_path, larger_than_MB):
    """Check if file size is larger than some given size.

    file_path: (str) File path.
    largerThanMB: (int) The file size in MB.
    """

    file_size = os.path.getsize(file_path)/(1024*1024) # MB

    return (file_size > float(larger_than_MB))


# ============================================================================ #
# _shouldDel
def _shouldDel(
        file_path, ftype, olderThanDate, olderThanDaysAgo, largerThanMB):
    """Should file be deleted based on criteria.

    This function checks if a given file meets the deletion criteria based on
    its file type, modification date, age in days, and size. 
    Any or all of these criteria can be specified.

    file_path: (str) File path.
    See _cleanDir(...) for other argument descriptions.

    Returns: bool
    """

    # Check extension
    if ftype and os.path.splitext(file_path)[1] != ftype:
        return False
    
    # Check date
    if olderThanDate and not _isFileOlderThanDate(file_path, olderThanDate):
        return False

    # Check days ago
    if olderThanDaysAgo and not _isFileOlderThanDaysAgo(file_path, olderThanDaysAgo):
        return False

    # Check size
    if largerThanMB and not _isFilelargerThanMB(file_path, largerThanMB):
        return False
    
    return True


# ============================================================================ #
# _filesFromWalk
def _filesFromWalk(
        dname, ftype, olderThanDate, olderThanDaysAgo, largerThanMB):
    """Finds files within a directory that meet specified deletion criteria.

    This function traverses a directory tree and identifies files that should 
    be deleted based on their file type, modification date, age in days, and 
    size.

    See _cleanDir(...) for argument descriptions.

    Returns: list[str]: File paths that meet the specified criteria.
    """

    file_matches = []
    for root, _, files in os.walk(dname):
        for file in files:
            file_path = os.path.join(root, file)
            if _shouldDel(file_path, ftype,  
                    olderThanDate, olderThanDaysAgo, largerThanMB):
                file_matches.append(file_path)

    return file_matches


# ============================================================================ #
# _cleanDir
def _cleanDir(
        dname, ftype='.npy', testing=True, ignore_list=[],
        olderThanDate=None, olderThanDaysAgo=None, largerThanMB=None):
    """Delete files in given dir (andd subdirs) which match all filters.

    ftype: (str) 
        File extension to match.
    olderThanDate: (str) 
        Filter: Match files older than YYYY-mm-dd date.
    olderThanDaysAgo: (int) 
        Filter: Match files older than this number days ago.
    largerThanMB: (int) 
        Filter: Match files larger than this in MB.
    testing: (bool) 
        Whether to actually delete files or not.
    ignore_list: (list[str])
        list of filenames to ignore.

    Notes:
        Filters are AND joined.
    """

    # initial message
    print(f"=== Cleaning {dname} ===")
    if testing:
        print("\tTESTING! Run with parameter testing=False to delete.")

    # walk dir to find files to delete
    try:
        file_paths_to_del = _filesFromWalk(dname, ftype,  
            olderThanDate, olderThanDaysAgo, largerThanMB)
    except Exception as e:
        print(f"\tAn error occurred: {str(e)}")
        return

    # remove ignore list files
    if ignore_list and len(ignore_list) > 0:
        print(f"\tOmitting most recent file versions.")
        file_paths_to_del = [
            f for f in file_paths_to_del if f not in ignore_list]

    # iterate through files (and delete)
    fcnt = len(file_paths_to_del)
    print(f"\t{fcnt} files to be deleted...")
    for file_path in file_paths_to_del:
        print(f"\t{file_path}")
        if not testing:
            os.remove(file_path) 

    print("=== Cleaning completed. ===")


# ============================================================================ #
# _boardMostRecentFilePathList
def _boardMostRecentFilePathList():
    '''Get a list of most recent board_io file paths (list[str]).
    '''

    for f in board_io.file.fileList():
        print(f)
        print(base_io.mostRecentPath(f) )

    return [
        base_io.mostRecentPath(file) 
        for file in board_io.file.fileList()
        ]




# ============================================================================ #
# == COMMANDS ==
# ============================================================================ #


# ============================================================================ #
# cleanQueenTmpDir
def cleanQueenTmpDir(**kwargs):
    """Delete files in tmp dir.

    See cleanDir(...) for argument descriptions.
    """

    _cleanDir("../src/tmp/", **kwargs)


# ============================================================================ #
# cleanBoardDroneDirs
def cleanBoardDroneDirs(leave_latest=True, **kwargs):
    """Delete files in drones dir.
    
    leave_latest: (bool)
        Whether to leave the most recent version of known files (in board_io).

    See cleanDir(...) for argument descriptions.
    """

    # build the file ignore list if leave_latest is true
    ignore_list = _boardMostRecentFilePathList() if leave_latest else []

    _cleanDir("../drones/", ftype=".npy", ignore_list=ignore_list, **kwargs)