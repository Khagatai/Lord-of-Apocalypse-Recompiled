# Title-owned experimental networking. Disabled unless explicitly configured.
LINK_OBJECTS += $(BUILD_DIR)/loa_coop_hle.o $(BUILD_DIR)/loa_coop_transport.o $(BUILD_DIR)/loa_coop_protocol.o $(BUILD_DIR)/loa_online_runtime.o
LINK_OBJECTS += $(BUILD_DIR)/loa_coop_diagnostics.o
override LDFLAGS += -Wl,--wrap=sr_hle_register_unsupported
override LDFLAGS += -Wl,--wrap=sr_null_code_pointer
LIBS += -lws2_32 -lcrypt32
compile: $(BUILD_DIR)/loa_coop_hle.o $(BUILD_DIR)/loa_coop_transport.o $(BUILD_DIR)/loa_coop_protocol.o
compile: $(BUILD_DIR)/loa_online_runtime.o
compile: $(BUILD_DIR)/loa_coop_diagnostics.o
$(BUILD_DIR)/loa_coop_diagnostics.o: ../../tools/coop_diagnostics.c $(RUNTIME_PROFILE_STAMP)
	$(CC) $(CFLAGS) $(DEPFLAGS) -c $< -o $@
$(BUILD_DIR)/loa_online_runtime.o: ../../tools/online_runtime.c ../../tools/online_runtime.h
	$(CC) $(CFLAGS) -Isrc/core -I../../tools $(DEPFLAGS) -c $< -o $@
$(BUILD_DIR)/loa_coop_hle.o: ../../tools/coop_hle.c ../../tools/coop_transport.h ../../tools/coop_service_wait.h $(RUNTIME_PROFILE_STAMP)
	$(CC) $(CFLAGS) $(HLE_INCLUDES) -Isrc/core -I../../tools $(DEPFLAGS) -c $< -o $@
$(BUILD_DIR)/loa_coop_transport.o: ../../tools/coop_transport.c ../../tools/coop_transport.h
	$(CC) $(CFLAGS) -Isrc/core -I../../tools $(DEPFLAGS) -c $< -o $@
$(BUILD_DIR)/loa_coop_protocol.o: src/core/nk_adhoc_relay.c src/core/nk_adhoc_relay.h
	$(CC) $(CFLAGS) -Isrc/core $(DEPFLAGS) -c $< -o $@
