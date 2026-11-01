/* A590 Photography UI. Included by gui.c after the Classic menu definitions.
 * Only tables and on-demand callbacks; no task, polling loop or framebuffer.
 * Host tests include this same file with camera services replaced by stubs.
 */
static CMenu photo_root_menu;

CMenu* gui_get_root_menu()
{
    ui_profile_root(conf.photography_ui_mode);
    return photo_ui_normalize(conf.photography_ui_mode) == PHOTO_UI_PHOTOGRAPHY
        ? &photo_root_menu : &root_menu;
}

static void gui_photo_switch(int mode)
{
    // No switching while script callbacks/RAW hooks own camera state.
    if (camera_info.state.state_kbd_script_run)
        return;
    int next = photo_ui_normalize(mode);
    if (next != conf.photography_ui_mode) {
        conf.photography_ui_mode = next;
        conf_save();
        ui_profile_switch();
    }
    gui_menu_init(gui_get_root_menu()); // resets navigation stack
    gui_set_need_restore();
}

static void photo_set_language(int ukrainian)
{
    // Explicit selection uses the built-in font with verified CP1251 glyphs.
    if (ukrainian)
        strcpy(conf.lang_file, "A/CHDK/LANG/ukrainian.lng");
    else
        conf.lang_file[0] = 0; // compiled English, available even without LANG files
    conf.font_cp = ukrainian ? FONT_CP_WIN_1251 : FONT_CP_WIN_1252;
    conf.menu_rbf_file[0] = 0;
    font_set(conf.font_cp);
    rbf_load_from_file(conf.menu_rbf_file, FONT_CP_WIN);
    gui_lang_init();
}

static void gui_photo_language(int ukrainian)
{
    if (ukrainian && stat("A/CHDK/LANG/ukrainian.lng", 0) != 0)
    {
        gui_mbox_init(LANG_ERROR, LANG_PHOTO_FILE_MISSING, MBOX_BTN_OK|MBOX_TEXT_CENTER, 0);
        return;
    }
    // Re-selecting the active built-in language needs no allocations or SD writes.
    if (!conf.menu_rbf_file[0] &&
        ((ukrainian && conf.font_cp == FONT_CP_WIN_1251 && !strcmp(conf.lang_file, "A/CHDK/LANG/ukrainian.lng")) ||
         (!ukrainian && conf.font_cp == FONT_CP_WIN_1252 && !conf.lang_file[0])))
        return;
    photo_set_language(ukrainian);
    conf_save();
    gui_menu_init(0); // retain current menu, recompute font metrics
    gui_set_need_restore();
}

void gui_photo_init_defaults(int fresh)
{
    // Only read the package marker once during a fresh configuration startup.
    int photo_package = fresh && stat(PHOTO_UI_PROFILE_MARKER, 0) == 0;
    conf.photography_ui_mode = photo_ui_initial_mode(conf.photography_ui_mode, fresh, photo_package);
    if (fresh && photo_package && stat("A/CHDK/LANG/ukrainian.lng", 0) == 0)
        photo_set_language(1);
    // Changes remain dirty for normal conf_save; do not write SD during startup.
}

int gui_photo_module_available(const char *name)
{
    char path[100];
    if (!name || !*name)
        return 0;
    if ((name[0] == 'A' || name[0] == 'a') && name[1] == '/')
    {
        if (strlen(name) >= sizeof(path)) return 0;
        strcpy(path, name);
    }
    else
    {
        if (strlen(name) + sizeof("A/CHDK/MODULES/") > sizeof(path)) return 0;
        strcpy(path, "A/CHDK/MODULES/");
        strcat(path, name);
    }
    return stat(path, 0) == 0;
}

