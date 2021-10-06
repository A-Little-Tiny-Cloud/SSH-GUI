
#define WIN32_LEAN_AND_MEAN      // 从 Windows 头中排除极少使用的资料
#include <windows.h>
#include <shellapi.h>
#include "sshgui_export.h"

SSHGUI_EXT_API void shell_open_and_wait(wchar_t * file)
{
	SHELLEXECUTEINFO sei;
	memset(&sei, 0, sizeof(SHELLEXECUTEINFO));

	sei.cbSize = sizeof(SHELLEXECUTEINFO);
	sei.fMask = SEE_MASK_NOCLOSEPROCESS;
	sei.lpVerb = L"open";
	sei.lpFile = file;
	sei.nShow = SW_SHOWDEFAULT;

	ShellExecuteEx(&sei);

	if (sei.hProcess)
	{
		WaitForSingleObject(sei.hProcess, INFINITE);
		CloseHandle(sei.hProcess);
	}
}
