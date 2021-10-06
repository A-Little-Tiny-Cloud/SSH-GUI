'''
windows操作系统相关的封装
本模块是其它模块基础,不可以引用工程内其它文件.
'''

import os
from ctypes import cdll, c_void_p, c_int, c_wchar_p, pointer
from ctypes.wintypes import HWND, LPRECT, RECT
import win32gui
import commctrl
from win32com.shell import shell, shellcon
from win32con import FILE_ATTRIBUTE_NORMAL, FILE_ATTRIBUTE_DIRECTORY
import wx


def listview_GetEdit(handle):
    '对正在编辑的listview,返回编辑控件'

    # 发送 LVM_GETEDITCONTROL 消息, 返回编辑控件的句柄
    hwnd = win32gui.SendMessage(handle, commctrl.LVM_GETEDITCONTROL, 0, 0)
    assert win32gui.IsWindow(hwnd)

    # title = win32gui.GetWindowText(hwnd)  # 测试句柄是否正确
    # print(title)

    edit_ctrl = wx.TextCtrl()
    edit_ctrl.AssociateHandle(hwnd)

    return edit_ctrl


def shell_get_fileinfo(extension):
    """根据扩展名得到文件图标"""

    assert len(extension) > 0

    flags = shellcon.SHGFI_SMALLICON | shellcon.SHGFI_ICON |  \
        shellcon.SHGFI_DISPLAYNAME | shellcon.SHGFI_TYPENAME | \
        shellcon.SHGFI_USEFILEATTRIBUTES

    if extension[0] == '.':
        retval, info = shell.SHGetFileInfo(extension, FILE_ATTRIBUTE_NORMAL, flags)
    else:
        retval, info = shell.SHGetFileInfo(extension, FILE_ATTRIBUTE_DIRECTORY, flags)

    # non-zero on success
    assert retval

    return info


def get_file_ext(fname):
    '得到文件扩展名'

    a, b = os.path.splitext(fname)
    ext = b if b else a
    return ext


class TypeItem:
    def __init__(self, ext, info, pos):
        hicon, iicon, attr, display_name, type_name = info

        # Get the bitmap
        icon = wx.Icon()
        icon.SetHandle(hicon)

        self.ext = ext
        self.icon = icon  # wx.BitmapFromIcon(icon)
        self.type_name = type_name
        self.pos = pos    # 图标在ImageList中序号


class FileTypeInfo:
    '文件类型信息,包括文字描述和图标'

    def __init__(self):

        self.img_list = wx.ImageList(20, 20)
        self.fti_map = {}
        self.cache()

    def cache(self):
        '预先缓存一批常用图标,加快速度'

        files = [os.getenv('windir'), '.---',  # 前两个是特殊的
                 '.txt', '.log', '.pdf', '.doc', '.docx', '.xls', '.ppt', '.pptx',
                 '.bmp', '.jpg', '.jpeg', '.png',
                 '.avi', '.mp4', '.mkv',
                 '.zip', '.rar', '.tar', '.bz2', '.gz', '.tgz',
                 '.htm', '.html', '.chm', '.xml',
                 '.md', '.py', '.whl', '.cpp', '.c', '.h']

        for i, x in enumerate(files):
            ti = TypeItem(x, shell_get_fileinfo(x), i)
            self.fti_map[x] = ti
            self.img_list.Add(ti.icon)

    def new_file_type(self, fi):

        ext = get_file_ext(fi.name)

        n = self.img_list.GetImageCount()

        ti = TypeItem(ext, shell_get_fileinfo(ext), n)
        self.fti_map[ext] = ti
        self.img_list.Add(ti.icon)

        return ti.pos

    def get_file_icon(self, fi):
        '根据文件信息,得到文件图标'

        if fi.attri[0] == 'd':
            return 0

        ext = get_file_ext(fi.name)

        fti = self.fti_map.get(ext)

        if fti is None:
            return self.new_file_type(fi)

        return fti.pos