static void gui_photo_script(int index)
{
    // Existing upstream examples, not promised Smart/Stack modes.
    static const char *paths[] = {"A/CHDK/SCRIPTS/hdr.lua", "A/CHDK/SCRIPTS/interval.lua", "A/CHDK/SCRIPTS/motion.lua"};
    if (index < 0 || index >= (int)(sizeof(paths)/sizeof(paths[0])) || camera_info.state.state_kbd_script_run)
        return;
    if (!gui_photo_module_available("lua.flt") || stat(paths[index], 0) != 0)
    {
        gui_mbox_init(LANG_ERROR, LANG_PHOTO_FILE_MISSING, MBOX_BTN_OK|MBOX_TEXT_CENTER, 0);
        return;
    }
    gui_menu_cancel_redraw();
    save_params_values(0);
    script_load(paths[index]);
    gui_menu_init(&script_submenu);
    gui_set_need_restore();
    // Loading never takes a picture. Existing full-shutter-in-ALT starts/stops it.
}

static void gui_photo_script_help(__attribute__((unused)) int arg)
{
    gui_mbox_init(LANG_PHOTO_SMART, LANG_PHOTO_SCRIPT_HELP, MBOX_BTN_OK|MBOX_TEXT_CENTER, 0);
}

static void gui_photo_macro_help(__attribute__((unused)) int arg)
{
    gui_mbox_init(LANG_PHOTO_FOCUS, LANG_PHOTO_MACRO_TEXT, MBOX_BTN_OK|MBOX_TEXT_CENTER, 0);
}

static CMenuItem photo_shoot_items[] = {
    MENU_ITEM(0x24,LANG_PHOTO_RAW_DNG, MENUITEM_SUBMENU, &raw_submenu, 0),
    MENU_ITEM(0x74,LANG_PHOTO_ISO, MENUITEM_STATE_VAL_PAIR, &iso_override_items, 10),
    MENU_ENUM2(0x59,LANG_MENU_TV_ENUM_TYPE, &conf.tv_enum_type, gui_tv_enum_type),
    MENU_ITEM(0x61,LANG_MENU_OVERRIDE_TV_VALUE, MENUITEM_STATE_VAL_PAIR, &tv_override_evstep, 0),
#if CAM_HAS_IRIS_DIAPHRAGM
    MENU_ITEM(0x62,LANG_PHOTO_APERTURE, MENUITEM_STATE_VAL_PAIR, &av_override_items, 0),
#endif
    MENU_ENUM2(0x5f,LANG_MENU_OVERRIDE_DISABLE, &conf.override_disable, gui_override_disable_modes),
    MENU_ENUM2(0x5f,LANG_MENU_RAW_NOISE_REDUCTION, &conf.raw_nr, gui_raw_nr_modes),
#if CAM_QUALITY_OVERRIDE
    MENU_ENUM2(0x5c,LANG_MENU_MISC_IMAGE_QUALITY, &conf.fast_image_quality, gui_fast_image_quality_modes),
#endif
    MENU_ITEM(0x51,LANG_MENU_BACK, MENUITEM_UP, 0, 0), {0}
};
static CMenu photo_shoot_menu = {0x21,LANG_PHOTO_SHOOT,photo_shoot_items};

static CMenuItem photo_exposure_items[] = {
    MENU_ITEM(0x25,LANG_MENU_MAIN_HISTO_PARAM, MENUITEM_SUBMENU, &histo_submenu, 0),
    MENU_ITEM(0x26,LANG_MENU_MAIN_ZEBRA_PARAM, MENUITEM_SUBMENU, &zebra_submenu, 0),
    MENU_ITEM(0x2c,LANG_MENU_BRACKET_IN_CONTINUOUS, MENUITEM_SUBMENU, &bracketing_in_continuous_submenu, 0),
    MENU_ITEM(0x2d,LANG_MENU_AUTOISO, MENUITEM_SUBMENU, &autoiso_submenu, 0),
    MENU_ITEM(0x25,LANG_MENU_RAW_EV_HISTO_TITLE, MENUITEM_SUBMENU, &raw_ev_histo_submenu, 0),
    MENU_ITEM(0x51,LANG_MENU_BACK, MENUITEM_UP, 0, 0), {0}
};
static CMenu photo_exposure_menu = {0x25,LANG_PHOTO_EXPOSURE,photo_exposure_items};

