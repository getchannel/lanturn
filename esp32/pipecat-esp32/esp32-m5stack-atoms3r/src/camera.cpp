#include "camera.h"

#include "esp_camera.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "PIPECAT_CAMERA";

static volatile uint32_t s_captures_ok = 0;
static volatile uint32_t s_captures_fail = 0;
static camera_fb_t *s_last_fb = nullptr;

int pipecat_camera_init_gc0308(void) {
  // Ensure camera power is enabled before SCCB/I2C probe (POWER_N is active LOW)
  gpio_config_t cam_power_cfg = {};
  cam_power_cfg.pin_bit_mask = (1ULL << 18);
  cam_power_cfg.mode = GPIO_MODE_OUTPUT;
  cam_power_cfg.pull_up_en = GPIO_PULLUP_DISABLE;
  cam_power_cfg.pull_down_en = GPIO_PULLDOWN_DISABLE;
  cam_power_cfg.intr_type = GPIO_INTR_DISABLE;
  gpio_config(&cam_power_cfg);
  gpio_set_level((gpio_num_t)18, 0);  // POWER_N LOW -> power on
  vTaskDelay(pdMS_TO_TICKS(100));

  camera_config_t config = {};
  // Pin map per M5 AtomS3R-CAM docs (GC0308)
  config.pin_pwdn = -1;   // no PWDN pin (GPIO18 is external power enable, not sensor PWDN)
  config.pin_reset = -1;  // not exposed
  config.pin_xclk = 21;   // XCLK
  config.pin_sccb_sda = 12;  // CAM_SDA
  config.pin_sccb_scl = 9;   // CAM_SCL

  config.pin_d7 = 13;  // Y9
  config.pin_d6 = 11;  // Y8
  config.pin_d5 = 17;  // Y7
  config.pin_d4 = 4;   // Y6
  config.pin_d3 = 48;  // Y5
  config.pin_d2 = 46;  // Y4
  config.pin_d1 = 42;  // Y3
  config.pin_d0 = 3;   // Y2

  config.pin_vsync = 10;  // VSYNC
  config.pin_href = 14;   // HREF
  config.pin_pclk = 40;   // PCLK

  config.xclk_freq_hz = 20000000;  // 20MHz typical
  config.ledc_timer = LEDC_TIMER_0;
  config.ledc_channel = LEDC_CHANNEL_0;

  config.pixel_format = PIXFORMAT_RGB565;  // avoid JPEG
  config.frame_size = FRAMESIZE_QVGA;      // 320x240
  config.jpeg_quality = 12;                // unused in RGB path
  config.fb_count = 2;                     // align with M5 example
  config.fb_location = CAMERA_FB_IN_PSRAM; // align with M5 example
  config.grab_mode = CAMERA_GRAB_LATEST;   // align with M5 example
  config.sccb_i2c_port = 0;                // explicit I2C0 per M5 example

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "esp_camera_init failed: %d", err);
    return -1;
  }

  return 0;
}

int camera_capture_rgb565(uint8_t **out_ptr, size_t *out_len) {
  if (!out_ptr || !out_len) return -1;
  s_last_fb = esp_camera_fb_get();
  if (!s_last_fb) {
    s_captures_fail++;
    ESP_LOGW(TAG, "camera capture failed");
    return -1;
  }
  if (s_last_fb->format != PIXFORMAT_RGB565) {
    s_captures_fail++;
    ESP_LOGW(TAG, "unexpected pixel format=%d", s_last_fb->format);
    esp_camera_fb_return(s_last_fb);
    s_last_fb = nullptr;
    return -1;
  }
  *out_ptr = s_last_fb->buf;
  *out_len = s_last_fb->len;
  s_captures_ok++;
  return 0;
}

void camera_release_frame(void) {
  if (s_last_fb) {
    esp_camera_fb_return(s_last_fb);
    s_last_fb = nullptr;
  }
}

uint32_t camera_get_captures_ok(void) { return s_captures_ok; }
uint32_t camera_get_captures_fail(void) { return s_captures_fail; }