class CExtDll:
    '''
    封装dll导出功能
    1.写入格式是自定义的RemoteFileName,因此写入后,操作系统的粘贴不能操作.
    2.读出格式支持两种,自定义的和系统的.因此操作系统的复制/剪切操作后,也可以读出.
    3.系统剪切板同一类数据只保存一个,因此写入剪切板后,之前的自定义数据会被清空.
    4.如果剪切板中存在两种可读数据(目前未出现,操作系统复制/剪切前会清空自定义数据),
      会优先读出自定义数据(同时清空剪切板)
    '''

    def __init__(self, dll_path):

        dll = cdll.LoadLibrary(dll_path)

        dll.clipboard_check.restype = c_int                   # int clipboard_check()

        dll.clipboard_put_files.argtypes = (c_void_p, )       # int clipboard_put_files(void * obj)
        dll.clipboard_put_files.restype = c_int

        dll.clipboard_get_filelist.restype = c_void_p         # void* clipboard_get_filelist()

        dll.filelist_create.argtypes = (c_int, c_int)         # void* filelist_create(int bCut, int bRemote)
        dll.filelist_create.restype = c_void_p

        dll.filelist_add.argtypes = (c_void_p, c_wchar_p)     # void filelist_add(void * obj, wchar_t * file)

        dll.filelist_get_num.argtypes = (c_void_p, )          # int filelist_get_num(void * obj)
        dll.filelist_get_num.restype = c_int

        dll.filelist_is_cut.argtypes = (c_void_p, )           # int filelist_get_cut(void * obj)
        dll.filelist_is_cut.restype = c_int

        dll.filelist_is_remote.argtypes = (c_void_p, )        # int filelist_is_remote(void * obj)
        dll.filelist_is_remote.restype = c_int

        dll.filelist_get_file.argtypes = (c_void_p, c_int)    # wchar_t*  filelist_get_file(void * obj, int i)
        dll.filelist_get_file.restype = c_wchar_p

        dll.filelist_free.argtypes = (c_void_p, )             # void filelist_free(void * obj)

        dll.shell_open_and_wait.argtypes = (c_wchar_p, )      # void shell_open_and_wait(wchar_t * file)

        dll.Edit_BalloonTip_Show.argtypes = (HWND, c_wchar_p)  # void Edit_BalloonTip_Show(HWND hEdit, wchar_t * msg)
        dll.Edit_BalloonTip_Hide.argtypes = (HWND, )           # void Edit_BalloonTip_Hide(HWND hEdit)

        dll.Toolbar_GetItemRect.argtypes = (HWND, c_int, LPRECT)  # void Toolbar_GetItemRect(HWND hToolbar, int idx, LPRECT rc)

        dll.ListCtrl_SetItemText.argtypes = (HWND, c_int, c_int, c_wchar_p)   # void ListCtrl_SetItemText(HWND hListCtrl, int idx, int sub, wchar_t * text)
        self.dll = dll

    def clipboard_check(self):
        '检查剪切板是否有数据'

        return bool(self.dll.clipboard_check())

    def clipboard_read(self):
        '从剪切板上读出数据'

        flobj = self.dll.clipboard_get_filelist()

        if flobj is None:
            return 0, 0, []

        n = self.dll.filelist_get_num(flobj)
        cut = self.dll.filelist_is_cut(flobj)
        remote = self.dll.filelist_is_remote(flobj)

        buf = []
        for i in range(n):
            fn = self.dll.filelist_get_file(flobj, i)
            buf.append(fn)

        self.dll.filelist_free(flobj)

        return cut, remote, buf

    def clipboard_write(self, flist, bcut):
        '把文件列表放入剪切板'

        flobj = self.dll.filelist_create(bcut, True)

        for x in flist:
            self.dll.filelist_add(flobj, x)

        self.dll.clipboard_put_files(flobj)

        self.dll.filelist_free(flobj)

    def shell_open_and_wait(self, filename):
        '使用windows shell 打开程序并等待结束'

        # 使用系统关联程序打开文件,并在编辑结束后上传文件.
        # 打开文件可使用shell程序os.startfile等.
        # 但如何判断编辑结束,考虑过多个方案:
        # a. 监视文件的变化, 若有改变则进入上传队列.
        # b. 拦截系统CloseHandle函数, 在关闭文件时通知界面.
        # c. 读注册表,得到关联程序,创建进程打开文件. 等待进程退出.
        # d. 使用带等待功能的shell函数, 如os.system或win32api.ShellExecuteEx等

        self.dll.shell_open_and_wait(filename)

    def Edit_ShowBalloonTip(self, hwnd, msg):
        self.dll.Edit_BalloonTip_Show(hwnd, msg)

    def Edit_BalloonTip_Hide(self, hwnd):
        self.dll.Edit_BalloonTip_Hide(hwnd)

    def Toolbar_GetItemRect(self, hwnd, idx):
        rc = RECT()
        self.dll.Toolbar_GetItemRect(hwnd, idx, pointer(rc))

        return (rc.left, rc.top, rc.right, rc.bottom)

    def ListCtrl_SetItemText(self, hwnd, idx, sub, text):
        self.dll.ListCtrl_SetItemText(hwnd, idx, sub, text)


# ----------------------------------------------------------------------------
# 全局对象

os_ext = CExtDll('sshgui_ext.dll')

# ----------------------------------------------------------------------------


if __name__ == "__main__":
    app = wx.App()
    k = FileTypeInfo()
