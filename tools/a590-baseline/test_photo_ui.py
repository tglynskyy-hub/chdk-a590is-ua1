"""Compile real Photography callbacks/menu tables against instrumented host services.

Host pointer-sized menu fields avoid pretending that a 64-bit PC has ARM's ABI.
The complete ARM build checks the real CMenu ABI and all linked callbacks.
"""
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'core/gui_photo.inc').read_text()
conf = (ROOT / 'core/conf.c').read_text()
assert re.search(r'CONF_INFO\(\s*299, conf.photography_ui_mode', conf)
assert 'case 299:' in conf and 'photo_ui_normalize(conf.photography_ui_mode)' in conf
assert 'gui_photo_init_defaults(fresh_osd && !old_config_loaded)' in conf
assert '{3,7}' in (ROOT / 'include/conf.h').read_text()
for filename in ('core/gui.c', 'core/gui_menu.c', 'core/gui_user_menu.c'):
    assert 'gui_get_root_menu()' in (ROOT / filename).read_text()
menu = (ROOT / 'core/gui_menu.c').read_text()
assert menu.index('gui_menu_stack_ptr >= MENUSTACK_MAXDEPTH') < menu.index('gui_menu_stack[gui_menu_stack_ptr].menu =')
assert 'gui_photo_module_available' in menu and 'LANG_PHOTO_MODULE_MISSING' in menu
assert '#include "camera.h"' not in menu  # shared lib/core must remain platform independent
assert not re.search(r'\b(malloc|calloc|shoot|set_focus|SleepTask|while)\s*\(', source)

