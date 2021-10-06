# coding:utf-8

import os
import time
import wx
from common import CmdID, PathData, sizeFormat, timeFormat, PostEvent, my_EVT_COMMAND_EVENT
from transport import SSHExecuteError
from os_win import listview_GetEdit, FileTypeInfo, os_ext


# TextValidator()不可用,只好自己实现.
class MyValidator(wx.Validator):

    def __init__(self):
        wx.Validator.__init__(self)
        self.chars = set(['/', '\\', ':', '*', '<', '>', '|', '?', '"'])
        self.Bind(wx.EVT_CHAR, self.OnChar)  # 绑定字符事件

    def OnChar(self, event):
        key = chr(event.GetKeyCode())
        if key in self.chars:
            hwnd = self.GetWindow().GetHandle()
            os_ext.Edit_ShowBalloonTip(hwnd, '文件名不能包含下列任何字符:\n    \\ / : * ? " < > |')
            return

        event.Skip()

    def Clone(self):
        return MyValidator()

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True


# 文件列表
# 显示文件名和其它文件信息
class FileListWnd(wx.ListCtrl):

    def __init__(self, parent, host):

        wx.ListCtrl.__init__(self, parent, wx.ID_ANY,
                             style=wx.VSCROLL | wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_EDIT_LABELS)

        columns = ["文件名", "修改日期", "权限", "大小"]
        for col, text in enumerate(columns):
            self.InsertColumn(col, text)

        self.SetColumnWidth(0, 300)
        self.SetColumnWidth(1, 160)
        self.SetColumnWidth(2, 120)

        li = wx.ListItem()
        li.SetWidth(160)  # wx.LIST_AUTOSIZE)
        li.SetAlign(wx.LIST_FORMAT_RIGHT)

        self.SetColumn(3, li)

        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_LIST_CACHE_HINT, self.DoCacheItems)
        self.Bind(wx.EVT_CHAR, self.OnChar)

        # self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemEvent)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemEvent)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnItemEvent)
        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnEditBegin)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEditEnd)
        self.Bind(wx.EVT_MENU, self.OnCommand, id=CmdID.open.value, id2=CmdID.last_id.value)
        self.Bind(my_EVT_COMMAND_EVENT, self.OnCommand)

        self.SetItemCount(0)  # 设置列表的大小

        self.data = None

        self.in_edit = False
        self.edit_line = -1
        self.edit_ctrl = None
        self.edit_text = ''
        self.validator = MyValidator()

        self.fti = FileTypeInfo()

        self.SetImageList(self.fti.img_list, wx.IMAGE_LIST_SMALL)
        self.SetLabel('list-ctrl-033')

        self.host = host

    def Load(self, ds: PathData):
        '加载一个目录的文件信息'

        self.DeleteAllItems()

        self.data = ds
        cnt = self.data.GetCount()
        self.SetItemCount(cnt)

    def OnChar(self, event):

        keycode = event.GetKeyCode()

        if keycode == wx.WXK_CONTROL_C:
            PostEvent(CmdID.copy, self)

        elif keycode == wx.WXK_CONTROL_X:
            PostEvent(CmdID.cut, self)

        elif keycode == wx.WXK_CONTROL_V:
            PostEvent(CmdID.paste, self)

        elif keycode == wx.WXK_DELETE:
            PostEvent(CmdID.delete, self)

    def GetLine(self, idx):
        return self.data.flist[idx]

    def GetAllSelected(self):
        '得到当前所有选择的行'

        idx = self.GetFirstSelected()

        lines = []  # 记录选择的多个行号
        while idx != -1:
            lines.append(idx)
            idx = self.GetNextSelected(idx)

        return lines

    def RenameLine(self, idx):
        self.RefreshItem(idx)

    def RemoveLines(self, lines):  # 删除一行
        # 删除一行(对应一个文件或目录),有三步:
        # 1.删除远程主机的磁盘内容
        # 2.更新本机缓存的目录信息
        # 3.删除界面listctrl中的一行
        #
        # 考虑到删除可能失败,必须是先删除磁盘文件,然后删除后台数据,最后更新界面.
        # 如果删除磁盘文件失败,则抛出异常,过程结束,后台数据和界面无需更新.
        # 反之先删除listctrl中的行,若后面删除磁盘文件出问题了,则状态无法统一,必须重新扫描目录!
        #
        # DeleteItem 会减少总行数,但过程会触发更新,而更新时尚未减少总行数.
        # 若删除最后一行, 更新过程会造成访问最后一行数据.
        # 同时, 数据在RemoveLine前已经删除了最后一行(上面第2步), 这样就造成数据访问越界.
        #
        # 目前尚不清楚 DeleteItem 的实现逻辑,但这样的机制逻辑上是有问题的.
        # 已经删除第idx项,为何还更新它(没有考虑第idx项是最后一行时,它已经不存在了)
        # 只能在访问PathData时做一个检查,若越界了,返回None

        lines.sort(reverse=True)  # 排序,从后面往前删,否则删除后位置就不对了.

        for idx in lines:
            self.DeleteItem(idx)

    def DoCacheItems(self, evt):
        self.data.UpdateCache(evt.GetCacheFrom(), evt.GetCacheTo())

    def OnGetItemText(self, item, col):
        fi = self.data.GetItem(item)

        if fi is None:
            return ''

        if col == 0:        # 文件名
            return fi.name
        elif col == 1:      # 日期时间
            return fi.date + ' ' + fi.time
        elif col == 2:      # 权限
            return fi.attri
        elif col == 3:
            if fi.size == -1:
                return ' '
            return str(fi.size)

        return ' '

    def OnGetItemAttr(self, item):
        return None

    def OnGetItemImage(self, item):
        fi = self.data.GetItem(item)
        if fi is None:
            return -1

        return self.fti.get_file_icon(fi)

    def OnRightDown(self, evt):  # 空白处右键

        if self.data is None or self.data.GetCount() == 0:
            return

        idx, flags = self.HitTest(evt.GetPosition())

        if idx == wx.NOT_FOUND or flags == wx.LIST_HITTEST_NOWHERE:

            menu = wx.Menu()

            menu.Append(CmdID.select_all.value, "全选", "选择所有项")

            menu.AppendSeparator()

            menu.Append(CmdID.refresh.value, "刷新", "刷新目录")
            menu.Append(CmdID.new_file.value, "新建文件", "新建")
            menu.Append(CmdID.new_folder.value, "新建目录", "新建文件")
            mi = menu.Append(CmdID.paste.value, "粘贴", "粘贴文件")

            menu.AppendSeparator()

            menu.Append(CmdID.info.value, "属性", "文件属性")

            mi.Enable(os_ext.clipboard_check())

            self.PopupMenu(menu)
        else:
            evt.Skip()

    def OnItemEvent(self, evt):

        if self.data.GetCount() == 0:
            return

        if evt.EventType == wx.EVT_LIST_ITEM_ACTIVATED.typeId:  # 双击或回车
            PostEvent(CmdID.open, self)

        elif evt.EventType == wx.EVT_LIST_ITEM_RIGHT_CLICK.typeId:  # 右键

            lines = self.GetAllSelected()

            menu = wx.Menu()

            if len(lines) == 1:
                menu.Append(CmdID.open.value, "打开", "打开文件")

            menu.Append(CmdID.download.value, "下载", "下载")
            menu.Append(CmdID.saveas.value, "另存为", "文件另存为")

            menu.AppendSeparator()

            menu.Append(CmdID.select_all.value, "全选", "选择所有项")
            menu.Append(CmdID.select_neg.value, "反选", "选择剩余项")

            menu.AppendSeparator()

            if len(lines) == 1:
                menu.Append(CmdID.head.value, "查看头部", "查看文件内容")
                menu.Append(CmdID.tail.value, "查看尾部", "查看文件内容")

                menu.AppendSeparator()

            menu.Append(CmdID.cut.value, "剪切", "剪切文件")
            menu.Append(CmdID.copy.value, "复制", "复制文件")

            menu.AppendSeparator()

            if len(lines) == 1:
                menu.Append(CmdID.link.value, "创建链接", "为当前文件创建软链接")
                menu.Append(CmdID.rename_begin.value, "重命名", "修改名称")
            else:
                menu.Append(CmdID.rename_batch.value, "批量重命名", "批量修改名称")

            menu.Append(CmdID.delete.value, "删除", "删除文件")

            menu.AppendSeparator()

            menu.Append(CmdID.info.value, "属性", "文件属性")

            self.PopupMenu(menu)

    def OnCommand(self, evt):

        cmd = evt.GetId()

        lines = self.GetAllSelected()  # 记录选择的多个行号

        if cmd == CmdID.open.value:
            self.host.open_line(lines[-1])

        elif cmd == CmdID.openfile.value:
            self.host.download(lines[-1])  # 先下载,再打开...
            MessageBox(self, "提示", "该功能目前只完成下载部分", wx.ICON_INFORMATION)

        elif cmd == CmdID.delete.value:

            if len(lines) == 1:
                fi = self.GetLine(lines[0])
                title = '删除文件'
                msg = '删除后无法恢复，确定删除此文件？\n\n' \
                      '文件名: {}\n 大  小: {}\n 修改日期: {} {}'.format(fi.name, fi.size, fi.date, fi.time)

            elif len(lines) > 1:
                fi1 = self.GetLine(lines[0])
                fi2 = self.GetLine(lines[-1])
                title = '删除多个文件'
                msg = '删除后无法恢复，确定删除{}个文件？\n\n'

                if len(lines) == 2:
                    msg = msg + ' {}\n {}'
                else:
                    msg = msg + ' {}\n ...\n {}'

                msg = msg.format(len(lines), fi1.name, fi2.name)

            else:
                return

            if MessageBox(self, title, msg, wx.ICON_INFORMATION | wx.YES_NO) == wx.ID_YES:
                self.host.remove(lines)
                self.RemoveLines(lines)

        elif cmd == CmdID.rename_begin.value:

            assert len(lines) == 1
            self.in_edit = True  # 屏蔽 OnEditBegin 中的操作
            self.edit_line = lines[0]   # 当前编辑行号

            # EditLabel函数发出 EVT_LIST_BEGIN_LABEL_EDIT 事件,请求开始编辑
            # 可以拦截该消息,以禁止或通过某个项的编辑.
            # 该函数返回编辑控件
            self.edit_ctrl = self.EditLabel(self.edit_line)
            self.edit_text = self.edit_ctrl.GetLineText(0)  # 保存原来的文本,以区分是否有修改
            self.edit_ctrl.SetValidator(self.validator)

            self.in_edit = False

        elif cmd == CmdID.rename_batch:
            MessageBox(self, '提示', '批量重命名的功能,目前尚未完成!')

        elif cmd == CmdID.rename_end.value:

            # 编辑完成后,发出 rename_end 命令
            # 到这里已经失去焦点,因此没有任何选中行.
            # 需要的信息必须从evt中获取.

            if self.data.find(evt.new_name) != -1:
                MessageBox(self, '错误', '此位置已经包含同名文件,请使用其它文件名!', wx.ICON_ERROR)
                return

            self.host.rename(evt.old_name, evt.new_name)
            self.RenameLine(evt.line)

        elif cmd == CmdID.download.value:
            self.host.download(lines)

        elif cmd == CmdID.saveas.value:
            pass

        elif cmd == CmdID.cut.value:
            self.host.cut(lines)

        elif cmd == CmdID.copy.value:
            self.host.copy(lines)

        elif cmd == CmdID.paste.value:
            self.host.paste()

        elif cmd == CmdID.info.value:
            pass

        elif cmd == CmdID.refresh.value:
            PostEvent(CmdID.refresh)

    def OnEditBegin(self, evt):
        '''通过'选中+点击'或'右键菜单->重命名'触发编辑消息'''

        if self.in_edit:  # 通过EditLabel函数触发的编辑消息,无需处理
            evt.Skip()
            return

        lines = self.GetAllSelected()  # 记录选择的多个行号

        assert len(lines) == 1

        self.edit_line = lines[0]   # 当前编辑行号
        self.edit_ctrl = listview_GetEdit(self.GetHandle())
        self.edit_text = self.edit_ctrl.GetLineText(0)  # 保存原来的文本,以区分是否有修改
        self.edit_ctrl.SetValidator(self.validator)

    def OnEditEnd(self, evt):

        self.edit_ctrl = None

        text = evt.Text

        if not text or text == '.' or text == '..':
            return

        if self.edit_text != text:
            PostEvent(CmdID.rename_end, self, line=self.edit_line, old_name=self.edit_text, new_name=text)


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


class myToolBar(wx.ToolBar):

    def __init__(self, parent, host):

        wx.ToolBar.__init__(self, parent, wx.ID_ANY, style=wx.TB_FLAT | wx.TB_HORIZONTAL)

        self.host = host

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


def MessageBox(parent, title, msg, style=wx.OK):
    dlg = wx.MessageDialog(parent, msg, title, style=style | wx.CENTRE)
    return dlg.ShowModal()


if __name__ == "__main__":
    app = wx.App()
    MessageBox(None, '测试', '详细信息长文本')
