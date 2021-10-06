'''
公用数据结构,通用函数.
本模块是其它模块基础,不可以引用工程内其它文件.
'''

import os
import uuid
import hashlib
import yaml
from enum import Enum, unique
import wx.lib.newevent


# ------------------------------------------------------------------------------
# 全局变量

g_next_cmd_id = 1
# ------------------------------------------------------------------------------


def get_cmd_id(delta=1):
    global g_next_cmd_id

    cid = g_next_cmd_id
    g_next_cmd_id += delta

    return cid


# 命令id
@unique
class CmdID(Enum):
    '''
    命令id. 可以新增, 不可以修改已有的.
    '''

    website_mgr = get_cmd_id()
    new_tab = get_cmd_id()
    close_tab = get_cmd_id()
    dir_tree = get_cmd_id()
    view_list = get_cmd_id()
    view_icon = get_cmd_id()

    disk_use = get_cmd_id()
    process = get_cmd_id()
    gpu_info = get_cmd_id()
    install = get_cmd_id()
    build = get_cmd_id()

    open = get_cmd_id()
    openfile = get_cmd_id()
    download = get_cmd_id()
    saveas = get_cmd_id()
    cut = get_cmd_id()
    copy = get_cmd_id()
    paste = get_cmd_id()
    link = get_cmd_id()
    rename_begin = get_cmd_id()
    rename_batch = get_cmd_id()
    rename_end = get_cmd_id()
    delete = get_cmd_id()
    info = get_cmd_id()
    refresh = get_cmd_id()
    new_file = get_cmd_id()
    new_folder = get_cmd_id()
    select_all = get_cmd_id()   # 全选
    select_neg = get_cmd_id()   # 反选
    report_error = get_cmd_id()

    new_task = get_cmd_id()
    task_end = get_cmd_id()

    path_load = get_cmd_id()
    path_parent = get_cmd_id()
    path_back = get_cmd_id()
    path_forward = get_cmd_id()
    path_set = get_cmd_id()

    path_list = get_cmd_id()
    path_list1 = get_cmd_id(20)  # 保留20个值, 区分不同的历史记录
    path_list2 = get_cmd_id()

    head = get_cmd_id()
    tail = get_cmd_id()

    connect = get_cmd_id()
    connect1 = get_cmd_id(50)  # 保留50个值, 区分不同的站点
    connect2 = get_cmd_id()

    view_info = get_cmd_id()

    last_id = get_cmd_id()


# 文件类型
@unique
class FileType(Enum):
    '文件类型,对应文件的功能和编辑方式'

    folder = 0        # 文件夹
    text_plain = 1    # *.txt *.log 配置文件: *.ini *.config *.bash_profile *.bash_rc
    text_struct = 2   # *.md *.yaml *.xml
    src_code = 3      # *.py *.cpp *.c *.bat  *.make
    web_page = 4      # *.htm
    doc = 5           # *.pdf *.doc *.ppt
    excut_bin = 6     # *.exe *.dll *.sys *.so
    pack = 7          # *.tar *.bz2 *.tgz ...
    image = 8         # *.jpg *.bmp *.png ...
    media = 9         # *.wav, *.avi *.mp4
    data = 10         # ...
    unknow = 200      # 未知文件


class HostInfo:
    def __init__(self, name, info):
        self.name = name
        self.ip = info['ip']
        self.port = info['port']
        self.user = info['user']
        self.password = info['password']
        self.remote_path = info['remote_path']
        self.local_path = info['local_path']


class ConfigFile:

    def __init__(self, yaml_file):

        file = open(yaml_file, 'r', encoding="utf-8-sig")
        file_data = file.read()
        file.close()

        self.host = yaml.load(file_data)

    def get_host_list(self):
        hs = list(self.host.keys())
        hs.sort()
        return hs

    def get_host_info(self, host_name):
        return HostInfo(host_name, self.host[host_name])


class FileItem:
    '文件项,一个文件或目录'

    def __init__(self, parent_path, line):

        if not parent_path.endswith('/'):
            parent_path = parent_path + '/'

        self.path = parent_path

        its = line.split()

        # 下面是line的一个例子(命令为: ls -l --time-style=long-iso)
        # -rw-rw-r--  1 lihengfeng lihengfeng       7397 2021-09-15 13:56 0001.txt
        assert len(its) == 8

        self.attri = its[0]
        self.group = its[2]
        self.owner = its[3]
        self.size = int(its[4]) if self.attri[0] != 'd' else -1
        self.date = its[5]  # 年-月-日
        self.time = its[6]  # 时:分
        self.name = its[7]

        ext = os.path.splitext(self.name)[-1]

        if self.attri[0] == 'd':
            self.ftype = FileType.folder

        elif ext in ('.txt', '.log', '.ini', '.config', '.bash_profile', '.bash_rc'):
            self.ftype = FileType.text_plain

        elif ext in ('.md', '.yaml', '.xml'):
            self.ftype = FileType.text_struct

        elif ext in ('.py', '.cpp', '.cxx', '.c', '.h', '.hpp', '.make'):
            self.ftype = FileType.src_code

        elif ext in ('.html', '.htm', '.mht'):
            self.ftype = FileType.web_page

        elif ext in ('.pdf', '.doc', '.ppt'):
            self.ftype = FileType.doc

        elif ext in ('.exe', '.dll', '.sys', '.so'):
            self.ftype = FileType.excut_bin

        elif ext in ('.tar', '.bz2', '.tgz'):
            self.ftype = FileType.pack

        elif ext in ('.jpg', '.jpeg', '.bmp', '.png', '.gif'):
            self.ftype = FileType.image

        elif ext in ('.wav', '.avi', '.mp4'):
            self.ftype = FileType.media

        else:
            self.ftype = FileType.unknow

    def change_path(self, path):
        '修改文件项所在的目录'

        if not path.endswith('/'):
            path = path + '/'

        self.path = path

    def full_path(self):
        '文件项的全路径'

        return self.path + self.name


