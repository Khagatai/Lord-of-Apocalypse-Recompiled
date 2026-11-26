# Title-owned runtime policy for the conditional generated timing seams.
LINK_OBJECTS += $(BUILD_DIR)/loa_gameplay_fps.o
LINK_OBJECTS += $(BUILD_DIR)/loa_camera.o
LINK_OBJECTS += $(BUILD_DIR)/loa_camera_input.o
LINK_OBJECTS += $(BUILD_DIR)/loa_password.o
override LDFLAGS += -Wl,--wrap=sr_hle_register
override LDFLAGS += -Wl,--wrap=nk_input_profile_eval_buttons
$(BUILD_DIR)/$(GAME_NAME)_recomp.c $(BUILD_DIR)/$(GAME_NAME)_recomp_funcs.h: ../../tools/frame_rate_codegen.py
$(BUILD_DIR)/$(GAME_NAME)_recomp.c $(BUILD_DIR)/$(GAME_NAME)_recomp_funcs.h: ../../tools/camera_codegen.py
$(BUILD_DIR)/$(GAME_NAME)_recomp.c $(BUILD_DIR)/$(GAME_NAME)_recomp_funcs.h: ../../tools/password_codegen.py
compile: $(BUILD_DIR)/loa_gameplay_fps.o $(BUILD_DIR)/loa_camera.o
compile: $(BUILD_DIR)/loa_camera_input.o
$(BUILD_DIR)/loa_camera_input.o: ../../tools/camera_input.c $(RUNTIME_PROFILE_STAMP)
	$(CC) $(CFLAGS) $(DEPFLAGS) -c $< -o $@
$(BUILD_DIR)/loa_gameplay_fps.o: ../../tools/gameplay_fps.c $(RUNTIME_PROFILE_STAMP)
	$(CC) $(CFLAGS) $(DEPFLAGS) -c $< -o $@
$(BUILD_DIR)/loa_camera.o: ../../tools/camera_runtime.c ../../tools/camera_motion.h $(RUNTIME_PROFILE_STAMP)
	$(CC) $(CFLAGS) $(DEPFLAGS) -c $< -o $@
compile: $(BUILD_DIR)/loa_password.o
$(BUILD_DIR)/loa_password.o: ../../tools/password_runtime.c ../../tools/password_alias.h $(RUNTIME_PROFILE_STAMP)
	$(CC) $(CFLAGS) $(DEPFLAGS) -c $< -o $@
