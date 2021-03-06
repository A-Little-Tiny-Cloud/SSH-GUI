
### 一、介绍

ssh-gui是一个构建在ssh上的gui工具，主要功能是使用gui界面管理一个只支持ssh的远程主机.

ssh-gui希望用户可以用类似于本地windows的方式来使用远程linux主机，同时仅要求远程linux主机提供ssh连接。

ssh-gui的计划功能包括：
- 常规文件操作：目录切换、文件浏览、文件创建、重命名、删除、复制、粘贴等
- 文件编辑：直接打开和编辑某些类型文件; 程序维护一个类型列表，对每种文件类型的操作都不同。例如，双击txt文件会打开记事本程序编辑；双击图像文件会显示图像；双击so文件会列出依赖项。
- 系统功能：如安装软件，查看磁盘使用情况，进程情况等。

考虑到现代操作系统提供的功能大致类似，区别只是使用命令行界面或图形界面；将图形界面映射到命令行界面或者反过来，理论上应该是行得通的。ssh-gui的目标就是将远程linux主机的命令行界面映射到本地windows系统图形界面，这样用户就可以在不了解bash命令行的情况下使用远程linux主机；

虽然ssh-gui尽量提供windows风格的界面，然而由于操作系统的不同，仍有一些重要的差别需要了解：
   1. linux下目录分隔符是'/'（windows下为'\\'）
   2. linux下文件系统没有盘符（如'C盘'，'D盘'等）的概念
   3. linux文件名区分大小写（因此 `Abc.txt`和`abc.txt`是两个不同的文件)
   4. linux文件的扩展名不重要. 例如可执行文件没有`.exe`扩展名, 一般情况下可执行文件都没有扩展名.
   5. linux对文件/目录权限管理较严格，不可以访问其它组或用户的文件，除非你有权限。

### 二、依赖项
ssh-gui目前使用python开发，使用了如下库：
- wxPython: 程序界面
- paramiko: 提供ssh和sft协议功能
- pywin32: 用于提供windows的一些额外功能(shell),后续将使用扩展dll代替.

由于wxPython某些功能的缺失(或者比较难用），程序还使用了一个c++实现的dll

### 三、已完成功能 
  1. 基本界面
     a.列表视图(使用本机系统上注册的图标代表文件)
     b.任务窗口
  2. 目录切换/文件选择
  3. 打开文件(只支持系统已关联文件)
  4. 重命名/删除
  5. 上传/下载(可通过菜单/复制/剪切/粘贴)

