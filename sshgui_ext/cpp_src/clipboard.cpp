// 系统剪切板操作(复制粘贴文件)
// 参考:
// https://docs.microsoft.com/en-us/windows/win32/shell/clipboard  微软官方文档
// https://www.cnblogs.com/swarmbees/p/9342585.html
// https://www.topomel.com/archives/1206.html

#define _CRT_SECURE_NO_WARNINGS
#define WIN32_LEAN_AND_MEAN      // 从 Windows 头中排除极少使用的资料
#include <windows.h>
#include <string.h>
#include <shellapi.h>
#include <shlobj.h>
#include <vector>
#include <tuple>
#include "sshgui_export.h"

//自定义格式标记
#define CFSTR_REMOTEFILENAME     TEXT("RemoteFileName")


//文件列表类
//容纳多个文件全路径
class FileList
{
public:

	FileList(int bCut, int bRemote)
	{
		m_bCut = bCut;
		m_bRemote = bRemote;
	}

	~FileList()
	{
		for (auto it : m_buf)
		{
			free(it);
		}

		m_buf.clear();
	}

	void add_file(const wchar_t * filename)
	{
		m_buf.push_back(wcsdup(filename));
	}

	int is_cut()
	{
		return m_bCut;
	}

	int is_remote()
	{
		return m_bRemote;
	}

	int get_count()
	{
		return (int)m_buf.size();
	}

	wchar_t * get_file(int i)
	{
		if (i <= (int)m_buf.size())
			return m_buf[i];

		return nullptr;
	}

	std::tuple<size_t, wchar_t*> pack_to_buf()  //将所有文件名打包为一个缓冲区
	{
		size_t size = 0;
		for (auto x : m_buf)
		{
			size += wcslen(x) + 1;
		}

		size = size * 2 + 2; //最后需要多加一个空字符

		wchar_t * buf = (wchar_t *)malloc(size);
		wchar_t * p = buf;

		for (auto x : m_buf)
		{
			wcscpy(p, x);
			p += wcslen(x) + 1;
		}

		*p = L'\0';

		return std::make_tuple(size, buf);
	}

private:
	int m_bCut;       //是否剪切.
	int m_bRemote;    //是否远程文件.
	std::vector<wchar_t *> m_buf;  //文件名称
};


//将远程文件列表放置到剪切板中
SSHGUI_EXT_API int clipboard_put_files(void * obj)
{
	HGLOBAL hGblEffect;
	UINT uDropEffect = 0;

	{//设置 copy/move 标记

		uDropEffect = RegisterClipboardFormat(CFSTR_PREFERREDDROPEFFECT);
		hGblEffect = GlobalAlloc(GMEM_ZEROINIT | GMEM_MOVEABLE | GMEM_DDESHARE, sizeof(DWORD));

		DWORD * dwDropEffect = (DWORD *)GlobalLock(hGblEffect);

		if (((FileList*)obj)->is_cut())
			*dwDropEffect = DROPEFFECT_MOVE;
		else
			*dwDropEffect = DROPEFFECT_COPY;

		GlobalUnlock(hGblEffect);
	}

	//将自定义的格式按标准格式CF_HDROP存储(前面加DROPFILES结构,后面是文件名串联).
	//读取的时候可以使用 DragQueryFile 解析.
	UINT uFmtRemoteFile = RegisterClipboardFormat(CFSTR_REMOTEFILENAME);

	DROPFILES dropFiles;

	UINT uDropFilesLen = sizeof(DROPFILES);
	dropFiles.pFiles = uDropFilesLen;
	dropFiles.pt.x = 0;
	dropFiles.pt.y = 0;
	dropFiles.fNC = FALSE;
	dropFiles.fWide = TRUE;

	auto info = ((FileList*)obj)->pack_to_buf();  //文件名打包为缓冲区

	UINT uGblLen = uDropFilesLen + std::get<0>(info) + 8;

	HGLOBAL hGblFiles = GlobalAlloc(GMEM_ZEROINIT | GMEM_MOVEABLE | GMEM_DDESHARE, uGblLen);

	char *szData = (char *)GlobalLock(hGblFiles);
	memcpy(szData, (LPVOID)(&dropFiles), uDropFilesLen);

	char * szFileList = szData + uDropFilesLen;
	memcpy(szFileList, std::get<1>(info), std::get<0>(info));

	GlobalUnlock(hGblFiles);

	free(std::get<1>(info));  //释放缓冲区

	if (OpenClipboard(NULL))
	{
		EmptyClipboard();
		SetClipboardData(uFmtRemoteFile, hGblFiles);
		SetClipboardData(uDropEffect, hGblEffect);
		CloseClipboard();
		return 1;
	}

	return 0;
}


