#pragma once

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// Initialize the GC0308 camera on M5Stack AtomS3R
int pipecat_camera_init_gc0308(void);

// Capture a frame in RGB565 format
// Returns 0 on success, -1 on failure
// out_ptr will point to the frame buffer (do not free!)
// out_len will contain the size of the buffer
int camera_capture_rgb565(uint8_t **out_ptr, size_t *out_len);

// Release the frame buffer after use
void camera_release_frame(void);

// Statistics
uint32_t camera_get_captures_ok(void);
uint32_t camera_get_captures_fail(void);

#ifdef __cplusplus
}
#endif

