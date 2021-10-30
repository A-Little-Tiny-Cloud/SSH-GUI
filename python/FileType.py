'''
文件类型
'''

import os
import mimetypes
import wx
from os_win import shell_get_fileinfo, get_associate_cmdline


class FileTypeItem:
    '文件类型信息,包括文字描述和图标'

    def __init__(self, mime, ext, descript):

        self.mime = mime
        self.ext = ext
        self.descript = descript
        self.open_cmd = ""
        if ext and ext not in ('/', '?', '->'):
            self.open_cmd = get_associate_cmdline(ext)

    def is_dir(self) -> bool:
        return self.mime == 'inode/directory'


# 区分文件类型,目的是: 图标和关联程序
# 图标用于显示,关联程序用于打开文件.
# 1.已知有固定扩展名的文件
# 2.无固定扩展名,但类型确定(如 *.so.xxx)
# 3.无扩展名,但类型确定(如elf文件)
# 4.类型未知(可有也可以没有扩展名)
class FileTypeList:
    '文件类型列表,保存所有文件类型信息'

    def __init__(self):
        mimetypes.init()

        self.img_list = wx.ImageList(20, 20)
        self.ft_list = []

        self.ext_map = {}    # 扩展名 -> 序号

        # 已知的mime类型,这些类型无法用扩展名区分
        # 为了统一处理, 将这些mine类型映射到扩展名
        self.mime_to_ext = {
            'inode/directory': '/',
            'application/octet-stream': '?',
            'inode/symlink': '->',
            'application/x-sharedlib': '.dll',
            'application/x-executable': '.exe',
            'application/x-archive': '.lib',
        }

        # 二次判别,在找不到扩展名类型的情况下,再次使用mime判别
        self.mime_to_ext_2 = {
            'text/plain': '.txt',
            'text/x-python': '.py',
        }

        self.init()

    def new_file_type(self, ext, mime):

        assert isinstance(ext, str) and len(ext) > 1

        info = shell_get_fileinfo(ext)  # hicon, iicon, attr, display_name, type_name
        ti = FileTypeItem(mime, ext, info[4])

        self.ft_list.append(ti)

        icon = wx.Icon()
        icon.SetHandle(info[0])
        self.img_list.Add(icon)

        pos = self.img_list.GetImageCount() - 1
        self.ext_map[ext] = pos

        return pos

    def x_file_type(self, ext, mime, hicon, descrip):
        '特殊文件'

        ti = FileTypeItem(mime, ext, descrip)

        self.ft_list.append(ti)

        icon = wx.Icon()
        icon.SetHandle(hicon)
        self.img_list.Add(icon)

        self.ext_map[ext] = len(self.ft_list) - 1

    def init(self):

        # 前3个是特殊的
        # 0:目录, 1:未知文件, 2:快捷方式(一律按未知文件的快捷方式处理)

        info = shell_get_fileinfo(os.getenv('windir'))  # hicon, iicon, attr, display_name, type_name
        self.x_file_type('/', 'inode/directory', info[0], "文件夹")   # 使用'/'作为目录的"扩展名"

        info = shell_get_fileinfo('.---')
        self.x_file_type('?', 'application/unknown', info[0], '未知文件')   # 使用'?'作为未知文件的"扩展名"

        info = shell_get_fileinfo('.---', True)
        self.x_file_type('->', 'inode/symlink', info[0], '软链接')   # 使用'->'作为快捷方式的"扩展名"

        for k, v in mimetypes.types_map.items():
            self.new_file_type(k, v)

    def first_check(self, mime):
        '首次检查,处理mime比较可靠的类型'

        ext = self.mime_to_ext.get(mime)

        if ext:
            return ext

        # mime检查对图像文件来说比较可靠
        if mime.startswith('image/'):
            ext2 = "." + mime[len('image/'):]
            return ext2

        return ''

    def get_file_icon(self, fname, mime):
        '根据文件信息,得到文件图标的序号'

        # 注意判定顺序
        # 1. 已知的几种 mime 类型
        # 2. 无扩展名的情况下, 根据 mime 判定
        # 3. 有扩展名的情况下:
        #    a. 看看是否已知扩展名类型
        #    b. mime 类型 二次判别
        #    c. 新类型或未知类型

        ext = self.first_check(mime)

        if not ext:
            ext = os.path.splitext(fname)[-1]

        if not ext:  # 没有扩展名
            ext2 = self.mime_to_ext_2.get(mime)
            if ext2:
                pos = self.ext_map.get(ext2)
                return pos

            return 1   # 未知文件

        pos = self.ext_map.get(ext)

        if pos is None:

            # 下面这些类别:
            # 直接通过mime判别有一定风险,如*.h有时会出现text/plain
            # 查找过已知扩展名之后,如果没有,再使用mime判定.
            ext2 = self.mime_to_ext_2.get(mime)

            if ext2:
                pos = self.ext_map.get(ext2)

            else:
                pos = self.new_file_type(ext, mime)

        return pos

    def get_file_descrip(self, pos):
        return self.ft_list[pos].descript


class FileItem:
    '文件项,一个文件或目录'

    def __init__(self, parent_path, line, f2m):

        if not parent_path.endswith('/'):
            parent_path = parent_path + '/'

        self.path = parent_path

        its = line.split()

        # 下面是line的两个例子(命令为: ls -l --time-style=long-iso)
        # -rw-rw-r--  1 lihengfeng lihengfeng       7397 2021-09-15 13:56 0001.txt
        # lrwxrwxrwx. 1 lihengfeng lihengfeng       45 2021-07-21 11:36 pip3 -> /home/lihengfeng/software/Python38/bin/pip3.8

        assert len(its) >= 8

        self.attri = its[0]
        self.group = its[2]
        self.owner = its[3]
        self.size = int(its[4]) if self.attri[0] != 'd' else -1
        self.date = its[5]  # 年-月-日
        self.time = its[6]  # 时:分

        # 考虑到文件名可能包含空格, 因此不能简单的 line.split() 分离出文件名
        # 但前 7 个字段格式固定, 不包含空格.
        pos = line.find(self.time) + len(self.time) + 1  # 文件名开始的位置

        if self.attri[0] == 'l':
            txt = line[pos:]
            p2 = txt.find(' ->')
            self.name = txt[0:p2]
            self.src = txt[p2 + 4:]
        else:
            self.name = line[pos:]
            self.src = None

        self.mime = f2m[self.name]
        self.icon = get_global_ft_list().get_file_icon(self.name, self.mime)
        self.descrip = get_global_ft_list().get_file_descrip(self.icon)

    def change_path(self, path):
        '修改文件项所在的目录'

        if not path.endswith('/'):
            path = path + '/'

        self.path = path

    def full_path(self) -> str:
        '文件项的全路径'

        return self.path + self.name

    def is_dir(self) -> bool:
        return self.mime == 'inode/directory'

    def is_link(self) -> bool:
        return self.mime == 'inode/symlink'


# 目录数据
class PathData:
    '保存一个目录的数据,包括内部的所有文件项'

    def __init__(self, full_path, flist, mimes):

        self.path = full_path

        f2m = {}
        for x in mimes:
            a, b = x.split(':')
            f2m[a] = b.strip()

        self.flist = []

        for x in flist:

            fi = FileItem(full_path, x, f2m)

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


# ------------------------------------------------------------------------------
# 全局变量

g_ft_list = None


def get_global_ft_list() -> FileTypeList:
    return g_ft_list

# ------------------------------------------------------------------------------


if __name__ == "__main__":
    app = wx.App()
    k = FileTypeList()
