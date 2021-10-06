'''
python代码调用dll例程
dll功能为读写剪切板(自定义格式)
'''

from ctypes import cdll, c_void_p, c_int, c_wchar_p


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

        self.dll = dll

    def clipboard_check(self):
        '检查剪切板是否有数据'

        return bool(self.dll.clipboard_check())

    def clipboard_read(self):
        '从剪切板上读出数据'

        flobj = self.dll.clipboard_get_filelist()

        if flobj is None:
            return 0, []

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


def test1():

    dllpath = r"D:\lhf\Program\sshgui_ext\bin\Release\sshgui_ext.dll"
    obj = CExtDll(dllpath)

    fl = [
        'd:\\1.jpg',
        'd:\\2.jpg',
        'd:\\3.jpg',
        'd:\\4.jpg',
        '10.10.11.50:/home/lihengfeng/temp/aaa.jpg',  # 格式可自由定义
        '10.10.11.50:/home/lihengfeng/temp/bbb.jpg',
        'lihengfeng@10.10.11.50:/home/lihengfeng/temp/ccc.jpg',
    ]

    obj.clipboard_write(fl, False)


def test2():

    dllpath = r"D:\lhf\Program\sshgui_ext\bin\Release\sshgui_ext.dll"
    obj = CExtDll(dllpath)
    cut, remote, flist = obj.clipboard_read()

    ops = 'move' if cut else 'copy'
    src = 'remote' if remote else 'local'

    print("%s %s file %d" % (ops, src, len(flist)))

    for x in flist:
        print(x)


if __name__ == "__main__":
    test1()
    test2()
