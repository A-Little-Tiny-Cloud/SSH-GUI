### 1. Introduction

SSH-GUI is a gui tool built on ssh. The main function is to use the GUI interface to manage a remote host that only supports ssh.

SSH-GUI hopes that users can use remote linux hosts in a similar way to local windows, while only requiring remote linux hosts to provide ssh connections.

The planned functions of SSH-GUI include:

- General file operations: directory switching, file browsing, file creation, renaming, deleting, copying, pasting, etc.
- File editing: directly open and edit certain types of files; the program maintains a type list, and the operations for each file type are different. For example, double-clicking the txt file will open the Notepad program for editing; double-clicking the image file will display the image; double-clicking the so file will list the dependencies.
- System functions: such as installing software, checking disk usage, process status, etc.

Considering that modern operating systems provide roughly similar functions, the difference is only the use of a command line interface or a graphical interface; mapping the graphical interface to the command line interface or vice versa should work  in theory. The goal of SSH-GUI is to map the command line interface of the remote linux host to the graphical interface of the local windows system, so that users can use the remote linux host without knowing the bash command line;

Although SSH-GUI tries to provide a windows-style interface, there are still some important differences that need to be understood due to different operating systems:
   1. The directory separator in linux is'/' ('\\' in windows)
   2. The file system under linux has no concept of drive letter (such as'C drive','D drive', etc.)
   3. Linux file names are case sensitive (so `Abc.txt` and `abc.txt` are two different files)
   4. The extension of the linux file is not important. For example, the executable file does not have an `.exe` extension, in general, the executable file does not have an extension.
   5. Linux is stricter on file/directory permission management, and you cannot access files of other groups or users unless you have permission.

### 2. dependencies
SSH-GUI is developed using python and uses the following libraries:
-wxPython: program GUI
-paramiko: Provides ssh and sft protocol functions
-pywin32: It is used to provide some additional functions (shell) of windows, which will be replaced by extended dll in the future.

Due to the lack of some functions of wxPython (or difficult to use), the program also uses a dll implemented in C++

### 3. Completed functions
  1. Basic interface
     a. List view (use the icon registered on the local system to represent the file)
     b. Task window
  2. Directory switching/file selection
  3. Open the file (only support system associated files)
  4. Rename/Delete
  5. Upload/download( can be done via menu/copy/cut/paste)

