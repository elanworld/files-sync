import hashlib
import json
import os
import pathlib
import re
import shutil
import sys
import traceback
from typing import Dict, Union

from common import python_box


class FileInfo(dict):
    st_mode: int  # protection bits,
    st_ino: int  # inode number,
    st_dev: int  # device,
    st_nlink: int  # number of hard links,
    st_uid: int  # user id of owner,
    st_gid: int  # group id of owner,
    st_size: int  # size of file, in bytes,
    st_atime: float  # time of most recent access,
    st_mtime: float  # time of most recent content modification,
    st_ctime: float  # platform dependent (time of most recent metadata change on Unix, or the time of creation on Windows)
    st_atime_ns: int  # time of most recent access, in nanoseconds
    st_mtime_ns: int  # time of most recent content modification in nanoseconds
    st_ctime_ns: int  # platform dependent (time of most recent metadata change on Unix, or the time of creation on Windows) in nanoseconds
    st_path: str
    st_absolute_path: str
    st_is_file: bool
    st_left: bool

    def __init__(self, stat: Union[os.stat_result, dict]):
        if type(stat) == dict:
            for k in stat:
                self.__setattr__(k, stat.get(k))
        if type(stat) == os.stat_result:
            for s in stat.__dir__():
                if s.startswith("st"):
                    self.__setattr__(s, stat.__getattribute__(s))

    def to_dict(self) -> dict:
        value_dict = {}
        for k in self.__dict__:
            if k.startswith("st"):
                value_dict[k] = self.__getattribute__(k)
        return value_dict

    def __str__(self):
        return self.to_dict().__str__()


