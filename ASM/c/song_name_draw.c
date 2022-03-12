#include "song_name_draw.h"

static uint32_t frames = 0;
static uint32_t render_song_flag = 0;
static int last_scene_shown = -1;

#define SONG_FRAMES_VISIBLE 60 // 20 Frames seems to be about 1 second
#define SONG_FRAMES_FADE_AWAY 60
#define SONG_FRAMES_FADE_INTO 5

#define TEXT_WIDTH 4
#define TEXT_HEIGHT 10

uint16_t song_name_enabled = 0;
uint16_t song_always_on_screen = 0;
uint16_t song_in_transitions = 0;
int8_t songs_ids[] = { 
    0x02, 0x18, 0x19, 0x1A,
    0x1B, 0x1C, 0x1D, 0x1E,
    0x1F, 0x26, 0x27, 0x28,
    0x29, 0x2A, 0x2C, 0x2D,
    0x2E, 0x2F, 0x30, 0x38,
    0x3A, 0x3C, 0x3E, 0x3F,
    0x40, 0x42, 0x4A, 0x4B,
    0x4C, 0x4E, 0x4F, 0x50,
    0x55, 0x56, 0x58, 0x5A,
    0x5B, 0x5C, 0x5F, 0x60,
    0x61, 0x62, 0x63, 0x64,
    0x65, 0x6B, 0x6C };
int8_t songs[47*40];

void draw_song_name(z64_disp_buf_t *db) {

    if (!song_name_enabled)
        return;

    // Find index of current scene
    int scene = z64_file.seq_index;
    //int scene = z64_game.unk_06_[0x2f6]; // Same value as seq_index
    int index = -1;
    for(int i = 0; i < 47; i++) {
        if (songs_ids[i] == scene) {
            index = i;
            break;
        }
    }
    if (index < 0 || index > 46)
        return;

    uint8_t alpha = 0;
    if (song_in_transitions && 
        scene != last_scene_shown) {
        render_song_flag = 1;
        frames = frames > SONG_FRAMES_FADE_INTO ? SONG_FRAMES_FADE_INTO : frames;
    }

    if (!song_always_on_screen) {
        // Pause screen
        if (z64_game.pause_ctxt.state == 6) {
            alpha = 255;
        } else { // Only in transitions
            // Do a fade in/out effect if the scene was changed
            if (render_song_flag) {
                if (frames <= SONG_FRAMES_FADE_INTO ) {
                    alpha = frames * 255 / SONG_FRAMES_FADE_INTO;
                } else if (frames <= SONG_FRAMES_FADE_INTO + SONG_FRAMES_VISIBLE ) {
                    alpha = 255;
                } else if (frames <= SONG_FRAMES_FADE_INTO + SONG_FRAMES_VISIBLE + SONG_FRAMES_FADE_AWAY) {
                    alpha = (frames - SONG_FRAMES_FADE_INTO - SONG_FRAMES_VISIBLE) * 255 /  SONG_FRAMES_FADE_AWAY;
                    alpha = 255 - alpha;
                } else {
                    render_song_flag = 0;
                    frames = 0;
                    return;
                }
            }
        }
    }
    else {
        alpha = 255;
    }

    last_scene_shown = scene;
    frames++;    

    int draw_x = 1;
    int draw_y_text = 1;

    // Find size of text
    int size_text = 1;
    for (int i = 1; i < 40; i++) {
        // Stop at two consecutive spaces
        if (songs[index*40 + i] == 32 && songs[index*40 + i - 1] == 32) {
            break;
        }
        size_text++;
    }
    if (size_text < 2)
        return;

    char text[size_text];
    for (int i = 0; i < size_text - 1; i++) {
        text[i] = (char)(songs[index*40 + i]);
    }

    // Call setup display list
    gSPDisplayList(db->p++, &setup_db);
    gDPPipeSync(db->p++);
    gDPSetCombineMode(db->p++, G_CC_MODULATEIA_PRIM, G_CC_MODULATEIA_PRIM);

    text_print_size(text, draw_x, draw_y_text, TEXT_WIDTH);
    gDPSetPrimColor(db->p++, 0, 0, 0xFF, 0xFF, 0xFF, alpha);

    text_flush_size(db, TEXT_WIDTH, TEXT_HEIGHT, 0, 0);

    gDPFullSync(db->p++);
    gSPEndDisplayList(db->p++);
}

void draw_song_name_on_file_select(z64_disp_buf_t *db) {

    if (!song_name_enabled)
        return;

    // Fairy fountain track
    int index = 11;

    int draw_x = 1;
    int draw_y_text = 1;

    // Find size of text
    int size_text = 1;
    for (int i = 1; i < 40; i++) {
        // Stop at two consecutive spaces
        if (songs[index*40 + i] == 32 && songs[index*40 + i - 1] == 32) {
            break;
        }
        size_text++;
    }
    if (size_text < 2)
        return;

    char text[size_text];
    for (int i = 0; i < size_text - 1; i++) {
        text[i] = (char)(songs[index*40 + i]);
    }

    // Call setup display list
    uint8_t alpha = 255;
    text_print_size(text, draw_x, draw_y_text, TEXT_WIDTH);
    gDPSetPrimColor(db->p++, 0, 0, 0xFF, 0xFF, 0xFF, alpha);
    text_flush_size(db, TEXT_WIDTH, TEXT_HEIGHT, 0, 0);
}