# 目录数据
class PathData:
    '保存一个目录的数据,包括内部的所有文件项'

    def __init__(self, full_path, flist):

        self.path = full_path
        self.flist = []
        for x in flist:

            fi = FileItem(full_path, x)

            if fi.name in ('.', '..'):
                continue

            self.flist.append(fi)

        # 先按(是否)目录排序,后按名称排序
        self.flist.sort(key=lambda x: (x.attri[0] != 'd', x.name.lower()))

    def Load(self, full_path, flist):
        '设置数据'

        self.__init__(full_path, flist)

        return len(self.flist)

    def rm_files(self, lines):
        lines.sort(reverse=True)

        out = []
        for x in lines:
            out.append(self.flist.pop(x))

        return out

    def rename(self, old_name, new_name):
        find = False
        for fi in self.flist:
            if fi.name == old_name:
                fi.name = new_name
                find = True
                break

        assert find

    def find(self, name):
        '查找目录中是否存在某个文件'

        for i, x in enumerate(self.flist):
            if x.name == name:
                return i

        return -1

    # 实现LC_VIRTUAL需要的接口
    def GetCount(self):
        return len(self.flist)

    # 实现LC_VIRTUAL需要的接口
    def GetItem(self, index):
        if index >= len(self.flist):
            return None

        return self.flist[index]

    # 实现LC_VIRTUAL需要的接口
    def UpdateCache(self, start, end):
        pass


def sizeFormat(size, is_disk=False, precision=2):
    '''
    size format for human.
        byte      ---- (B)
        kilobyte  ---- (KB)
        megabyte  ---- (MB)
        gigabyte  ---- (GB)
        terabyte  ---- (TB)
        petabyte  ---- (PB)
        exabyte   ---- (EB)
        zettabyte ---- (ZB)
        yottabyte ---- (YB)
    '''
    formats = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    unit = 1000.0 if is_disk else 1024.0

    if not(isinstance(size, float) or isinstance(size, int)):
        raise TypeError('a float number or an integer number is required!')

    if size < 0:
        raise ValueError('number must be non-negative')

    for i in formats:
        if size < unit:
            if i == 'B':
                return "{} B".format(size)
            return "{} {}".format(format(size, '.%df' % precision), i)
        size /= unit

    return "{} {}".format(format(size, '.%df' % precision), i)


def timeFormat(secs):
    secs = int(secs)
    h = int(secs/3600)
    m = int(secs/60)
    s = secs % 60

    return "%02d:%02d:%02d" % (h, m, s)


def get_floder_size(path):

    size = 0

    for x in os.listdir(path):

        x = os.path.join(path, x)

        if os.path.isfile(x):
            size += os.path.getsize(x)
        elif os.path.isdir(x):
            size += get_floder_size(x)

    return size


def get_file_md5(filename):
    '获取文件的md5'

    f = open(filename, 'rb')
    data = f.read()
    f.close()

    h = hashlib.md5()
    h.update(data)
    md5 = h.hexdigest()

    return md5


def get_safe_tempfile(path, ext=''):
    '获取临时文件名'

    guid = uuid.uuid1()
    tmp = os.path.join(path, str(guid) + ext)
    return tmp


def get_uuid_str():
    return str(uuid.uuid1())


def get_remote_filename(filename, remote_path):

    fn = os.path.split(filename)[-1]

    if not remote_path.endswith('/'):
        remote_path = remote_path + '/'

    rfn = remote_path + fn

    return rfn


def covert_path(flist, new_path):
    '为一批文件更换目录'

    if not new_path.endswith('/'):
        new_path = new_path + '/'

    fl2 = []

    for x in flist:
        fn = os.path.split(x)[-1]
        fn2 = new_path + fn
        fl2.append(fn2)

    return fl2


my_CommandEvent, my_EVT_COMMAND_EVENT = wx.lib.newevent.NewCommandEvent()


def PostEvent(cmd_id, wnd=None, **kw):
    '发送命令事件'

    if isinstance(cmd_id, CmdID):
        cmd_id = cmd_id.value

    evt = my_CommandEvent(id=cmd_id, **kw)

    if wnd is None:
        wnd = wx.GetApp().GetTopWindow()

    wx.PostEvent(wnd, evt)  # Post the event


if __name__ == "__main__":
    cfg = ConfigFile('config.yaml')
    cfg.get_host_list()
