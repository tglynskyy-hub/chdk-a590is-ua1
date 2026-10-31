#ifndef PHOTO_UI_POLICY_H
#define PHOTO_UI_POLICY_H

#define PHOTO_UI_CLASSIC 0
#define PHOTO_UI_PHOTOGRAPHY 1
#define PHOTO_UI_PROFILE_MARKER "A/CHDK/DATA/PHOTO_UI.TXT"

/* Existing configurations always win. Corrupt/unknown mode means recovery UI. */
static inline int photo_ui_normalize(int mode)
{
    return mode == PHOTO_UI_PHOTOGRAPHY ? PHOTO_UI_PHOTOGRAPHY : PHOTO_UI_CLASSIC;
}

static inline int photo_ui_initial_mode(int saved_mode, int fresh, int photo_package)
{
    return fresh && photo_package ? PHOTO_UI_PHOTOGRAPHY : photo_ui_normalize(saved_mode);
}

#endif
