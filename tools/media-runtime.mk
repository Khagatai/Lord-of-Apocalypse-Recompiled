# Identity-checked private source copy; original framework checkout stays pinned.
RT_OBJS := $(filter-out $(BUILD_DIR)/mpeg.o $(BUILD_DIR)/hle_audio.o,$(RT_OBJS))
LINK_OBJECTS += $(BUILD_DIR)/loa_mpeg.o $(BUILD_DIR)/loa_audio.o $(BUILD_DIR)/loa_movie_subtitles.o
compile: $(BUILD_DIR)/loa_mpeg.o $(BUILD_DIR)/loa_audio.o $(BUILD_DIR)/loa_movie_subtitles.o
$(BUILD_DIR)/loa_mpeg.o: $(BUILD_DIR)/media-runtime/mpeg.c
	$(CC) $(CFLAGS) $(DEPFLAGS) -c $< -o $@
$(BUILD_DIR)/loa_audio.o: $(BUILD_DIR)/media-runtime/hle_audio.c ../../tools/audio_diagnostics.h
	$(CC) $(CFLAGS) $(HLE_INCLUDES) -I../../tools $(DEPFLAGS) -c $< -o $@
$(BUILD_DIR)/loa_movie_subtitles.o: ../../tools/movie_subtitles.c ../../tools/movie_caption_format.h
	$(CC) $(CFLAGS) $(DEPFLAGS) -c $< -o $@
