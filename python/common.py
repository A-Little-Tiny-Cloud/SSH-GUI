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


def MessageBox(parent, title, msg, style=wx.OK):
    dlg = wx.MessageDialog(parent, msg, title, style=style | wx.CENTRE)
    return dlg.ShowModal()


if __name__ == "__main__":
    cfg = ConfigFile('config.yaml')
    cfg.get_host_list()
