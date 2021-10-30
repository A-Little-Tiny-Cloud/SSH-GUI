# coding:utf-8

import os
import time
import wx
from common import CmdID, sizeFormat, timeFormat, PostEvent
from os_win import os_ext


# 任务列表
# 显示传输任务信息
class TaskListWnd(wx.ListCtrl):

    cmd_open_src_path = 300
    cmd_open_dst_path = 301
    cmd_task_pause = 302
    cmd_task_resume = 303
    cmd_task_del = 304

    def __init__(self, parent):

        wx.ListCtrl.__init__(self, parent, wx.ID_ANY,
                             style=wx.VSCROLL | wx.LC_REPORT | wx.LC_SINGLE_SEL)

        columns = ["开始时间", "类型", "源", "目标", "总大小", "进度(%)", "已耗时/剩余时间", "平均速度"]
        for col, text in enumerate(columns):
            self.InsertColumn(col, text)

        self.SetColumnWidth(0, 150)
        self.SetColumnWidth(1, 100)
        self.SetColumnWidth(2, 200)
        self.SetColumnWidth(3, 200)
        self.SetColumnWidth(4, 80)
        self.SetColumnWidth(5, 100)
        self.SetColumnWidth(6, 150)
        self.SetColumnWidth(7, 120)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTimerEvent)
        self.timer.Start(1000)

        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemEvent)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnItemEvent)

        self.Bind(wx.EVT_MENU, self.OnCommand, id=self.cmd_open_src_path, id2=self.cmd_task_del)

        self.tasks = []

    def OnTimerEvent(self, evt):
        '定时刷新任务信息'

        n = self.GetItemCount()

        for i in range(n):

            if self.GetItemData(i) == 303:  # skip dead task
                continue

            task = self.tasks[i]

            if self.GetItemText(i, 4) == '未知' and task.get_size() >= 0:
                os_ext.ListCtrl_SetItemText(self.GetHandle(), i, 4, sizeFormat(task.get_size()))

            prg = "完成" if task.is_end() else "%.2f" % task.get_progreess()
            os_ext.ListCtrl_SetItemText(self.GetHandle(), i, 5, prg)

            consume, remain, speed = task.get_time()

            if task.is_end():
                remain = 0

            consume = timeFormat(consume)
            remain = timeFormat(remain)

            os_ext.ListCtrl_SetItemText(self.GetHandle(), i, 6, "%s/%s" % (consume, remain))
            os_ext.ListCtrl_SetItemText(self.GetHandle(), i, 7, sizeFormat(speed))

            if task.is_end():
                self.SetItemData(i, 303)  # magic num for task end
                PostEvent(CmdID.task_end, task_id=task.id)

    def add(self, task):
        '添加一个新任务'

        self.tasks.append(task)

        begin = time.strftime('%y-%m-%d-%H:%M:%S', time.localtime(task.begin))

        if task.get_size() < 0:
            sz = '未知'
        else:
            sz = sizeFormat(task.get_size())

        self.Append((begin, task.type, task.src, task.dst, sz, '0', '-/-', '-'))

    def OnRightDown(self, evt):  # 空白处右键

        if self.GetItemCount() == 0:
            return

        idx, flags = self.HitTest(evt.GetPosition())

        if idx == wx.NOT_FOUND or flags == wx.LIST_HITTEST_NOWHERE:
            pass

        else:
            evt.Skip()

    def OnItemEvent(self, evt):

        if self.GetItemCount() == 0:
            return

        if evt.EventType == wx.EVT_LIST_ITEM_ACTIVATED.typeId:  # 双击或回车
            pass

        elif evt.EventType == wx.EVT_LIST_ITEM_RIGHT_CLICK.typeId:  # 右键

            menu = wx.Menu()

            menu.Append(self.cmd_open_src_path, "打开源目录")
            menu.Append(self.cmd_open_dst_path, "打开目标目录")
            menu.Append(self.cmd_task_pause, "暂停下载")
            menu.Append(self.cmd_task_del, "删除任务")
            menu.AppendSeparator()

            self.PopupMenu(menu)

    def OnCommand(self, evt):

        cmd = evt.GetId()
        idx = self.GetFirstSelected()
        task = self.tasks[idx]

        if cmd == self.cmd_open_src_path:
            if task.type == 'download':
                PostEvent(CmdID.path_set, self, path=task.src)
            else:
                os.system('explorer {}'.format(task.dst))

        elif cmd == self.cmd_open_dst_path:

            if task.type == 'download':
                os.system('explorer {}'.format(task.dst))
            else:
                PostEvent(CmdID.path_set, self, path=task.src)

        elif cmd == self.cmd_task_pause:
            pass

        elif cmd == self.cmd_task_resume:
            pass

        elif cmd == self.cmd_task_del:
            pass


if __name__ == "__main__":
    pass
