set(COMMON_SRC "webrtc.cpp" "main.cpp" "http.cpp")

if(IDF_TARGET STREQUAL linux)
	idf_component_register(
		SRCS ${COMMON_SRC}
		REQUIRES peer esp-libopus esp_http_client cjson)
else()
	idf_component_register(
		SRCS ${COMMON_SRC} "wifi.cpp" "media.cpp" "rtvi.cpp" "rtvi_callbacks.cpp" "camera.cpp" "video_task.cpp"
		REQUIRES driver esp_wifi nvs_flash peer esp_psram esp-libopus esp_http_client cjson
		PRIV_REQUIRES esp_driver_i2s esp_driver_i2c esp_driver_gpio esp_timer esp_ringbuf)
endif()

idf_component_get_property(lib peer COMPONENT_LIB)
target_compile_options(${lib} PRIVATE -Wno-error=restrict)
target_compile_options(${lib} PRIVATE -Wno-error=stringop-truncation)
target_compile_options(${lib} PRIVATE -Wno-error=discarded-qualifiers)

# Silence volatile deprecation warnings in this component under IDF 6.0
idf_component_get_property(src_lib src COMPONENT_LIB)
target_compile_options(${src_lib} PRIVATE -Wno-error=volatile)

idf_component_get_property(lib srtp COMPONENT_LIB)
target_compile_options(${lib} PRIVATE -Wno-error=incompatible-pointer-types)

idf_component_get_property(lib esp-libopus COMPONENT_LIB)
target_compile_options(${lib} PRIVATE -Wno-error=maybe-uninitialized)
target_compile_options(${lib} PRIVATE -Wno-error=stringop-overread)
