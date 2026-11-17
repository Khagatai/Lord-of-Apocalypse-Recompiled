# Title-owned, identity-checked private renderer copy; upstream stays pinned.
RT_OBJS := $(filter-out $(BUILD_DIR)/ge_gpu.o,$(RT_OBJS))
LINK_OBJECTS += $(BUILD_DIR)/loa_ge_gpu.o
compile: $(BUILD_DIR)/loa_ge_gpu.o
$(BUILD_DIR)/loa_ge_gpu.o: $(BUILD_DIR)/hd-renderer/ge_gpu.c $(BUILD_DIR)/hd-renderer/mip_gpu.c $(BUILD_DIR)/hd-renderer/mip_chain.c $(BUILD_DIR)/hd-renderer/sampler_pack.c
	$(CC) $(CFLAGS) -Isrc/rt/gpu_sdl3vk -I../../tools $(DEPFLAGS) -c $< -o $@
