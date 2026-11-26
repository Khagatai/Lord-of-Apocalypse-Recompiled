# Identity-checked private scheduler copy; no change to the pinned checkout.
RT_OBJS := $(filter-out $(BUILD_DIR)/sched.o,$(RT_OBJS))
LINK_OBJECTS += $(BUILD_DIR)/loa_sched.o
compile: $(BUILD_DIR)/loa_sched.o
$(BUILD_DIR)/loa_sched.o: $(BUILD_DIR)/performance-runtime/sched.c $(RUNTIME_PROFILE_STAMP)
	$(CC) $(CFLAGS) $(DEPFLAGS) -c $< -o $@
