# coding:utf-8

import wx
from wx.adv import Animation, AnimationCtrl


class DlgConnect(wx.Dialog):

    def __init__(self, parent):

        wx.Dialog.__init__(self, parent, wx.ID_ANY, "请稍候", size=(400, 300), style=wx.BORDER_DEFAULT | wx.CAPTION)

        panel = wx.Panel(self)

        gif = Animation('res/loading.gif')

        sz1 = self.GetClientSize()
        sz2 = gif.GetSize()
        x = (sz1.x - sz2.x)//2
        y = (sz1.y - sz2.y)//2 - 20

        animation = AnimationCtrl(panel, -1, gif, pos=(x, y))
        animation.Play()

        txt = wx.StaticText(panel, -1, '正在连接服务器,请等待...', (0, 0))
        sz3 = txt.GetSize()
        x = (sz1.x - sz3.x)//2
        y = y + sz2.y + 10

        txt.Move((x, y))

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.Centre()

    def OnClose(self, _):
        pass

    def CloseDialog(self):
        self.EndModal(wx.ID_CANCEL)


#########################################################################################################


if __name__ == "__main__":

    app = wx.App()  # 必须使用app对象,初始化 wx 库.
#   app.MainLoop()  # 对话框为主窗口不必使用主消息循环

    if 1:
        dlg = DlgConnect(None)
        dlg.ShowModal()
