﻿'''
打开文件
根据文件类型不同,打开文件的操作也不同.
例如:
 - 文本文件,表示打开文件,并编辑(完成后还可以上传)
 - 图像文件,显示图像.
 - 动态库: 显示依赖关系
'''

import os
import wx
from common import FileItem, FileType, get_safe_tempfile, get_file_md5
from CtrlWnd import MessageBox
from os_win import os_ext


def open_file(fi: FileItem, work_path, ssh):
    '打开一个文件,根据文件类型不同,实际操作也不同'

    # a. 先判断是否可以打开,以及根据文件大小等决定是否提示.
    # a. 若文件太大,提示用户先下载.
    # b. 若文件较小,判断是否已知的文件类型.
    #    - 若是已知类型,调用对应的关联程序打开.
    #    - 若不是已知类型, 需弹出对话框选择打开方式.
    # c. 监控文件改变,当文件关闭后,弹出消息框提示用户,上传覆盖.

    max_size = 600 * 1024  # 以100K为界限

    big = False

    # step1, 判断文件情况
    if fi.size > max_size:
        msg = "当前文件尺寸较大，无法直接编辑。\n\n 可下载后自行编辑\n 需要现在下载吗？"
        if MessageBox(None, "提示", msg, wx.ICON_INFORMATION | wx.YES_NO) == wx.ID_NO:
            return
        big = True

    # step2, 下载文件
    tmp_path = get_safe_tempfile(work_path)
    os.makedirs(tmp_path)
    locfile = os.path.join(tmp_path, fi.name)
    ssh.get_file(fi.full_path(), locfile)

    if big:
        return

    sz = os.path.getsize(locfile)
    md5 = get_file_md5(locfile)

    # step3, 根据文件类型,打开已知类型, 或调用操作系统打开

    if fi.ftype == FileType.text_plain:    # 简单文本

        # 对简单文本文件,由于需要做回城符转换('\n' <--> '\r\n'),
        # 应该使用自己的代码编辑文件.
        # 目前暂时使用系统默认打开方式(记事本程序)
        os_ext.shell_open_and_wait(locfile)

    elif fi.ftype == FileType.image:       # 图像
        os_ext.shell_open_and_wait(locfile)

    else:
        os_ext.shell_open_and_wait(locfile)

    # step4, 检测文件是否修改,弹框确认后,上传文件.
    sz_ = os.path.getsize(locfile)
    md5_ = get_file_md5(locfile)

    if sz != sz_ or md5 != md5_:
        msg = "检测到您修改了文件：\n\n{}\n是否要将新版本上传到服务器（覆盖老版本）？".format(fi.name)

        if MessageBox(None, "提示", msg, wx.YES_NO) == wx.ID_YES:
            ssh.put_file(locfile, fi.full_path())


if __name__ == "__main__":
    pass
