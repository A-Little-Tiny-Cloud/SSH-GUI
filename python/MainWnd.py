# coding:utf-8
from threading import Thread

import wx
from HostOps import RemoteHost
from transport import SSHExecuteError
from common import CmdID, PostEvent, my_EVT_COMMAND_EVENT
from Dialogs import DlgConnect
from CtrlWnd import FileListWnd, TaskListWnd, myToolBar, MessageBox


# 主框架窗口
class MainFrame(wx.Frame):

    def __init__(self, parent, host):

        style = wx.DEFAULT_FRAME_STYLE | wx.MAXIMIZE_BOX
        wx.Frame.__init__(self, parent, -1, "SSH-GUI", size=(1200, 750), style=style)  # pos=pos

        menu1 = wx.Menu()
        menu1.Append(CmdID.website_mgr.value, "站点管理", "管理站点信息")
        menu1.AppendSeparator()
        menu1.Append(CmdID.new_tab.value, "新标签", "打开站点的新目录")
        menu1.Append(CmdID.close_tab.value, "关闭标签", "关闭当前标签")
        menu1.AppendSeparator()
        m_exit = menu1.Append(wx.ID_CLOSE, "退出", "退出程序 ")

        menu2 = wx.Menu()
        menu2.AppendCheckItem(CmdID.dir_tree.value, "导航", "显示导航窗格")
        menu2.AppendCheckItem(CmdID.view_info.value, "任务窗口", "显示任务窗口")
        menu2.AppendCheckItem(CmdID.view_list.value, "列表模式", "切换到列表模式")
        menu2.AppendCheckItem(CmdID.view_icon.value, "图标模式", "切换到图标模式")

        menu3 = wx.Menu()
        menu3.Append(CmdID.disk_use.value, "磁盘", "查看磁盘使用情况")
        menu3.Append(CmdID.process.value, "进程", "查看进程")
        menu3.Append(CmdID.gpu_info.value, "显卡", "查看显卡使用情况")
        menu3.Append(CmdID.install.value, "安装", "安装软件")
        menu3.Append(CmdID.build.value, "编译", "编译软件")

        menuBar = wx.MenuBar()
        menuBar.Append(menu1, "站点")
        menuBar.Append(menu2, "查看")
        menuBar.Append(menu3, "工具")

        self.SetMenuBar(menuBar)

        self.toolbar = myToolBar(self, host)
        self.SetToolBar(self.toolbar)

        self.splitter = wx.SplitterWindow(self, style=wx.SP_3D | wx.SP_3DSASH | wx.SP_LIVE_UPDATE)

        self.panel = wx.Panel(self.splitter, name="main_panel")
        self.bottom = wx.Panel(self.splitter, name="info_panel")

        self.flist_wnd = FileListWnd(self.panel, host)
        self.info_wnd = TaskListWnd(self.bottom)

        b = wx.BoxSizer(wx.HORIZONTAL)
        b.Add(self.flist_wnd, 1, wx.EXPAND)
        self.panel.SetSizerAndFit(b)

        b2 = wx.BoxSizer(wx.HORIZONTAL)
        b2.Add(self.info_wnd, 1, wx.EXPAND)
        self.bottom.SetSizerAndFit(b2)

        self.splitter.SplitHorizontally(self.panel, self.bottom, 550)

        self.bar = wx.Frame.CreateStatusBar(self, 5)
        self.bar.SetStatusWidths([200, 100, 120, 200, -1])  # 提示信息|模式|当前位置|标注进度|当前文件名
        self.bar.SetStatusText("标注模式", 1)

        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI, id=CmdID.view_info.value)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_MENU, self.OnExit, m_exit)

        self.Bind(wx.EVT_MENU, self.OnCommand, id=CmdID.connect1.value, id2=CmdID.connect2.value)
        self.Bind(wx.EVT_MENU, self.OnCommand, id=CmdID.view_info.value)
        self.Bind(my_EVT_COMMAND_EVENT, self.OnCommand)

        self.Center()

        self.host = host  # RemoteHost()
    # ------------------------------------------------------------------------------------
    # 系统消息

    def OnUpdateUI(self, event):
        event.Check(self.splitter.IsSplit())

    def OnClose(self, event):
        event.Skip()

    def OnExit(self, _):
        self.Close()

    # ------------------------------------------------------------------------------------
    # 响应命令

    def OnConnect(self, idx):

        dlg = DlgConnect(self)

        ret = []
        thread = Thread(target=self.thread_func, args=(idx, dlg, ret))
        thread.start()

        dlg.ShowModal()

        thread.join()

        if ret[0]:  # 连接服务器成功
            self.SetTitle("%s" % self.host.host.name)
            ds = self.host.get_path_data()
            self.toolbar.set_path(self.host.get_current_path())
            self.flist_wnd.Load(ds)

        else:  # 连接失败
            MessageBox(self, "错误", ret[1], wx.ICON_ERROR)

    def thread_func(self, idx, dlg, out):

        try:
            self.host.connect(idx)
            out.append(True)

        except SSHExecuteError as e:
            out.append(False)
            out.append(str(e))

        wx.CallAfter(dlg.CloseDialog)

    def OnCommand(self, evt):

        cmd = evt.GetId()

        if CmdID.connect1.value <= cmd <= CmdID.connect2.value:
            self.OnConnect(cmd - CmdID.connect1.value)
            return

        if cmd == CmdID.view_info.value:
            if self.splitter.IsSplit():
                self.splitter.Unsplit()
            else:
                self.splitter.SplitHorizontally(self.panel, self.bottom, 350)

        elif cmd == CmdID.new_task.value:
            self.info_wnd.add(evt.task)

        elif cmd == CmdID.task_end.value:
            # 这里有bug,应该刷新 任务 关联的远程端目录,而不是当前目录.
            PostEvent(CmdID.refresh, self)

        elif cmd == CmdID.path_load.value:
            self.flist_wnd.Load(evt.data)
            self.toolbar.set_path(evt.path)

        elif cmd == CmdID.refresh.value:  # 刷新
            self.host.refresh()
            ds = self.host.get_path_data()
            self.flist_wnd.Load(ds)

        elif cmd == CmdID.report_error.value:
            MessageBox(self, "错误", evt.msg, wx.ICON_ERROR)


def main():
    host = RemoteHost()
    app = wx.App()
    frame = MainFrame(None, host)
    frame.Show(True)
    app.MainLoop()


if __name__ == "__main__":
    main()
