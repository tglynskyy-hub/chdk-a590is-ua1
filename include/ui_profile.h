#ifndef UI_PROFILE_H
#define UI_PROFILE_H
/* Opt-in diagnostic build only. No allocation, file I/O or timer calls in normal builds. */
enum { UI_PROF_INIT, UI_PROF_DRAW, UI_PROF_MOVE, UI_PROF_RESPONSE,
       UI_PROF_SAVE, UI_PROF_MODULE_LOAD, UI_PROF_MODULE_UNLOAD, UI_PROF_COUNT };
#ifdef OPT_UI_PROFILE
unsigned ui_profile_begin(void);
void ui_profile_end(int event, unsigned start);
void ui_profile_input(void);
void ui_profile_present(void);
void ui_profile_memory(int tag);
void ui_profile_root(int mode);
void ui_profile_menu(const void *menu);
void ui_profile_switch(void);
int ui_profile_export(void);
#else
#define ui_profile_begin() 0U
#define ui_profile_end(event,start) ((void)(start))
#define ui_profile_input() ((void)0)
#define ui_profile_present() ((void)0)
#define ui_profile_memory(tag) ((void)0)
#define ui_profile_root(mode) ((void)0)
#define ui_profile_menu(menu) ((void)0)
#define ui_profile_switch() ((void)0)
#endif
#endif