class FileSyncClient:
    str_new = "new"
    str_del = "del"
    str_garbage = ".garbage"
    str_temp_copy = ".temp_copy"

    def __init__(self, directory1: str, directory2: str):

        self.sync_dir1 = directory1
        self.sync_dir2 = directory2
        self.save_file = f"config/file_info_{os.path.basename(directory1)}_{hashlib.md5((self.sync_dir1 + self.sync_dir2).encode()).hexdigest()}.ini"
        self.garbage_flag = False
        # copy file to temp directory then move to target path ，avoid copy didnt finished when program be interrupted
        self.temp_copy = False

    def run(self):
        origin = self.load_saved_info()
        files1 = self.get_files_name(self.sync_dir1, True)
        files2 = self.get_files_name(self.sync_dir2, False)
        if len(files1) == 0 and len(files2) == 0:
            self.log("directory empty, exit!")
            return
        change_file = self.get_change_file(origin, files1, files2)
        new = [k for k in sorted(change_file.get(self.str_new).values(), key=lambda x: x.st_path, )]
        deleted = [k for k in sorted(change_file.get(self.str_del).values(), key=lambda x: x.st_path, reverse=True)]
        self.log(
            f"changed file: {len(new) + len(deleted)} / {len(origin)}\n"
            f"copy size: {(sum([k.st_size for k in new])) / 1024 / 1024} MB")
        [self.copy_file(k) for k in new]
        [self.del_file(k) for k in deleted]
        self.save_info(self.get_files_name(self.sync_dir1, left=True))

    def get_files_name(self, directory: str, left: bool) -> Dict[Union[str, bytes], FileInfo]:
        dir_list = {}
        for i in pathlib.Path(directory).rglob(f"*"):
            stat = i.stat()  # type: os.stat_result
            info = FileInfo(stat)
            info.st_is_file = i.is_file()
            info.st_absolute_path = i.__str__()
            file = os.path.relpath(info.st_absolute_path, directory)
            info.st_path = file
            info.st_left = left
            if (self.garbage_flag and re.match(self.str_garbage, info.st_path)) or (
                    self.temp_copy and re.match(self.str_temp_copy, info.st_path)):
                continue
            dir_list[file] = info
        return dir_list

    def get_change_file(self, origin_file: Dict[Union[str, bytes], FileInfo],
                        left_file: Dict[Union[str, bytes], FileInfo], right_file: Dict[Union[str, bytes], FileInfo]) -> \
            Dict[
                str, Dict[Union[str, bytes], FileInfo]]:
        """
        根据修改时间获取新增或者删除文件
        :param origin_file:
        :param left_file:
        :return:
        """
        new_files = {self.str_new: {}, self.str_del: {}}
        keys = []
        keys.extend(origin_file.keys())
        keys.extend(left_file.keys())
        keys.extend(right_file.keys())
        for key in keys:
            # modified
            origin = origin_file.get(key)
            left = left_file.get(key)
            right = right_file.get(key)
            if left is not None and right is not None:
                if left.st_is_file:
                    if left.st_mtime > right.st_mtime:
                        new_files.get(self.str_new)[key] = left
                        continue
                    elif right.st_mtime > left.st_mtime:
                        new_files.get(self.str_new)[key] = right
                        continue
            # added
            elif origin is None:
                new_files.get(self.str_new)[key] = left if left is not None else right
                continue
            # deleted
            if origin is not None:
                if left is not None and right is None:
                    new_files.get(self.str_del)[key] = left
                if right is not None and left is None:
                    new_files.get(self.str_del)[key] = right
        return new_files

    def save_info(self, info: Dict[Union[str, bytes], FileInfo]):
        self.log(f"save file to {self.save_file}")
        save = {}
        for k in info:
            save[k] = info.get(k).to_dict()
        with open(self.save_file, "w") as f:
            json.dump(save, f)

    def load_saved_info(self):
        """
        read files information from local save file
        :return:
        """
        jsonOb = json.load(open(self.save_file)) if os.path.exists(self.save_file) else {}
        res = {}
        for k in jsonOb:
            res[k] = FileInfo(jsonOb.get(k))
        return res

    def copy_file(self, file: FileInfo):
        self.log(
            f"copy {file.st_path if os.path.basename(self.sync_dir1) != os.path.basename(self.sync_dir2) else file.st_absolute_path} to {os.path.basename(self.sync_dir2) if file.st_left else os.path.basename(self.sync_dir1)}")
        target = os.path.join(self.sync_dir2 if file.st_left else self.sync_dir1, file.st_path)
        try:
            temp_path = self._get_temp_copy_path(file, not file.st_left)
            shutil.copy2(file.st_absolute_path,
                         temp_path if self.temp_copy else target) if file.st_is_file else os.makedirs(
                target, exist_ok=True)
            if self.temp_copy and os.path.exists(target) and os.path.isfile(target):
                shutil.move(target, self._get_temp_copy_path(file, not file.st_left))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.move(temp_path, target) if self.temp_copy else None
        except Exception as e:
            traceback.print_exception(e)
            self.log(e)
        return target

    def del_file(self, file: FileInfo):
        self.log(
            f"{'garbage' if self.garbage_flag else 'delete'} {file.st_path if os.path.basename(self.sync_dir1) != os.path.basename(self.sync_dir2) else file.st_absolute_path} at {os.path.basename(self.sync_dir1) if file.st_left else os.path.basename(self.sync_dir2)}")
        if self.garbage_flag:
            os.path.join(self.sync_dir1 if file.st_left else self.sync_dir2, self.str_garbage)
            garbage_path = self._get_garbage_path(file, file.st_left)
            garbage_dir = os.path.dirname(garbage_path)
            os.makedirs(garbage_dir, exist_ok=True)
            if os.path.exists(garbage_path):
                if os.path.isfile(garbage_path):
                    os.remove(garbage_path)
                    shutil.move(file.st_absolute_path, garbage_path)
                else:
                    os.removedirs(file.st_absolute_path)
            else:
                shutil.move(file.st_absolute_path, garbage_path)
        else:
            os.remove(file.st_absolute_path)

    def _get_garbage_path(self, file: FileInfo, left: True):
        os_path_join = os.path.join(os.path.join(self.sync_dir1 if left else self.sync_dir2, self.str_garbage),
                                    file.st_path)
        dirname = os.path.dirname(os_path_join)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        return os_path_join

    def _get_temp_copy_path(self, file: FileInfo, left: True):
        os_path_join = os.path.join(os.path.join(self.sync_dir1 if left else self.sync_dir2, self.str_temp_copy),
                                    file.st_path)
        dirname = os.path.dirname(os_path_join)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        return os_path_join

    def log(self, logs):
        python_box.log(logs, "config/sync.log")


if __name__ == '__main__':
    str_garbage = "garbage"
    dir1 = "dir1"
    dir2 = "dir2"
    config_from_file = "config from file"
    tmp_copy = "tmp_copy"
    config = python_box.read_config("config/config_fileSync.ini",
                                    {("%s" % config_from_file): "0", ("%s" % dir1): "", ("%s" % dir2): "",
                                     ("%s" % str_garbage): "0", tmp_copy: 0}, apend_default=True)
    if config is None:
        exit(0)
    if config.get(config_from_file) == 1:
        argv_1 = config.get(dir1)
        argv_2 = config.get(dir2)
    else:
        argv_1 = sys.argv[1]
        argv_2 = sys.argv[2]
    client = FileSyncClient(argv_1, argv_2)
    if config.get(config_from_file) == 1:
        client.garbage_flag = config.get(str_garbage) == 1
        client.temp_copy = config.get(tmp_copy) == 1
    else:
        client.garbage_flag = "garbage" in sys.argv
        client.temp_copy = "tmp_copy" in sys.argv
    client.log("start")
    client.run()
    client.log("done")

