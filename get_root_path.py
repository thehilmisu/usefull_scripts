import os
import pathlib

def get_root_path():
    """
    Get the root folder absolute path, use it as a base for all paths
    """
    return pathlib.Path(os.path.realpath(__file__)).parents[1]