prefix = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "include/photo_ui_policy.h"
#include "include/ui_profile.h"
#include "core/gui_lang.h"
#define CAM_HAS_IRIS_DIAPHRAGM 1
#define CAM_SD_OVER_IN_MF 1
#define CAM_QUALITY_OVERRIDE 1
#define FONT_CP_WIN_1251 1
#define FONT_CP_WIN_1252 2
#define FONT_CP_WIN 0
#define MBOX_BTN_OK 1
#define MBOX_TEXT_CENTER 2
typedef struct { int symbol,text,type; void *value; intptr_t arg; } CMenuItem;
typedef struct { int symbol,title; CMenuItem *menu; } CMenu;
#define MENU_ITEM(s,t,k,v,a) {s,t,k,(void*)(v),(intptr_t)(a)}
#define MENU_ENUM2(s,t,v,a) MENU_ITEM(s,t,MENUITEM_ENUM2,v,a)
struct {int photography_ui_mode,font_cp,tv_enum_type,override_disable,raw_nr,fast_image_quality,save_raw,dng_raw; char lang_file[100],menu_rbf_file[100];} conf;
struct {struct {int state_kbd_script_run;} state;} camera_info;
static int saved, saves, restored, errors, loads, language_calls;
static int marker, language_file=1, lua_file=1, script_file=1;
static CMenu *current;
static char loaded[100];
static int stat(const char *path, void *unused) {
    (void)unused;
    if (!strcmp(path,PHOTO_UI_PROFILE_MARKER)) return marker?0:-1;
    if (!strcmp(path,"A/CHDK/LANG/ukrainian.lng")) return language_file?0:-1;
    if (!strcmp(path,"A/CHDK/MODULES/lua.flt")) return lua_file?0:-1;
    if (strstr(path,"A/CHDK/SCRIPTS/")) return script_file?0:-1;
    return -1;
}
static void conf_save(void){ saved=conf.photography_ui_mode; saves++; }
static void gui_menu_init(CMenu *m){if(m)current=m;}
static void gui_set_need_restore(void){restored++;}
static void font_set(int cp){assert(cp==conf.font_cp);}
static void rbf_load_from_file(const char *p,int cp){assert(!*p && cp==FONT_CP_WIN);}
void gui_lang_init(void){language_calls++;}
static void gui_mbox_init(int title,int msg,int flags,void *cb){(void)title;(void)msg;(void)flags;(void)cb;errors++;}
static void gui_menu_cancel_redraw(void){}
static void save_params_values(int n){assert(n==0);}
static void script_load(const char *p){loads++;strcpy(loaded,p);}
static void cb_change_dng(void){}
static void gui_draw_fselect(int n){(void)n;}
static void gui_show_build_info(int n){(void)n;}
static CMenu root_menu,raw_submenu,histo_submenu,zebra_submenu,bracketing_in_continuous_submenu,autoiso_submenu,raw_ev_histo_submenu,dof_submenu,edge_overlay_submenu,script_submenu,osd_submenu,menu_settings_submenu,chdk_settings_menu;
static CMenuItem iso_override_items[2],tv_override_evstep[2],av_override_items[2],sd_override_items[2];
static const char *gui_tv_enum_type[]={"Ev Step"},*gui_override_disable_modes[]={"No"},*gui_raw_nr_modes[]={"Auto"},*gui_fast_image_quality_modes[]={"Fine"};
'''
# Share the actual type/flag constants, not duplicate numbers in the harness.
header = (ROOT / 'core/gui_menu.h').read_text()
prefix += '\n'.join(re.findall(r'^#define MENUITEM_\w+\s+0?x?[0-9a-fA-F]+', header, re.M)) + '\n'
suffix = r'''
int main(void) {
    assert(gui_get_root_menu()==&root_menu);
    marker=1;gui_photo_init_defaults(1);
    assert(gui_get_root_menu()==&photo_root_menu && conf.font_cp==FONT_CP_WIN_1251 && saves==0);
    assert(strstr(conf.lang_file,"ukrainian.lng"));
    for(int i=0;i<100;i++) {
        gui_photo_switch(i%2);
        assert(saved==i%2 && current==gui_get_root_menu());
        conf.photography_ui_mode=saved;gui_photo_init_defaults(0);
        assert(conf.photography_ui_mode==saved);
    }
    conf.photography_ui_mode=99;gui_photo_init_defaults(0);assert(conf.photography_ui_mode==0);
    marker=0;gui_photo_init_defaults(1);assert(conf.photography_ui_mode==0);
    gui_photo_language(0);assert(!conf.lang_file[0] && conf.font_cp==FONT_CP_WIN_1252);
    language_file=0;int e=errors;gui_photo_language(1);assert(errors==e+1 && !conf.lang_file[0]);
    marker=1;gui_photo_init_defaults(1);assert(conf.photography_ui_mode==1 && !conf.lang_file[0]);
    language_file=1;gui_photo_language(1);assert(conf.font_cp==FONT_CP_WIN_1251);
    int unchanged_saves=saves, unchanged_lang=language_calls;
    gui_photo_language(1);gui_photo_switch(conf.photography_ui_mode);
    assert(saves==unchanged_saves && language_calls==unchanged_lang);
    assert(!gui_photo_module_available(0) && !gui_photo_module_available(""));
    assert(!gui_photo_module_available("calend.flt"));
    assert(gui_photo_module_available("lua.flt") && gui_photo_module_available("A/CHDK/MODULES/lua.flt"));
    char longname[150];memset(longname,'x',149);longname[149]=0;assert(!gui_photo_module_available(longname));
    lua_file=0;gui_photo_script(0);assert(!loads);lua_file=1;
    script_file=0;gui_photo_script(0);assert(!loads);script_file=1;
    gui_photo_script(-1);gui_photo_script(3);assert(!loads);
    for(int i=0;i<3;i++){gui_photo_script(i);assert(current==&script_submenu);}
    assert(loads==3 && strstr(loaded,"motion.lua"));
    camera_info.state.state_kbd_script_run=1;int old=conf.photography_ui_mode;
    gui_photo_switch(0);gui_photo_script(0);assert(conf.photography_ui_mode==old && loads==3);
    CMenu *menus[]={&photo_root_menu,&photo_shoot_menu,&photo_exposure_menu,&photo_focus_menu,&photo_smart_menu,&photo_settings_menu,&photo_quick_menu};
    for(unsigned m=0;m<sizeof(menus)/sizeof(menus[0]);m++) {
        int i=0;
        for(;menus[m]->menu[i].text;i++) {
            assert(i<16);
            CMenuItem *it=&menus[m]->menu[i];int type=it->type & MENUITEM_MASK;
            assert(it->text>0 && it->text<=GUI_LANG_ITEMS);
            if(type!=MENUITEM_UP && type!=MENUITEM_WARNING)assert(it->value);
        }
        assert(i>0);
        if(m)assert(menus[m]->menu[i-1].type==MENUITEM_UP);
    }
    assert(photo_root_items[0].text==LANG_PHOTO_SHOOT && photo_root_items[4].text==LANG_PHOTO_SETTINGS);
    assert(photo_root_items[6].value==(void*)gui_photo_switch && photo_root_items[6].arg==PHOTO_UI_CLASSIC);
    puts("PASS: real C callbacks/tables, 100 switches, restore policy, missing files/modules, script guard, seven menus");
    return 0;
}
'''
out = ROOT / 'baseline-output/photo-ui-host.c'
out.parent.mkdir(exist_ok=True)
out.write_text(prefix + '\n#include "core/gui_photo.inc"\n' + suffix)
gcc = shutil.which('gcc')
if not gcc:
    raise SystemExit('Host gcc required; run in pinned build container')
exe = out.with_suffix('')
subprocess.run([gcc, '-std=c99', '-Wall', '-Wextra', '-Werror', '-I', str(ROOT), str(out), '-o', str(exe)], check=True)
subprocess.run([str(exe)], check=True)