static CMenuItem photo_focus_items[] = {
    MENU_ITEM(0,LANG_PHOTO_FOCUS_NOTE, MENUITEM_WARNING, 0, 0),
#if CAM_SD_OVER_IN_AF || CAM_SD_OVER_IN_AFL || CAM_SD_OVER_IN_MF
    MENU_ITEM(0x5e,LANG_MENU_OVERRIDE_SUBJ_DIST_VALUE, MENUITEM_STATE_VAL_PAIR, &sd_override_items, 0),
#endif
    MENU_ITEM(0x31,LANG_MENU_DOF_TITLE, MENUITEM_SUBMENU, &dof_submenu, 0),
    MENU_ITEM(0x7f,LANG_MENU_EDGE_OVERLAY, MENUITEM_SUBMENU, &edge_overlay_submenu, 0),
    MENU_ITEM(0x80,LANG_PHOTO_MACRO_HELP, MENUITEM_PROC, gui_photo_macro_help, 0),
    MENU_ITEM(0x51,LANG_MENU_BACK, MENUITEM_UP, 0, 0), {0}
};
static CMenu photo_focus_menu = {0x31,LANG_PHOTO_FOCUS,photo_focus_items};

static CMenuItem photo_smart_items[] = {
    MENU_ITEM(0x27,LANG_MENU_MAIN_SCRIPT_PARAM, MENUITEM_SUBMENU, &script_submenu, 0),
    MENU_ITEM(0x27,LANG_PHOTO_HDR, MENUITEM_PROC, gui_photo_script, 0),
    MENU_ITEM(0x27,LANG_PHOTO_INTERVAL, MENUITEM_PROC, gui_photo_script, 1),
    MENU_ITEM(0x27,LANG_PHOTO_MOTION, MENUITEM_PROC, gui_photo_script, 2),
    MENU_ITEM(0x80,LANG_PHOTO_SCRIPT_GUIDE, MENUITEM_PROC, gui_photo_script_help, 0),
    MENU_ITEM(0x51,LANG_MENU_BACK, MENUITEM_UP, 0, 0), {0}
};
static CMenu photo_smart_menu = {0x27,LANG_PHOTO_SMART,photo_smart_items};

#ifdef OPT_UI_PROFILE
static void gui_photo_checkpoint(int arg) { ui_profile_memory(100 + arg); }
static void gui_photo_export(int arg) {
    (void)arg;
    gui_mbox_init(LANG_PHOTO_DIAGNOSTICS,
        ui_profile_export() ? LANG_PHOTO_EXPORT_OK : LANG_PHOTO_EXPORT_FAIL,
        MBOX_BTN_OK|MBOX_TEXT_CENTER, 0);
}
static CMenuItem photo_diagnostic_items[] = {
    MENU_ITEM(0,LANG_PHOTO_MEMORY_SAMPLE,MENUITEM_PROC,gui_photo_checkpoint,0),
    MENU_ITEM(0,LANG_PHOTO_AFTER_LUA,MENUITEM_PROC,gui_photo_checkpoint,1),
    MENU_ITEM(0,LANG_PHOTO_IDLE_SAMPLE,MENUITEM_PROC,gui_photo_checkpoint,2),
    MENU_ITEM(0,LANG_PHOTO_EXPORT,MENUITEM_PROC,gui_photo_export,0),
    MENU_ITEM(0x51,LANG_MENU_BACK,MENUITEM_UP,0,0), {0}
};
static CMenu photo_diagnostic_menu = {0,LANG_PHOTO_DIAGNOSTICS,photo_diagnostic_items};
#endif
static CMenuItem photo_settings_items[] = {
#ifdef OPT_UI_PROFILE
    MENU_ITEM(0,LANG_PHOTO_DIAGNOSTICS,MENUITEM_SUBMENU,&photo_diagnostic_menu,0),
#endif
    MENU_ITEM(0x20,LANG_PHOTO_CLASSIC, MENUITEM_PROC, gui_photo_switch, PHOTO_UI_CLASSIC),
    MENU_ITEM(0x35,LANG_PHOTO_UKRAINIAN, MENUITEM_PROC, gui_photo_language, 1),
    MENU_ITEM(0x35,LANG_PHOTO_ENGLISH, MENUITEM_PROC, gui_photo_language, 0),
    MENU_ITEM(0x22,LANG_MENU_MAIN_OSD_PARAM, MENUITEM_SUBMENU, &osd_submenu, 0),
    MENU_ITEM(0x28,LANG_MENU_MENU_SETTINGS, MENUITEM_SUBMENU, &menu_settings_submenu, 0),
    MENU_ITEM(0x28,LANG_MENU_CHDK_SETTINGS, MENUITEM_SUBMENU, &chdk_settings_menu, 0),
    MENU_ITEM(0x35,LANG_MENU_MISC_FILE_BROWSER, MENUITEM_PROC, gui_draw_fselect, 0),
    MENU_ITEM(0x80,LANG_MENU_MISC_BUILD_INFO, MENUITEM_PROC, gui_show_build_info, 0),
    MENU_ITEM(0x51,LANG_MENU_BACK, MENUITEM_UP, 0, 0), {0}
};
static CMenu photo_settings_menu = {0x28,LANG_PHOTO_SETTINGS,photo_settings_items};

