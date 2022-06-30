#include "model_text.h"

uint16_t illegal_model = 0;

void draw_illegal_model_text(z64_disp_buf_t *db) {

    // Only draw when paused
    if (!(illegal_model && z64_game.pause_ctxt.state == 6)) {
        return;
    }
    
    // Setup draw location
    int str_len = 38;
    int total_w = str_len * font_sprite.tile_w;
    int draw_x = Z64_SCREEN_WIDTH / 2 - total_w / 2;
    int draw_y_text = 5;

    // Create collected/required string
    char text[str_len + 1];
    strncpy(text, "Race advisory:irregular model skeleton\0", str_len + 1);

    // Call setup display list
    gSPDisplayList(db->p++, &setup_db);
    gDPPipeSync(db->p++);
    gDPSetCombineMode(db->p++, G_CC_MODULATEIA_PRIM, G_CC_MODULATEIA_PRIM);
    gDPSetPrimColor(db->p++, 0, 0, 0xFF, 0xFF, 0xFF, 0xFF);

    text_print(text, draw_x, draw_y_text);

    text_flush(db);
    gDPFullSync(db->p++);
    gSPEndDisplayList(db->p++);
}
