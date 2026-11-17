# Diagnostic link only; title.py's normal build does not include this file.
LINK_OBJECTS += $(BUILD_DIR)/loa_texture_probe.o
override LDFLAGS += -Wl,--wrap=nk_texrepl_lookup -Wl,--wrap=ge_decode_tex_rgba
compile: $(BUILD_DIR)/loa_texture_probe.o
$(BUILD_DIR)/loa_texture_probe.o: ../../tools/texture-probe.c $(RUNTIME_PROFILE_STAMP)
	$(CC) $(CFLAGS) $(DEPFLAGS) -c $< -o $@
