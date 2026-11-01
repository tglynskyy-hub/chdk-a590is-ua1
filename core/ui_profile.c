#include "ui_profile.h"
#ifdef OPT_UI_PROFILE
#include "stdlib.h"
#include "string.h"
#include "meminfo.h"
#include "clock.h"

/* Best-effort aligned counters, never used to control the camera. Event writers
 * can be in different tasks; export while idle. No locks in camera hot paths.
 * Saturation prevents wrap from producing plausible but incorrect long runs. */
typedef struct { unsigned count, total, maximum, last; } profile_stat;
typedef struct { int tag; unsigned tick; cam_meminfo memory; } profile_sample;
#define PROFILE_SAMPLES 32
static profile_stat stats[UI_PROF_COUNT];
static profile_sample samples[PROFILE_SAMPLES];
static unsigned sample_count, dropped, switches, seen_roots;
static volatile unsigned input_tick, input_serial;
static unsigned presented_serial;
static unsigned response_samples[64], response_count;

unsigned ui_profile_begin(void) { return (unsigned)get_tick_count(); }
void ui_profile_end(int event, unsigned start)
{
    if (event < 0 || event >= UI_PROF_COUNT) return;
    unsigned elapsed = (unsigned)get_tick_count() - start;
    profile_stat *s = &stats[event];
    if (s->count == ~0U || elapsed > ~0U - s->total) return;
    s->count++; s->total += elapsed; s->last = elapsed;
    if (elapsed > s->maximum) s->maximum = elapsed;
}
void ui_profile_input(void)
{
    input_tick = get_tick_count();
    input_serial++;
}
void ui_profile_present(void)
{
    unsigned serial = input_serial, tick = input_tick;
    if (serial != presented_serial) {
        if (response_count < 64)
            response_samples[response_count++] = (unsigned)get_tick_count() - tick;
        ui_profile_end(UI_PROF_RESPONSE, tick);
        presented_serial = serial;
    }
}
void ui_profile_memory(int tag)
{
    /* Called by startup or explicit GUI checkpoints, never by drawing/polling. */
    if (sample_count >= PROFILE_SAMPLES) { dropped++; return; }
    profile_sample *s = &samples[sample_count];
    s->tag = tag; s->tick = get_tick_count();
    memset(&s->memory, 0xff, sizeof(s->memory)); // unavailable fields stay -1
    GetMemInfo(&s->memory);
    sample_count++;
}
void ui_profile_root(int mode)
{
    unsigned bit = mode == 1 ? 2 : 1;
    if (!(seen_roots & bit)) {
        seen_roots |= bit;
        ui_profile_memory(mode == 1 ? 1 : 2);
    }
}
void ui_profile_switch(void)
{
    switches++;
    if (switches == 10 || switches == 30) ui_profile_memory((int)switches);
}
static int line_write(int fd, const char *line)
{
    int n = strlen(line);
    return write(fd, line, n) == n;
}
int ui_profile_export(void)
{
    /* Explicit user action only. Fixed names replaced on each export. */
    char line[192];
    int fd = open("A/CHDK/DATA/UISTAT.CSV", O_WRONLY|O_CREAT|O_TRUNC, 0777);
    if (fd < 0) return 0;
    int ok = line_write(fd, "event,count,total_ms,max_ms,last_ms\n");
    int i;
    for (i=0; ok && i<UI_PROF_COUNT; i++) {
        profile_stat s = stats[i];
        sprintf(line, "%d,%u,%u,%u,%u\n", i,s.count,s.total,s.maximum,s.last);
        ok = line_write(fd,line);
    }
    if (close(fd) != 0) ok = 0;
    if (!ok) return 0;
    fd = open("A/CHDK/DATA/UIMEM.CSV", O_WRONLY|O_CREAT|O_TRUNC,0777);
    if (fd < 0) return 0;
    ok = line_write(fd,"tag,tick_ms,free,largest,free_blocks,allocated,peak,alloc_count\n");
    unsigned n = sample_count;
    for (i=0; ok && i<(int)n; i++) {
        profile_sample *s = &samples[i];
        sprintf(line,"%d,%u,%d,%d,%d,%d,%d,%d\n",s->tag,s->tick,
            s->memory.free_size,s->memory.free_block_max_size,s->memory.free_block_count,
            s->memory.allocated_size,s->memory.allocated_peak,s->memory.allocated_count);
        ok = line_write(fd,line);
    }
    sprintf(line,"# dropped=%u,switches=%u\n",dropped,switches);
    if (ok) ok = line_write(fd,line);
    if (close(fd) != 0) ok = 0;
    if (!ok) return 0;
    fd = open("A/CHDK/DATA/UIDELAY.CSV", O_WRONLY|O_CREAT|O_TRUNC,0777);
    if (fd < 0) return 0;
    ok = line_write(fd,"sample,response_ms\n");
    n = response_count;
    for (i=0; ok && i<(int)n; i++) {
        sprintf(line,"%d,%u\n",i,response_samples[i]);
        ok = line_write(fd,line);
    }
    if (close(fd) != 0) ok = 0;
    return ok;
}
#endif
