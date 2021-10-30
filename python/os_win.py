'''
windows操作系统相关的封装
本模块是其它模块基础,不可以引用工程内其它文件.
'''

import os
from ctypes import cdll, c_void_p, c_int, c_wchar_p, pointer
from ctypes.wintypes import HWND, LPRECT, RECT
import winreg

import win32api
import win32gui
import win32process
import win32event
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


def shell_get_fileinfo(extension, link=False):
    """根据扩展名得到文件图标"""

    assert len(extension) > 0

    flags = shellcon.SHGFI_SMALLICON | shellcon.SHGFI_ICON |  \
        shellcon.SHGFI_DISPLAYNAME | shellcon.SHGFI_TYPENAME | \
        shellcon.SHGFI_USEFILEATTRIBUTES

    if link:
        flags = flags | shellcon.SHGFI_LINKOVERLAY

    if extension[0] == '.':
        retval, info = shell.SHGetFileInfo(extension, FILE_ATTRIBUTE_NORMAL, flags)
    else:
        retval, info = shell.SHGetFileInfo(extension, FILE_ATTRIBUTE_DIRECTORY, flags)

    # non-zero on success
    assert retval

    return info


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


def read_reg_value(path, name=None):
    '读出一个注册表项的值,path是全路径,name是项的名称'

    its = path.split('\\')

    root = its[0]

    if root == 'HKEY_CURRENT_USER':
        root = winreg.HKEY_CURRENT_USER

    elif root == 'HKEY_LOCAL_MACHINE':
        root = winreg.HKEY_LOCAL_MACHINE

    elif root == 'HKEY_CLASSES_ROOT':
        root = winreg.HKEY_CLASSES_ROOT

    else:
        root = int(root)

    sub = "\\".join(its[1:])

    try:
        key = winreg.OpenKey(root, sub)
        value, code = winreg.QueryValueEx(key, name)

        if code == winreg.REG_EXPAND_SZ:
            value = os.path.expandvars(value)

        return value

    except OSError:
        pass

    return ''


def read_reg_fileexts(root_key, ext):

    cmd = ''

    path = r'%s\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\%s\UserChoice' % (root_key, ext)

    progid = read_reg_value(path, 'ProgId')

    if progid:

        path3 = [
            r'HKEY_CURRENT_USER\Software\Classes\%s\shell\open\command' % progid,
            r'HKEY_LOCAL_MACHINE\Software\Classes\%s\shell\open\command' % progid,
            r'HKEY_CLASSES_ROOT\Software\Classes\%s\shell\open\command' % progid
        ]

        for x in path3:

            cmd = read_reg_value(x, None)

            if cmd:
                break

    return cmd


def get_associate_cmdline(ext):
    '得到扩展名对应文件的open命令行'

    cmd = read_reg_fileexts(winreg.HKEY_CURRENT_USER, ext)

    if cmd:
        return cmd

    cmd = read_reg_fileexts(winreg.HKEY_LOCAL_MACHINE, ext)
    if cmd:
        return cmd

    # 按如下优先级:
    path3 = [
        r'HKEY_CURRENT_USER\Software\Classes',
        r'HKEY_LOCAL_MACHINE\Software\Classes',
        r'HKEY_CLASSES_ROOT',
    ]

    for x in path3:
        path = x + r'\%s' % ext
        ftype = read_reg_value(path)

        if ftype:
            path = x + r'\%s\shell\open\command' % ftype
            cmd = read_reg_value(path)

            if cmd:
                return cmd

    return ''


def Excute_and_Wait(cmd):
    # CreateProcess(
    #   appName,
    #   commandLine ,
    #   processAttributes ,
    #   threadAttributes ,
    #   bInheritHandles ,
    #   dwCreationFlags ,
    #   newEnvironment ,
    #   currentDirectory ,
    #   startupinfo )

    info = win32process.STARTUPINFO()
    info.hStdInput = win32api.GetStdHandle(win32api.STD_INPUT_HANDLE)
    info.hStdOutput = win32api.GetStdHandle(win32api.STD_OUTPUT_HANDLE)
    info.hStdError = win32api.GetStdHandle(win32api.STD_ERROR_HANDLE)

    this_dir = os.path.dirname(__file__)

    hProcess, hThread, dwProcessId, dwThreadId = win32process.CreateProcess(None, cmd, None, None, 1, 0, os.environ, this_dir, info)
    win32event.WaitForSingleObject(hProcess, win32event.INFINITE)


if __name__ == "__main__":
    print(".bmp " + get_associate_cmdline('.bmp'))
    print(".tar " + get_associate_cmdline('.tar'))
    print('.doc ' + get_associate_cmdline('.doc'))
    print('.pdf ' + get_associate_cmdline('.pdf'))
    print('.exe ' + get_associate_cmdline('.exe'))
    print('.flv ' + get_associate_cmdline('.flv'))
    print('.chm ' + get_associate_cmdline('.chm'))
    print('.jpg ' + get_associate_cmdline('.jpg'))
    print('.gif ' + get_associate_cmdline('.gif'))
    print('.dat ' + get_associate_cmdline('.dat'))
    print('.*** ' + get_associate_cmdline('.***'))
