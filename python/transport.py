'''
封装通讯功能ssh/sftp
'''


import os
import sys
import paramiko
from common import ConfigFile, get_file_md5, get_remote_filename


class SSHExecuteError(RuntimeError):
    "ssh 命令执行错误"

    def __init__(self, cmd, msg):
        self.cmd = cmd
        self.msg = msg

    def __str__(self):
        return "ssh cmd err:{} {}".format(self.cmd, self.msg)


# 由于 SSHClient.exec_command 每次都是新的session
# 因此无法设置当前目录, 而是每次都从用户主目录开始
# 为了方便,记录当前目录.每次都先切换到目录,再执行命令(合成一条语句执行).
class SSH_Wrap:
    'ssh/stfp功能封装'

    def __init__(self):

        self.ssh = paramiko.SSHClient()
        # 自动添加策略(自动保存服务器的主机/密钥信息); 默认不在本地know_hosts文件中的主机无法连接
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        self.sftp = None
        self.path = None  # 记录当前目录

    def __del__(self):
        if self.sftp is not None:
            self.sftp.close()

        self.ssh.close()

    def conncet(self, ip, port, user, passwd):

        try:
            self.ssh.connect(ip, port, user, passwd)
            self.sftp = self.ssh.open_sftp()
            self.chan = self.ssh._transport.open_session()

        except paramiko.BadHostKeyException as e:
            raise SSHExecuteError('connet', str(e))

        except paramiko.SSHException as e:
            raise SSHExecuteError('connet', str(e))

        except paramiko.AuthenticationException as e:
            raise SSHExecuteError('connet', str(e))

        except Exception as e:
            raise SSHExecuteError('connet', str(e))

    def execute(self, cmd, current_path=None):

        # ssh.exec_command是一个单次执行session,执行完毕就销毁
        # 因此需先cd到指定目录,然后再执行命令

        if current_path:
            path = current_path
        else:
            path = self.path

        cmd2 = "cd {}; {}".format(path, cmd)
        stdin, stdout, stderr = self.ssh.exec_command(cmd2)
        buf1 = stdout.read()
        buf2 = stderr.read()

        if len(buf2) > 0:
            text = buf2.decode(encoding='utf-8')
            raise SSHExecuteError(cmd.split()[0], text)

        text = buf1.decode(encoding='utf-8')

        return text

    def open_dir(self, remote_path, show_hide=False):
        '打开目录, 对应cd + ls + file命令'

        if show_hide:
            cmd = "ls -al --time-style=long-iso; file --mime-type .* *"
        else:
            cmd = "ls -l --time-style=long-iso; file --mime-type *"

        ret = self.execute(cmd, remote_path)

        self.path = remote_path  # 命令执行成功,才改变当前目录(否则不变)

        buf = ret.split('\n')

        lines = []

        for x in buf[1:]:  # 第0行是 total xxxx
            if x == '*: cannot open (No such file or directory)':
                continue
            elif len(x.strip()) == 0:
                continue
            else:
                lines.append(x)

        assert len(lines) % 2 == 0

        n = len(lines)//2
        lines1 = lines[0:n]
        lines2 = lines[n:]

        files = []
        for line in lines1:

            its = line.split()

            if len(its) < 8:
                continue

            files.append(line)

        mimes = []
        for line in lines2:

            its = line.split()

            if len(its) < 2:
                continue

            mimes.append(line)

        return files, mimes

    def set_path(self, remote_path):
        '直接设置当前目录'

        self.path = remote_path

    def rename(self, old_name, new_name):
        '修改名称, 对应mv命令'

        cmd = "mv {} {}".format(old_name, new_name)
        self.execute(cmd)

    def rm_file(self, item):
        '删除文件或目录, 对应rm命令'

        cmd = "rm -rf {}".format(item)
        self.execute(cmd)

    def mv_files(self, src):
        '移动多个文件或目录到当前目录, 对应mv命令'

        if isinstance(src, str):
            src = [src]

        cmd = "mv {} ./ --backup=numbered".format(' '.join(src))
        self.execute(cmd)

    def cp_files(self, src, dst_path):
        '复制文件或目录, 对应cp命令'

        if isinstance(src, str):
            src = [src]

        self.execute("cp -bdpR {} {}".format(' '.join(src), dst_path))

    def mkdir(self, path):
        '创建目录'

        self.execute("mkdir {}".format(path))

    def check_file(self, local_file, remote_file):
        '检查远程文件和本地文件md5是否相同'

        cmd = 'md5sum {}'.format(remote_file)
        text = self.execute(cmd)

        code = text.split()[0]

        md5 = get_file_md5(local_file)

        return md5 == code

    def put_file(self, filename, remote_file, callback=None):
        '使用sftp上传文件'

        try:
            self.sftp.put(filename, remote_file, callback)
        except Exception as e:
            raise SSHExecuteError('stp-put', str(e))

    def get_file(self, remote_file, local_file, callback=None):
        '使用sftp下载文件'

        try:
            self.sftp.get(remote_file, local_file, callback)
        except Exception as e:
            raise SSHExecuteError('stp-get', str(e))


def upload(filename):
    cfg = ConfigFile('config.yaml')
    info = cfg.get_host_info('bandwagon')
    sftp = SSH_Wrap(info.ip, info.port, info.user, info.password)
    sftp.put_file(filename, '/home/lhf/tmp')


def download(filename):
    cfg = ConfigFile('config.yaml')
    info = cfg.get_host_info('bandwagon')
    sftp = SSH_Wrap(info.ip, info.port, info.user, info.password)

    rfile = get_remote_filename(filename, info.remote_path)
    local_path = os.path.split(filename)[0]

    sftp.get_file(rfile, local_path)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print('usage: python FileSync.py upload/download filename')

    elif sys.argv[1] == 'upload':
        print('upload %s ...' % sys.argv[2])
        upload(sys.argv[2])

    elif sys.argv[1] == 'download':
        print('download %s ...' % sys.argv[2])
        download(sys.argv[2])
