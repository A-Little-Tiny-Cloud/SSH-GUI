'''
传输文件
包括下载,上传,两个远程主机互传.
输入是多个文件项

linux文件名区分大小写,windows不区分.
例如在linux下可能在一个目录中同时存在: a.txt 和 A.txt
复制到windows下就有问题, 因为 a.txt 和 A.txt 会当成一个文件!
因此需要检测是否重名,以及(为了方便)自动重命名.

由于会发生自动重命名,软连接也可能失效.因此软连接直接复制源文件.
'''

import os
import time
from threading import Thread, Lock
from common import FileType, FileItem, PathData, get_safe_tempfile, get_floder_size, get_uuid_str


class FileProgress:
    '一个文件的进度信息'

    def __init__(self, filesize):
        self.size = filesize
        self.__pos = 0
        self.lock = Lock()

    def update(self, a, b):

    #   self.lock.acquire()
        self.__pos = a
    #   self.lock.release()

    def close(self):

    #   self.lock.acquire()
        self.__pos = self.size
    #   self.lock.release()

    def get(self):

    #   self.lock.acquire()
        pos = self.__pos
    #   self.lock.acquire()

        return pos


# 记录每个文件的进度,总的进度
# 有三个线程:
# a. 界面线程,会定时调用: is_end, get_files, get
# b. download_thread 线程, 调用: new_file, set_end
# c. ssh下载线程, 调用当前文件的 FileProgress.update
class Progress:
    '下载进度管理'

    def __init__(self, total=-1):
        self.total = total    # 总任务大小
        self.pos = 0          # 已下载
        self.pos2 = 0         # 实时进度

        self.files = []

        self.lock = Lock()
        self.end = False

    def new_file(self, filesize):
        '开始一个新文件,把上一个文件的大小加入'

        self.lock.acquire()

        if self.files:
            self.files[-1].close()
            self.pos += self.files[-1].size

        self.pos2 = self.pos

        fp = FileProgress(filesize)
        self.files.append(fp)

        self.lock.release()

        return fp

    def set_end(self):
        '设置处理完成'

        self.lock.acquire()

        self.end = True

        self.lock.release()

    def is_end(self):

        self.lock.acquire()

        end = self.end

        self.lock.release()

        return end

    def get_files(self):
        '所有已知文件进度'

        self.lock.acquire()

        flist = self.files.copy()

        self.lock.release()

        return flist

    def get(self):
        '任务总进度'

        self.lock.acquire()

        cp = self.files[-1].get() if self.files else 0
        self.pos2 = self.pos + cp
        pos2 = self.pos2
        total = self.total if self.total > 0 else 1

        self.lock.release()

        return pos2 * 100 / total


def get_relative_path(path: str, base_path: str):
    '得到相对路径'

    if not base_path.endswith('/'):
        base_path = base_path + '/'

    assert path.startswith(base_path)

    sub = path[len(base_path):]

    return sub


def safe_rename(locfile):
    '重命名,避免重名冲突'

    a, b = os.path.splitext(locfile)

    i = 0

    while True:

        fn = a + "_%d" % i + b

        if not os.path.exists(fn):
            return fn

        i += 1

    return ''


def download_file(local_path, fi: FileItem, ssh, prg: Progress):
    '下载单个文件'

    locfile = os.path.join(local_path, fi.name)
    if os.path.exists(locfile):
        newfile = safe_rename(locfile)
        print('waring: file name conflict! {} -> {}'.format(locfile, newfile))
        locfile = newfile

    fp = prg.new_file(fi.size)
    ssh.get_file(fi.full_path(), locfile, fp.update)


# 下载一个目录
# path: 全路径
# base_path: 基础路径
def download_folder(path: str, base_path: str, work_path: str, ssh, prg: Progress):

    sub = get_relative_path(path, base_path)
    subs = sub.split('/')

    if work_path.endswith('\\'):
        local_path = work_path + "\\".join(subs)
    else:
        local_path = work_path + "\\" + "\\".join(subs)

    os.makedirs(local_path)

    flist = ssh.open_dir(path)
    pd = PathData(path, flist)

    for fi in pd.flist:

        if fi.ftype == FileType.folder:  # 是目录
            download_folder(fi.full_path(), path, local_path, ssh, prg)

        else:
            download_file(local_path, fi, ssh, prg)


# 由于下载过程可能耗时较长,本函数需在新线程中调用,以免阻塞主界面
def download_thread(fi_list, base_path, work_path, ssh, prg: Progress):
    '下载多个文件项(文件或目录)到本地目录,保持目录结构不变'

    # step1,统计总的大小
    total_sz = 0

    for fi in fi_list:
        if fi.ftype == FileType.folder:  # 是目录
            cmd = "du -sblL {}".format(fi.full_path())
            ret = ssh.execute(cmd)
            size = int(ret.split()[0])
            total_sz += size
        else:
            total_sz += fi.size

    prg.total = total_sz

    # step2,下载
    for fi in fi_list:

        if fi.ftype == FileType.folder:  # 是目录
            download_folder(fi.full_path(), base_path, work_path, ssh, prg)

        else:
            download_file(work_path, fi, ssh, prg)

    prg.set_end()


def upload_file(local_path: str, fname: str, remote_path: str, ssh, prg: Progress):
    '上传单个文件,无需考虑重名问题'

    locfile = os.path.join(local_path, fname)

    filesize = os.path.getsize(locfile)
    fp = prg.new_file(filesize)

    if remote_path.endswith('/'):
        remote_file = remote_path + fname
    else:
        remote_file = remote_path + '/' + fname

    ssh.put_file(locfile, remote_file, fp.update)