static CMenuItem photo_quick_items[] = {
    MENU_ITEM(0x24,LANG_MENU_RAW_SAVE, MENUITEM_BOOL|MENUITEM_ARG_CALLBACK, &conf.save_raw, cb_change_dng),
    MENU_ITEM(0x24,LANG_MENU_DNG_FORMAT, MENUITEM_BOOL|MENUITEM_ARG_CALLBACK, &conf.dng_raw, cb_change_dng),
    MENU_ITEM(0x74,LANG_PHOTO_ISO, MENUITEM_STATE_VAL_PAIR, &iso_override_items, 10),
    MENU_ITEM(0x61,LANG_MENU_OVERRIDE_TV_VALUE, MENUITEM_STATE_VAL_PAIR, &tv_override_evstep, 0),
#if CAM_HAS_IRIS_DIAPHRAGM
    MENU_ITEM(0x62,LANG_PHOTO_APERTURE, MENUITEM_STATE_VAL_PAIR, &av_override_items, 0),
#endif
    MENU_ENUM2(0x5f,LANG_MENU_OVERRIDE_DISABLE, &conf.override_disable, gui_override_disable_modes),
    MENU_ITEM(0x27,LANG_PHOTO_SMART, MENUITEM_SUBMENU, &photo_smart_menu, 0),
    MENU_ITEM(0x2e,LANG_MENU_MENU_SETTINGS, MENUITEM_SUBMENU, &menu_settings_submenu, 0),
    MENU_ITEM(0x51,LANG_MENU_BACK, MENUITEM_UP, 0, 0), {0}
};
static CMenu photo_quick_menu = {0x2e,LANG_PHOTO_QUICK,photo_quick_items};

static CMenuItem photo_root_items[] = {
    MENU_ITEM(0x21,LANG_PHOTO_SHOOT, MENUITEM_SUBMENU, &photo_shoot_menu, 0),
    MENU_ITEM(0x25,LANG_PHOTO_EXPOSURE, MENUITEM_SUBMENU, &photo_exposure_menu, 0),
    MENU_ITEM(0x31,LANG_PHOTO_FOCUS, MENUITEM_SUBMENU, &photo_focus_menu, 0),
    MENU_ITEM(0x27,LANG_PHOTO_SMART, MENUITEM_SUBMENU, &photo_smart_menu, 0),
    MENU_ITEM(0x28,LANG_PHOTO_SETTINGS, MENUITEM_SUBMENU, &photo_settings_menu, 0),
    MENU_ITEM(0x2e,LANG_PHOTO_QUICK, MENUITEM_SUBMENU, &photo_quick_menu, 0),
    MENU_ITEM(0x20,LANG_PHOTO_CLASSIC, MENUITEM_PROC, gui_photo_switch, PHOTO_UI_CLASSIC),
    {0}
};
static CMenu photo_root_menu = {0x20,LANG_PHOTO_TITLE,photo_root_items};
