# coding:utf-8

import wx
from common import CmdID, PostEvent, my_EVT_COMMAND_EVENT, MessageBox
from transport import SSHExecuteError
from os_win import os_ext
from HostOps import get_global_host


class myToolBar(wx.ToolBar):

    def __init__(self, parent):

        wx.ToolBar.__init__(self, parent, wx.ID_ANY, style=wx.TB_FLAT | wx.TB_HORIZONTAL)

        self.host = get_global_host()

        bmp1 = wx.Bitmap(wx.Image("res/imageres_25.ico").Scale(32, 32))
        bmp2 = wx.Bitmap(wx.Image("res/imageres_185.ico").Scale(32, 32))
        bmp3 = wx.Bitmap(wx.Image("res/imageres_5303.ico").Scale(32, 32))
        bmp4 = wx.Bitmap(wx.Image("res/imageres_171.ico").Scale(32, 32))
        bmp5 = wx.Bitmap(wx.Image("res/imageres_184.ico").Scale(32, 32))

        self.edit = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER, pos=(335, 3), size=(400, 32))

        self.AddTool(CmdID.connect.value, "", bmp1, shortHelp="连接远程主机")
        self.AddTool(CmdID.path_parent.value, "", bmp2, shortHelp="上一级目录")
        self.AddTool(CmdID.path_back.value, "", bmp3, shortHelp="回退目录")
        self.AddTool(CmdID.path_forward.value, "", bmp4, shortHelp="前进目录")
        self.AddTool(CmdID.path_list.value, "", bmp5, shortHelp="历史目录")
        self.AddControl(self.edit)

        self.Realize()

        self.Bind(wx.EVT_TOOL, self.OnButton0, id=CmdID.connect.value)
        self.Bind(wx.EVT_MENU, self.OnCommand, id=CmdID.path_parent.value, id2=CmdID.path_list2.value)
        self.Bind(my_EVT_COMMAND_EVENT, self.OnCommand)

        self.Bind(wx.EVT_TEXT_ENTER, self.OnEditEnter, self.edit)

    def OnButton0(self, evt):  # 连接

        hosts = self.host.get_host_list()
        menu = wx.Menu()

        for i, x in enumerate(hosts):
            menu.Append(CmdID.connect1.value + i, x)

        hwnd = self.GetHandle()
        rc = os_ext.Toolbar_GetItemRect(hwnd, 0)
        pt = rc[0], rc[1] + rc[3]

        self.PopupMenu(menu, pt)

    def OnButton4(self):  # 历史
        plist, pos = self.host.get_path_list()

        menu = wx.Menu()

        for i, x in enumerate(plist):
            mi = menu.AppendCheckItem(CmdID.path_list1.value + i, x)
            if i == pos:
                mi.Check()

        hwnd = self.GetHandle()
        rc = os_ext.Toolbar_GetItemRect(hwnd, 4)
        pt = rc[0], rc[1] + rc[3]

        self.PopupMenu(menu, pt)

    def OnCommand(self, evt):  # 路径切换
        cmd = evt.GetId()

        if cmd == CmdID.path_list.value:
            self.OnButton4()
            return

        # 目录历史记录的逻辑
        # 1.目录历史记录是帮助快速切换,不记录重复的目录,不保证原来的访问顺序.
        # 2.之前访问过的目录,再次访问后会移到最后面.
        # 3.回退一次,则切换到记录列表中的上一项(如果有)
        # 4.前进一次,则切换到记录列表中的下一项(如果有)
        # 5.可以点击某个记录项,直接切换.
        # 6.通过3,4,5切换目录,不改变当前目录在记录列表中的顺序,还在原来的位置.
        # 7.如果当前位于列表的中间位置(例如通过3,4,5),再打开新目录,则覆盖后面的记录.

        try:
            if cmd == CmdID.path_parent.value:     # 上一级路径
                self.host.path_parent()

            elif cmd == CmdID.path_back.value:     # 回退
                self.host.path_back()

            elif cmd == CmdID.path_forward.value:  # 前进
                self.host.path_forward()

            elif cmd == CmdID.path_set.value:      # 通过编辑框设置路径,或双击打开路径
                self.host.path_set(evt.path)

            else:                                  # 通过历史记录切换
                pidx = cmd - CmdID.path_list1.value
                self.host.path_switch(pidx)

        except SSHExecuteError as e:
            MessageBox(self, '错误', str(e), wx.ICON_ERROR)

        ds = self.host.get_path_data()
        PostEvent(CmdID.path_load, path=self.host.get_current_path(), data=ds)

    def OnEditEnter(self, evt):
        path = self.edit.GetLineText(0)
        PostEvent(CmdID.path_set, self, path=path)

    def set_path(self, path):
        self.edit.SetLabel(path)


if __name__ == "__main__":
    pass
