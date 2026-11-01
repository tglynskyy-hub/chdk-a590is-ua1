"""Compile actual changed C against faults; count navigation work, not camera latency."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'baseline-output'
OUT.mkdir(exist_ok=True)


def function(text, signature):
    start = text.index(signature)
    pos = text.index('{', start)
    depth = 1
    end = pos + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def run(name, code):
    path = OUT / (name + '.c')
    path.write_text(code)
    exe = path.with_suffix('')
    subprocess.run(['gcc', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-variable',
                    '-I', str(ROOT), '-I', str(ROOT / 'include'), str(path), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)


navigation = function((ROOT / 'core/gui_menu.c').read_text(), 'static void gui_menu_updown(int increment)')
baseline = (ROOT / 'tools/a590-baseline/navigation_task004.inc').read_text()
run('navigation-test', r'''
#include <assert.h>
#include <stdio.h>
#include "ui_profile.h"
#define MENUITEM_MASK 15
#define MENUITEM_STATE_VAL_PAIR 13
#define KEY_ZOOM_IN 1
#define KEY_ZOOM_OUT 2
struct {struct {int is_shutter_half_press;} state;} camera_info;
typedef struct {int type,arg;} Item;
struct {Item menu[32];} storage,*curr_menu=&storage;
static int gui_menu_curr_item,gui_menu_top_item,gui_menu_redraw,int_incr,num_lines;
static int n,mask,queries;
static int kbd_is_key_pressed(int key){(void)key;return 0;}
static int gui_menu_rows(void){queries++;return n;}
static int isText(int row){return (mask>>row)&1;}
''' + baseline.replace('gui_menu_updown(', 'old_move(') + '\n' + navigation + r'''
int main(void){
    unsigned cases=0,old_queries=0,new_queries=0;
    for(n=2;n<=10;n++)for(mask=0;mask<(1<<(n-1));mask++)
    for(int initial=-1;initial<n;initial++)for(int dir=-1;dir<=1;dir+=2)
    for(int boost=0;boost<2;boost++){
        camera_info.state.is_shutter_half_press=boost;num_lines=5;
        for(int j=0;j<n;j++){storage.menu[j].type=(j%2)?13:1;storage.menu[j].arg=10;}
        gui_menu_curr_item=initial;gui_menu_top_item=0;gui_menu_redraw=0;int_incr=1;queries=0;
        old_move(dir);int c=gui_menu_curr_item,t=gui_menu_top_item,r=gui_menu_redraw,k=int_incr;
        old_queries+=queries;
        gui_menu_curr_item=initial;gui_menu_top_item=0;gui_menu_redraw=0;int_incr=1;queries=0;
        gui_menu_updown(dir);new_queries+=queries;
        assert(c==gui_menu_curr_item && t==gui_menu_top_item && r==gui_menu_redraw && k==int_incr);
        assert(queries==1);cases++;
    }
    printf("PASS navigation equivalence: %u cases; row-count calls old=%u new=%u (host operation counts, not camera ms)\n",cases,old_queries,new_queries);
}
''')

run('profile-test', r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include "meminfo.h"
static unsigned ticks;
long get_tick_count(void){return ticks;}
void GetMemInfo(cam_meminfo *m){m->free_size=1000;m->free_block_max_size=500;}
static int fail_open,fail_write,fail_close,opens,writes;
static int test_open(const char *name,int flags,int mode){(void)name;(void)flags;(void)mode;opens++;return fail_open?-1:3;}
static int test_write(int fd,const void *b,long n){assert(fd==3);(void)b;writes++;return fail_write?n-1:n;}
static int test_close(int fd){assert(fd==3);return fail_close?-1:0;}
#define open test_open
#define write test_write
#define close test_close
#define OPT_UI_PROFILE 1
#include "core/ui_profile.c"
int main(void){
    ticks=0xfffffff0U;unsigned t=ui_profile_begin();ticks=16;ui_profile_end(UI_PROF_DRAW,t);
    assert(stats[UI_PROF_DRAW].last==32);
    ui_profile_end(-1,0);ui_profile_end(UI_PROF_COUNT,0);
    stats[UI_PROF_MOVE].total=~0U;ticks=1;ui_profile_end(UI_PROF_MOVE,0);assert(!stats[UI_PROF_MOVE].count);
    ticks=100;ui_profile_input();ticks=120;ui_profile_present();ui_profile_present();
    assert(stats[UI_PROF_RESPONSE].count==1 && response_samples[0]==20);
    for(int i=0;i<100;i++){ui_profile_input();ui_profile_present();}
    assert(response_count==64);
    ui_profile_memory(0);ui_profile_root(1);ui_profile_root(1);ui_profile_root(0);
    for(int i=0;i<30;i++)ui_profile_switch();
    assert(sample_count==5 && samples[3].tag==10 && samples[4].tag==30);
    for(int i=0;i<40;i++)ui_profile_memory(100);
    assert(sample_count==32 && dropped==13 && samples[0].memory.allocated_count==-1);
    assert(!opens && !writes);assert(ui_profile_export() && opens==3);
    fail_open=1;assert(!ui_profile_export());fail_open=0;
    fail_write=1;assert(!ui_profile_export());fail_write=0;
    fail_close=1;assert(!ui_profile_export());
    puts("PASS profile: bounded samples, timer wrap/saturation, no hot-path I/O, export faults");
}
''')

conf = (ROOT / 'core/conf.c').read_text()
assert 'if (config_save_checked(' in conf
assert 'if (!config_save_checked(' in conf
run('config-save-test', r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CONF_STRUCT_PTR 7
#define CONF_STR_LEN 100
#define CONF_MAGICK_VALUE 0x33204741
#define O_WRONLY 1
#define O_CREAT 2
#define O_TRUNC 4
typedef struct {int (*saved_size)(void);char *(*save)(char*);} tVarArrayConfig;
typedef struct {unsigned short id,size;} ConfInfoSave;
typedef struct {int id,size,type;void *var;} ConfInfo;
static int fail_alloc,fail_open,short_write,fail_close,opens,frees;
static void *umalloc(int size){return fail_alloc?0:malloc(size);}
static void ufree(void *p){assert(p);frees++;free(p);}
static int open(const char *p,int flags,int mode){(void)p;(void)flags;(void)mode;opens++;return fail_open?-1:3;}
static int write(int fd,const void *b,long n){assert(fd==3);assert(((const int*)b)[0]==CONF_MAGICK_VALUE);return short_write?n-1:n;}
static int close(int fd){assert(fd==3);return fail_close?-1:0;}
''' + function(conf, 'static int config_save_checked(') + r'''
int main(void){
    int value=17;ConfInfo ci[]={{299,sizeof(value),0,&value},{0,0,0,0}};
    fail_alloc=1;assert(!config_save_checked(ci,"cfg",2000) && !opens && !frees);fail_alloc=0;
    fail_open=1;assert(!config_save_checked(ci,"cfg",2000) && frees==1);fail_open=0;
    short_write=1;assert(!config_save_checked(ci,"cfg",2000));short_write=0;
    fail_close=1;assert(!config_save_checked(ci,"cfg",2000));fail_close=0;
    assert(config_save_checked(ci,"cfg",2000));assert(frees==4);
    puts("PASS config save: allocation failure cannot truncate/dereference NULL; open/short write/close faults detected");
}
''')

# Normal object must have no tracing data/code, not just a runtime-disabled flag.
obj = OUT / 'profile-disabled.o'
subprocess.run(['gcc', '-I', str(ROOT/'include'), '-c', str(ROOT/'core/ui_profile.c'), '-o', str(obj)], check=True)
assert not subprocess.check_output(['nm', '--defined-only', str(obj)], text=True).strip()
print('PASS: normal profile object contains no symbols or storage')
