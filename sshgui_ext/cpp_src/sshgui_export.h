
#ifdef SSHGUI_EXT_EXPORTS
#define SSHGUI_EXT_API extern "C" __declspec(dllexport)
#else
#define SSHGUI_EXT_API extern "C" __declspec(dllimport)
#endif

