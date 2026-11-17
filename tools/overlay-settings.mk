# Title-owned host UI extension; upstream sources and revision remain untouched.
LINK_OBJECTS += $(BUILD_DIR)/loa_settings.o
override LDFLAGS += -Wl,--wrap=nk_overlay_page_settings -Wl,--wrap=nk_overlay_host_due -Wl,--wrap=nk_overlay_page_menu -Wl,--wrap=nk_ui_theme_n1 -Wl,--wrap=nk_ui_type
compile: $(BUILD_DIR)/loa_settings.o
$(BUILD_DIR)/loa_settings.o: ../../tools/in-game-settings.c ../../tools/title_settings_menu.h $(RUNTIME_PROFILE_STAMP)
	$(CC) $(CFLAGS) $(RT_NK_UI_FLAGS) $(DEPFLAGS) -c $< -o $@