//从剪切板读出文件名列表
//注意:支持两种文件名,一种是本机,一种是远程
SSHGUI_EXT_API void * clipboard_get_filelist()
{
	UINT uDropEffect = RegisterClipboardFormat(CFSTR_PREFERREDDROPEFFECT);
	UINT uFmtRemoteFile = RegisterClipboardFormat(CFSTR_REMOTEFILENAME);

	if (OpenClipboard(nullptr))
	{
		int bCut = -1;

		{//读出 CFSTR_PREFERREDDROPEFFECT 数据

			DWORD dwEffect, *dw;
			dw = (DWORD *)(GetClipboardData(uDropEffect));
			if (dw == NULL)
				dwEffect = DROPEFFECT_COPY;
			else
				dwEffect = *dw;

			if (dwEffect & DROPEFFECT_MOVE)
				bCut = 1;
			else if (dwEffect & DROPEFFECT_COPY)
				bCut = 0;
		}

		if (IsClipboardFormatAvailable(uFmtRemoteFile))  //检测是否有特定格式的数据
		{
			HDROP hDrop = (HDROP)GetClipboardData(uFmtRemoteFile);

			if (hDrop)
			{
				FileList * obj = new FileList(bCut, TRUE);

				UINT cFiles = DragQueryFile(hDrop, (UINT)-1, NULL, 0);

				wchar_t szFile[300];

				for (UINT count = 0; count < cFiles; ++count)
				{
					DragQueryFile(hDrop, count, szFile, sizeof(szFile));
					obj->add_file(szFile);
				}

				EmptyClipboard();
				CloseClipboard();

				return obj;
			}
		}

		if (IsClipboardFormatAvailable(CF_HDROP))  // 检查是否有特定格式数据
		{
			HDROP hDrop = (HDROP)GetClipboardData(CF_HDROP);
			if (hDrop)
			{
				FileList * obj = new FileList(bCut, FALSE);

				UINT cFiles = DragQueryFile(hDrop, (UINT)-1, NULL, 0);

				wchar_t szFile[300];

				for (UINT count = 0; count < cFiles; ++count)
				{
					DragQueryFile(hDrop, count, szFile, sizeof(szFile));
					obj->add_file(szFile);
				}

				EmptyClipboard();			
				CloseClipboard();

				return obj;
			}
		}

		CloseClipboard();
	}

	return nullptr;
}

SSHGUI_EXT_API int clipboard_check()
{
	UINT uFmtRemoteFile = RegisterClipboardFormat(CFSTR_REMOTEFILENAME);

	return IsClipboardFormatAvailable(uFmtRemoteFile) || \
		   IsClipboardFormatAvailable(CF_HDROP);
}

SSHGUI_EXT_API void*  filelist_create(int bCut, int bRemote)
{
	return new FileList(bCut, bRemote);
}


SSHGUI_EXT_API void filelist_free(void * obj)
{
	FileList * fl = (FileList *)obj;
	delete fl;
}


SSHGUI_EXT_API void filelist_add(void * obj, wchar_t * file)
{
	FileList * fl = (FileList *)obj;
	fl->add_file(file);
}

SSHGUI_EXT_API int filelist_get_num(void * obj)
{
	FileList * fl = (FileList *)obj;
	return fl->get_count();
}

SSHGUI_EXT_API int filelist_is_cut(void * obj)
{
	FileList * fl = (FileList *)obj;
	return fl->is_cut();
}

SSHGUI_EXT_API int filelist_is_remote(void * obj)
{
	FileList * fl = (FileList *)obj;
	return fl->is_remote();
}

SSHGUI_EXT_API wchar_t * filelist_get_file(void * obj, int i)
{
	FileList * fl = (FileList *)obj;
	return fl->get_file(i);
}
