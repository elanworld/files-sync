import json
import os
import re
import shutil
import sys
import typing
import hashlib

from common import python_box


class FileSyncClient:
    str_new = "new"
    str_del = "del"
    str_garbage = ".garbage"

    def __init__(self, directory1: str, directory2: str):

        self.sync_dir1 = directory1
        self.sync_dir2 = directory2
        self.save_file = f"config/file_info_{os.path.basename(directory1)}_{hashlib.md5(self.sync_dir2.encode()).hexdigest()}.json"
        self.garbage_flag = False

    def run(self):
        origin = self.load_info()
        files1 = self.get_files_name(self.sync_dir1)
        files2 = self.get_files_name(self.sync_dir2)
        change_file1 = self.get_change_file(origin, files1)
        change_file2 = self.get_change_file(origin, files2)
        # 右边新增文件
        change_file = self.get_change_file(change_file1.get(self.str_new), change_file2.get(self.str_new))
        [self.copy_file(k, to_right=False) for k in change_file.get(self.str_new)]
        # 左边新增文件
        change_file = self.get_change_file(change_file2.get(self.str_new), change_file1.get(self.str_new))
        [self.copy_file(k, to_right=True) for k in change_file.get(self.str_new)]
        # 右边删除文件
        change_file = self.get_change_file(change_file1.get(self.str_del), change_file2.get(self.str_del))
        [self.del_file(k, left=True) for k in change_file.get(self.str_new)]
        # 左边删除文件
        change_file = self.get_change_file(change_file2.get(self.str_del), change_file1.get(self.str_del))
        [self.del_file(k, left=False) for k in change_file.get(self.str_new)]
        self.save_info(self.get_files_name(self.sync_dir1))

    def get_files_name(self, directory: str) -> dict:
        dir_list = python_box.dir_list(directory, walk=True, return_full_path=False)
        if self.garbage_flag:
            for i in range(len(dir_list) - 1, -1, -1):
                if re.search(self.str_garbage, dir_list[i]):
                    dir_list.remove(dir_list[i])
        return {k: self._get_file_info(os.path.join(directory, k)) for k in dir_list}

    def _get_file_info(self, file, left: bool = None):
        if left is True:
            return os.path.getmtime(os.path.join(self.sync_dir1, file))
        elif left is False:
            return os.path.getmtime(os.path.join(self.sync_dir1, file))
        return os.path.getmtime(file)

    def get_change_file(self, origin_state: dict, target_state: dict):
        new_files = {self.str_new: {}, self.str_del: {}}  # type: typing.Dict[str,typing.Dict[str,float]]
        for file in target_state:
            if file in origin_state.keys():
                if target_state[file] > origin_state.get(file):
                    new_files.get(self.str_new)[file] = target_state[file]
            else:
                new_files.get(self.str_new)[file] = target_state[file]
        for file in origin_state:
            if file in target_state.keys():
                pass
            else:
                new_files.get(self.str_del)[file] = origin_state[file]
        return new_files

    def save_info(self, info):
        self.log(f"save file to {self.save_file}")
        with open(self.save_file, "w") as f:
            json.dump(info, f)

    def load_info(self):
        return json.load(open(self.save_file)) if os.path.exists(self.save_file) else {}

    def copy_file(self, file_name, to_right: bool):
        self.log(f"copy {file_name} to {'right' if to_right else 'left'}")
        left = os.path.join(self.sync_dir1, file_name)
        right = os.path.join(self.sync_dir2, file_name)
        if to_right:
            if os.path.exists(right):
                os.remove(right)
            path = left
            target = right
        else:
            if os.path.exists(left):
                os.remove(left)
            path = right
            target = left
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            shutil.copy2(path, target)
        except Exception as e:
            self.log(e)
        return target

    def del_file(self, file_name, left=None):
        self.log(
            f"{'garbage' if self.garbage_flag else 'del'} {file_name} {'at left' if left is True else 'at right' if left is False else ''}")
        if left is None:
            os.remove(file_name)
        else:
            self.remove_file(file_name, left)

    def remove_file(self, file, left: bool):
        if left:
            garbage = os.path.join(self.sync_dir1, self.str_garbage)
        else:
            garbage = os.path.join(self.sync_dir2, self.str_garbage)
        path1 = os.path.join(self.sync_dir1, file)
        path2 = os.path.join(self.sync_dir2, file)
        os.makedirs(garbage, exist_ok=True) if self.garbage_flag else None
        if left:
            path = path1
        else:
            path = path2
        if self.garbage_flag:
            dst = os.path.join(garbage, os.path.dirname(file))
            os.makedirs(dst, exist_ok=True)
            shutil.move(path, dst)
        else:
            os.remove(path)

    def log(self, logs):
        python_box.log(logs, "config/sync.log")


if __name__ == '__main__':
    client = FileSyncClient(sys.argv[1], sys.argv[2])
    if "garbage" in sys.argv:
        client.garbage_flag = True
    client.run()
    client.log("done")
