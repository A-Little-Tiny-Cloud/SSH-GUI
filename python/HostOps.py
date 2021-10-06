'''
封装对远程主机的操作
供界面调用
'''

import os
from common import CmdID, ConfigFile, PathData, get_remote_filename, PostEvent
from transport import SSH_Wrap
from openfile import open_file
from os_win import os_ext
from task import DownloadTask, UploadTask


# 封装了远程主机的操作
class RemoteHost:
    '封装远程主机操作'

    def __init__(self):
        self.cfg = ConfigFile('config.yaml')
        self.host = None
        self.ssh = SSH_Wrap()
        self.remote_path = '/'
        self.local_path = "d:\\"
        self.path_list = []  # 记录最近n次不同的目录
        self.path_pos = -1   # 当前目录在列表中的位置
        self.path_info = {}  # 所有(访问过)目录的内容

    def get_host_list(self):
        return self.cfg.get_host_list()

    def get_path_list(self):
        return self.path_list, self.path_pos

    def get_path_data(self):
        '当前目录的数据'
        return self.path_info[self.remote_path]

    def get_current_path(self):
        '远程主机的当前目录'
        return self.remote_path

    def connect(self, idx):
        hosts = self.cfg.get_host_list()

        self.host = self.cfg.get_host_info(hosts[idx])

        self.ssh.conncet(self.host.ip, self.host.port, self.host.user, self.host.password)

        self.__open_dir(self.host.remote_path)

        self.local_path = self.host.local_path

        self.path_list.append(self.host.remote_path)
        self.path_pos = 0

    def open_line(self, idx):  # 打开某个项

        fi = self.__get_fileitem(idx)

        if fi.attri[0] == 'd':  # 当前项是目录

            self.path_set(fi.full_path())
            ds = self.get_path_data()
            PostEvent(CmdID.path_load, path=fi.full_path(), data=ds)

        else:  # 当前项是文件
            open_file(fi, self.local_path, self.ssh)

    def download(self, lines):  # 下载到本地目录

        fis = [self.__get_fileitem(idx) for idx in lines]
        task = DownloadTask(fis, self.remote_path, self.local_path, self.ssh)
        PostEvent(CmdID.new_task, task=task)

    def cut(self, lines):  # 剪切

        fis = [self.__get_fileitem(idx) for idx in lines]
        rfns = [self.host.user + '@' + self.host.ip + ":" + x.full_path() for x in fis]
        os_ext.clipboard_write(rfns, True)

    def copy(self, lines):  # 复制

        fis = [self.__get_fileitem(idx) for idx in lines]
        rfns = [self.host.user + '@' + self.host.ip + ":" + x.full_path() for x in fis]
        os_ext.clipboard_write(rfns, False)

    def paste(self):  # 粘贴文件到当前目录(远程)
        cut, remote, flist = os_ext.clipboard_read()

        if len(flist) == 0:
            return

        if remote:  # 远程 -> ?

            buf = [x.replace('@', ':').split(':') for x in flist]
            ip = buf[0][1]

            if ip != self.host.ip:  # 远程 -> 远程
                PostEvent(CmdID.report_error, msg="目前不支持不同远程主机之间传输\n\n请使用scp命令完成!")
                return

            files = [x[2] for x in buf]

            # 远程 -> 本地

            if cut:
                self.ssh.mv_files(files)

                # 刷新源目录
                path = os.path.dirname(files[0])
                flist = self.ssh.open_dir(path)
                self.path_info[path] = PathData(path, flist)

            else:
                self.ssh.cp_files(files, self.remote_path)

            PostEvent(CmdID.refresh)  # 刷新当前目录

        else:  # 本地 -> 远程

            base_path = os.path.split(flist[0])[0]

            buf = []
            for x in flist:
                fn = os.path.split(x)[-1]
                buf.append(fn)

            task = UploadTask(base_path, buf, self.remote_path, self.ssh)

            PostEvent(CmdID.new_task, task=task)

            if cut:  # 剪切,删除本地文件
                pass

    def rename(self, old_name, new_name):

        self.ssh.rename(old_name, new_name)

        # 更新缓存
        ds = self.path_info[self.remote_path]
        ds.rename(old_name, new_name)

        # 若当前行是目录,需要修改缓存记录
        rfn = get_remote_filename(old_name, self.remote_path)
        if self.path_info.get(rfn) is not None:
            ds = self.path_info.pop(rfn)
            rfn2 = get_remote_filename(new_name, self.remote_path)
            self.path_info[rfn2] = ds

    def remove(self, lines):  # 删除多个文件项(其中可能有目录)

        for i in lines:
            fi = self.__get_fileitem(i)
            self.ssh.rm_file(fi.name)

        # 更新缓存
        pd = self.path_info[self.remote_path]
        fis = pd.rm_files(lines)  # 返回删除的文件项

        for x in fis:  # 若删除的项是目录,且有记录,需要删除其记录
            if x.attri[0] != 'd':
                continue

            record = self.path_info.get(x.full_path())
            if record is not None:
                self.path_info.pop(record)

    def path_set(self, path):  # 通过编辑框设置路径,或双击打开目录
        self.__open_dir(path)
        self.__plist_append(path)

    def path_parent(self):  # 上一级目录
        path = os.path.dirname(self.remote_path)
        self.__open_dir(path)
        self.__plist_append(path)

    def path_back(self):  # 回退

        if self.path_pos > 0:
            self.path_pos -= 1
            path = self.path_list[self.path_pos]
            self.__open_dir(path)

    def path_forward(self):  # 前进
        if self.path_pos < len(self.path_list)-1:
            self.path_pos += 1
            path = self.path_list[self.path_pos]
            self.__open_dir(path)

    def path_switch(self, idx):  # 通过目录列表切换目录
        self.path_pos = idx
        path = self.path_list[self.path_pos]
        self.__open_dir(path)

    def refresh(self, path=None):  # 刷新
        if path is None:
            path = self.remote_path

        self.__open_dir(path, False)  # 刷新时不可使用缓存

    def __open_dir(self, path, use_cache=True):
        '打开一个远程目录'

        if path.endswith('/') and path != '/':
            path = path[0:-1]

        if use_cache:  # 允许使用缓存
            ds = self.path_info.get(path)
            self.ssh.set_path(path)
        else:
            ds = None

        if ds is None:
            flist = self.ssh.open_dir(path)
            self.path_info[path] = PathData(path, flist)

        self.remote_path = path

    def __plist_append(self, path):
        '新增加一个目录记录'

        if self.path_pos != len(self.path_list) - 1:  # 不是指向最后一个,截断
            self.path_list = self.path_list[0:self.path_pos+1]

        if path in self.path_list:  # 不重复记录
            self.path_list.remove(path)
            self.path_pos -= 1

        self.path_list.append(path)
        self.path_pos += 1

        if len(self.path_list) > 15:
            self.path_list = self.path_list[-15:]
            self.path_pos = len(self.path_list) - 1  # pos需对应修改

    def __get_fileitem(self, idx):
        pd = self.path_info[self.remote_path]
        fi = pd.flist[idx]
        return fi


if __name__ == "__main__":
    pass
