# generate from base common code
import os
import collections
import datetime
import io
import logging
import string
import threading
import time
from typing import Union, AnyStr, Optional
from typing.io import IO
import re
def dir_list(directory=None, filter_str="", return_full_path=True, walk=False, return_dir=False):
    if directory is None:
        directory = "."
    if os.path.exists(directory):
        if os.path.isfile(directory):
            return [directory]
    else:
        return []
    file_list = []
    for path, dirs, files in os.walk(directory):
        for file in files:
            if return_full_path:
                filepath = os.path.join(os.path.abspath(path), file)
            else:
                filepath = os.path.relpath(os.path.join(os.path.abspath(path), file), directory)
            file_list.append(filepath)
        if return_dir:
            for dire in dirs:
                if return_full_path:
                    filepath = os.path.join(os.path.abspath(path), dire)
                else:
                    filepath = os.path.relpath(os.path.join(os.path.abspath(path), dire), directory)
                file_list.append(filepath)
        if walk is False:
            break
    if filter_str:
        for i in range(len(file_list) - 1, -1, -1):
            if not re.search(filter_str, file_list[i]):
                file_list.remove(file_list[i])
    return file_list
def log(msg, file=None, console=True, fmt='%(asctime)s - %(levelname)s - %(message)s', flush_now=True):
    """日志打印"""
    handlers = logging.root.handlers
    if not any(h.get_name() == "base_log_handler" for h in handlers):
        # 已存在当前方法的handle
        for h in handlers:
            logging.root.removeHandler(h)
        if file:
            dirname = os.path.dirname(file)
            os.makedirs(dirname, exist_ok=True)
            file_handler = logging.FileHandler(file, mode='a', encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(fmt))
            file_handler.set_name("base_log_handler")
            logging.root.addHandler(file_handler)

        if console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(logging.Formatter(fmt))
            console_handler.set_name("base_log_handler")
            logging.root.addHandler(console_handler)
        logging.root.setLevel(logging.DEBUG)
        handlers = logging.root.handlers
    logging.info(msg)
    if flush_now:
        for h in handlers:
            h.flush()