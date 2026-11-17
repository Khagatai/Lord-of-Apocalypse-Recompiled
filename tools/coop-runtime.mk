# Title-owned experimental networking. Disabled unless explicitly configured.
LINK_OBJECTS += $(BUILD_DIR)/loa_coop_hle.o $(BUILD_DIR)/loa_coop_transport.o $(BUILD_DIR)/loa_coop_protocol.o $(BUILD_DIR)/loa_online_runtime.o
override LDFLAGS += -Wl,--wrap=sr_hle_register_unsupported
LIBS += -lws2_32 -lcrypt32
compile: $(BUILD_DIR)/loa_coop_hle.o $(BUILD_DIR)/loa_coop_transport.o $(BUILD_DIR)/loa_coop_protocol.o
compile: $(BUILD_DIR)/loa_online_runtime.o
$(BUILD_DIR)/loa_online_runtime.o: ../../tools/online_runtime.c ../../tools/online_runtime.h
	$(CC) $(CFLAGS) -Isrc/core -I../../tools $(DEPFLAGS) -c $< -o $@
$(BUILD_DIR)/loa_coop_hle.o: ../../tools/coop_hle.c ../../tools/coop_transport.h ../../tools/coop_service_wait.h $(RUNTIME_PROFILE_STAMP)
	$(CC) $(CFLAGS) $(HLE_INCLUDES) -Isrc/core -I../../tools $(DEPFLAGS) -c $< -o $@
$(BUILD_DIR)/loa_coop_transport.o: ../../tools/coop_transport.c ../../tools/coop_transport.h
	$(CC) $(CFLAGS) -Isrc/core -I../../tools $(DEPFLAGS) -c $< -o $@
$(BUILD_DIR)/loa_coop_protocol.o: src/core/nk_adhoc_relay.c src/core/nk_adhoc_relay.h
	$(CC) $(CFLAGS) -Isrc/core $(DEPFLAGS) -c $< -o $@
