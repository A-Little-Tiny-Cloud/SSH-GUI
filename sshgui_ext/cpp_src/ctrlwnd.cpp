// 控件相关

#define WIN32_LEAN_AND_MEAN      // 从 Windows 头中排除极少使用的资料
#include <windows.h>
#include <commctrl.h>
#include "sshgui_export.h"

//编辑框的气泡提示
SSHGUI_EXT_API void Edit_BalloonTip_Show(HWND hEdit, wchar_t * msg)
{
	EDITBALLOONTIP bt;

	::ZeroMemory(&bt, sizeof(bt));
	bt.cbStruct = sizeof(bt);
	bt.pszTitle = L"";
	bt.pszText  = msg;
	bt.ttiIcon  = NULL;

	//Edit_ShowBalloonTip
	::SendMessage(hEdit, EM_SHOWBALLOONTIP, 0, (LPARAM)&bt);
}

SSHGUI_EXT_API void Edit_BalloonTip_Hide(HWND hEdit)
{
	//Edit_HideBalloonTip
	::SendMessage(hEdit, EM_HIDEBALLOONTIP, 0, 0);
}


//返回工具栏Item的矩形框
SSHGUI_EXT_API void Toolbar_GetItemRect(HWND hToolbar, int idx, LPRECT rc)
{
	::SendMessage(hToolbar, TB_GETITEMRECT, (WPARAM)idx, (LPARAM)rc);
}


//设置listview控件某个子项的文本
SSHGUI_EXT_API void ListCtrl_SetItemText(HWND hListCtrl, int idx, int sub, wchar_t * text)
{
	ListView_SetItemText(hListCtrl, idx, sub, text);
}
