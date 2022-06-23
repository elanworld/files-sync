import json
import os
import shutil
import sys
import typing

from common import python_box


class FileSyncClient:
    str_new = "new"
    str_del = "del"

    def __init__(self, directory1, directory2):

        self.sync_dir1 = directory1
        self.sync_dir2 = directory2
        self.save_file = "file_info.json"

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
        return {k: self._get_file_info(os.path.join(directory, k)) for k in dir_list}

    def _get_file_info(self, file, left: bool = None):
        if left is True:
            return os.path.getmtime(os.path.join(self.sync_dir1, file))
        elif left is False:
            return os.path.getmtime(os.path.join(self.sync_dir1, file))
        return os.path.getmtime(file)

    def get_added_file(self, old_state: dict, new_state: dict):
        new_files = []
        for file in new_state:
            if file in old_state.keys():
                m_time = old_state.get(file)
                if new_state[file] > m_time:
                    new_files.append(file)
            else:
                new_files.append(file)
        return new_files

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

    def compare_new(self, files1, files2):
        new1 = []
        new2 = []
        for file in files1:
            if file in files2:
                if self._get_file_info(file, True) > self._get_file_info(file, False):
                    new1.append(file)
            else:
                new1.append(file)
        for file in files2:
            if file in files1:
                if self._get_file_info(file, False) > self._get_file_info(file, True):
                    new2.append(file)
            else:
                new2.append(file)
        return (new1, new2)

    def save_info(self, info):
        with open(self.save_file, "w") as f:
            json.dump(info, f)

    def load_info(self):
        return json.load(open(self.save_file)) if os.path.exists(self.save_file) else {}

    def copy_file(self, file_name, to_right: bool):
        print(f"copy {file_name} to {'right' if to_right else 'left'}")
        left = os.path.join(self.sync_dir1, file_name)
        right = os.path.join(self.sync_dir2, file_name)
        if to_right:
            if os.path.exists(right):
                os.remove(right)
            shutil.copy2(left, right)
            return right
        else:
            if os.path.exists(left):
                os.remove(left)
            shutil.copy2(right, left)
            return left

    def del_file(self, file_name, left=None):
        print(f"del {file_name} {'at left' if left is True else 'at right' if left is False  else ''}")
        if left is None:
            os.remove(file_name)
        elif left:
            os.remove(os.path.join(self.sync_dir1, file_name))
        else:
            os.remove(os.path.join(self.sync_dir2, file_name))


if __name__ == '__main__':
    client = FileSyncClient(sys.argv[1], sys.argv[2])
    client.run()
    print("done")
