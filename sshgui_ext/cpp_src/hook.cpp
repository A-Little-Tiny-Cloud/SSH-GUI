#include <windows.h>
#include <string.h>
#include <stdio.h>
//#include <fstream.h>

#include "include/detours.h"

#include "sshgui_export.h"

#pragma comment(lib, "detours.lib")
//#pragma comment(lib, "detoured.lib")

//ָ��MessageBox������ָ��
int (WINAPI *SysMessageBox)(HWND hWnd, LPCTSTR lpText, LPCTSTR lpCaption, UINT uType)
= MessageBox;

//�ػ������ʵ��ִ�еĺ���,�����Ȱ����ݼ�¼��һ���ı���Ȼ����ŵ���ԭ����MessageBox����ȥ���Ǹ���,�����滻������
int WINAPI MyMessageBox(HWND hWnd, LPCTSTR lpText, LPCTSTR lpCaption, UINT uType)
{
	printf("******** MyMessageBox ********");

	return SysMessageBox(hWnd, L"�˺����Ѿ�������", lpCaption, uType);
}


HANDLE (WINAPI * sys_CreateFile)(
	LPCTSTR lpFileName,
	DWORD dwDesiredAccess,
	DWORD dwShareMode,
	LPSECURITY_ATTRIBUTES lpSecurityAttributes,
	DWORD dwCreationDisposition,
	DWORD dwFlagsAndAttributes,
	HANDLE hTemplateFile
) = CreateFileW;


HANDLE WINAPI my_CreateFile(
	LPCTSTR lpFileName,
	DWORD dwDesiredAccess,
	DWORD dwShareMode,
	LPSECURITY_ATTRIBUTES lpSecurityAttributes,
	DWORD dwCreationDisposition,
	DWORD dwFlagsAndAttributes,
	HANDLE hTemplateFile
	)
{
	printf("******** my_CreateFile ********");

	return sys_CreateFile(lpFileName, dwDesiredAccess, dwShareMode, lpSecurityAttributes, dwCreationDisposition, dwFlagsAndAttributes, hTemplateFile);
}

SSHGUI_EXT_API void Hook()
{
	printf("******** Hook 111********");

	DetourTransactionBegin();
	DetourUpdateThread(GetCurrentThread());
	DetourAttach(&(PVOID&)CreateFileW, sys_CreateFile);
	DetourTransactionCommit();

	printf("******** Hook 222********");
}

SSHGUI_EXT_API void Unhook()
{
	DetourTransactionBegin();
	DetourUpdateThread(GetCurrentThread());
	DetourDetach(&(PVOID&)SysMessageBox, MyMessageBox);
	DetourTransactionCommit();
}

int main()
{
	//GetFinalPathNameByHandle();

	MessageBox(NULL, L"AAAAAAAAAA", L"", MB_OK);
	Hook();
	MessageBox(NULL, L"AAAAAAAAAA", L"", MB_OK);
	Unhook();
	MessageBox(NULL, L"AAAAAAAAAA", L"", MB_OK);
	return 0;
}

