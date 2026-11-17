# Title-owned runtime policy for the conditional generated timing seams.
LINK_OBJECTS += $(BUILD_DIR)/loa_gameplay_fps.o
override LDFLAGS += -Wl,--wrap=sr_hle_register
$(BUILD_DIR)/$(GAME_NAME)_recomp.c $(BUILD_DIR)/$(GAME_NAME)_recomp_funcs.h: ../../tools/frame_rate_codegen.py
compile: $(BUILD_DIR)/loa_gameplay_fps.o
$(BUILD_DIR)/loa_gameplay_fps.o: ../../tools/gameplay_fps.c $(RUNTIME_PROFILE_STAMP)
	$(CC) $(CFLAGS) $(DEPFLAGS) -c $< -o $@