# 上传一个目录
def upload_folder(local_path: str, fname: str, remote_path: str, ssh, prg: Progress):

    if remote_path.endswith('/'):
        remote_sub = remote_path + fname
    else:
        remote_sub = remote_path + '/' + fname

    ssh.mkdir(remote_sub)

    path = os.path.join(local_path, fname)

    for x in os.listdir(path):
        x_full = os.path.join(path, x)

        if os.path.isdir(x_full):  # 是目录
            upload_folder(path, x, remote_sub, ssh, prg)

        else:
            upload_file(path, x, remote_sub, ssh, prg)


# local_path: 本地目录(所有上传文件都该目录下)
# fnlist: 文件名/目录名列表,只有名称,不是全路径.
# remote_path: 远程目录
def upload_thread(local_path, fnlist, remote_path, ssh, prg: Progress):
    '上传多个文件项(文件或目录)到远程目录,保持目录结构不变'

    # step1,统计总的大小
    total_sz = 0

    for x in fnlist:
        x = os.path.join(local_path, x)

        if os.path.isdir(x):  # 是目录
            total_sz += get_floder_size(x)
        else:
            total_sz += os.path.getsize(x)

    prg.total = total_sz

    # step2,上传
    # 与下载不同,这里目录内部不存在重名的可能.
    # 为避免最上层目录出现重名,先上传到一个临时目录.
    # 然后使用 mv --backup 选项处理重名的文件.

    if remote_path.endswith('/'):
        tmp_path = remote_path + get_uuid_str()
    else:
        tmp_path = remote_path + '/' + get_uuid_str()

    ssh.execute("mkdir {}".format(tmp_path))

    for x in fnlist:
        x_full = os.path.join(local_path, x)

        if os.path.isdir(x_full):  # 是目录
            upload_folder(local_path, x, tmp_path, ssh, prg)

        else:
            upload_file(local_path, x, tmp_path, ssh, prg)

    # step3
    # 处理重名文件
    cmd = "mv {}/* {} --backup=numbered -v".format(tmp_path, remote_path)
    ssh.execute(cmd)

    ssh.rm_file(tmp_path)

    prg.set_end()


# ------------------------------------------------------------------------------
# 全局变量

g_next_task_id = 1
# ------------------------------------------------------------------------------


def get_next_taskid():
    global g_next_task_id

    tid = g_next_task_id
    g_next_task_id += 1

    return tid


class TransportTask:
    '传输任务基类'

    def __init__(self, task_type, src, dst):

        self.prg = Progress()
        self.id = get_next_taskid()
        self.begin = time.time()
        self.type = task_type
        self.src = src
        self.dst = dst
        self.alive = True

    def get_size(self):
        return self.prg.total

    def get_progreess(self):
        return self.prg.get()

    def is_end(self):

        if not self.alive:
            return True

        if self.prg.is_end():
            self.alive = False
            self.thread.join()
            return True

        return False

    def get_time(self):
        '返回已耗时,剩余时间,平均速度'

        consume = time.time() - self.begin
        prg = self.prg.get()
        speed = self.prg.pos2 / consume

        if prg < 1e-2:
            remain = consume * 100
        else:
            remain = (100-prg)/prg * consume

        return consume, remain, speed


class DownloadTask(TransportTask):
    '下载任务'

    def __init__(self, fi_list, base_path, work_path, ssh):

        tmp_path = get_safe_tempfile(work_path)
        os.makedirs(tmp_path)

        super(DownloadTask, self).__init__('download', base_path, tmp_path)

        self.thread = Thread(target=download_thread, args=(fi_list, base_path, tmp_path, ssh, self.prg))
        self.thread.start()


class UploadTask(TransportTask):
    '上传任务'

    def __init__(self, base_path, fname_list, remote_path, ssh):

        super(UploadTask, self).__init__('upload', base_path, remote_path)

        self.thread = Thread(target=upload_thread, args=(base_path, fname_list, remote_path, ssh, self.prg))
        self.thread.start()


def test_download():
    from transport import SSH_Wrap
    from common import ConfigFile

    cfg = ConfigFile('config.yaml')
    info = cfg.get_host_info('bandwagon')
    ssh = SSH_Wrap()

    ssh.conncet(info.ip, info.port, info.user, info.password)

    flist = ssh.open_dir(info.remote_path)
    pd = PathData(info.remote_path, flist)

    dl_list = [pd.flist[3], pd.flist[4], pd.flist[0]]

    prg = Progress()
    th = Thread(target=download_thread, args=(dl_list, info.remote_path, 'd:\\temp', ssh, prg))
    th.start()

    while not prg.is_end():
        time.sleep(2)
        print("progress=%f" % prg.get())

    th.join()


def test_upload():
    from transport import SSH_Wrap
    from common import ConfigFile

    cfg = ConfigFile('config.yaml')
    info = cfg.get_host_info('50服务器')
    ssh = SSH_Wrap()

    ssh.conncet(info.ip, info.port, info.user, info.password)
    ssh.open_dir(info.remote_path)

    local_path = r"d:\temp"
    fnlist = ['aaa.txt', '111']

    prg = Progress()
    th = Thread(target=upload_thread, args=(local_path, fnlist, info.remote_path, ssh, prg))
    th.start()

    while not prg.is_end():
        time.sleep(2)
        print("progress=%f" % prg.get())

    th.join()


if __name__ == "__main__":
    test_upload()
