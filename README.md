# Lanturn 🔦 (Work in Progress)

A hackathon project connecting the Gemini Live API to an ESP32 Atoms3r-CAM device for **voice + vision** conversations on embedded hardware.

## Overview

Lantern demonstrates real-time AI voice conversations with vision running on an ESP32 microcontroller. It uses:
- ESP32 Atoms3r‑CAM (mic, speaker, camera)
- Pipecat (voice/media orchestration)
- Gemini Live API (multimodal speech + vision)

## Features

- ✅ Real-time voice conversations
- ✅ **Real-time vision processing with camera** (Work in Progress)
- ✅ Gemini Live multimodal AI integration
- ✅ ESP32 hardware support
- ✅ WebRTC audio + vision streaming
- ✅ Automatic greeting on connection
- ✅ Google Search tool call
- ✅ **AI can see and describe what the camera shows**

## Architecture

```
ESP32 Atoms3r-CAM  <---WiFi/WebRTC--->  Pipecat Server  <--->  Gemini Live API
(Camera + Mic + Speaker)              (Signaling + Bot + Processing)       (Multimodal LLM)
```

### Data Flow

1. ESP32 captures audio from microphone and **camera video**
2. ESP_H264 converts the camera frames using Espressif's lightweight H.264 software encoder to **H.264 QVGA (320x240) at ~1 FPS** and streams via a WebRTC video track; audio uses Opus
3. Pipecat handles WebRTC signaling (`/api/offer`) and communicates with server to server via Gemini Live API
4. Gemini generates voice responses based on **what it hears AND sees** (inference)
5. Audio streams back to the tiny devices speaker

## Prerequisites

### Hardware
- ESP32 Atoms3r-CAM (M5Stack) with GC0308 camera
- USB-C cable for programming/power
- WiFi network on the 2.4ghz band with AP Isolation Disabled

### Software
- Python 3.13+
- uv (Python package manager)
- ESP-IDF toolchain (installed at `~/esp/esp-idf`)

## Quick Start

1) Install server deps
```bash
cd lanturn
uv sync
```

2) Configure API key (one of)
```bash
export GOOGLE_API_KEY=your_api_key_here
# or
cp env.example .env
```

3) Run the server (SmallWebRTC on :7860)
```bash
uv run python Lanturn_esp32_gemini_live_vision_bot.py -t webrtc --esp32 --host YOUR_COMPUTER_IP
```

4) Flash ESP32 firmware
```bash
cd esp32/pipecat-esp32/esp32-m5stack-atoms3r
source ~/esp/esp-idf/export.sh
idf.py set-target esp32s3
export WIFI_SSID="your_wifi_network"
export WIFI_PASSWORD="your_wifi_password"
export PIPECAT_SMALLWEBRTC_URL="http://YOUR_COMPUTER_IP:7860/api/offer"
idf.py build -p PORT flash
```

5) Monitor
```bash
idf.py monitor
```

## Setup

### 1) Start the Pipecat server (Python)

Follow the Quick Start steps (1–3).
   - The ESP32 will POST its WebRTC offer to: `http://YOUR_COMPUTER_IP:7860/api/offer`
   - Ensure your firewall allows inbound connections to port 7860 on `YOUR_COMPUTER_IP`.

Notes:
- The server enables audio-in, audio-out, and video-in; video-out to ESP32 is disabled.

### 2) Build and flash the ESP32 firmware

Set these env vars (compiled in): `WIFI_SSID`, `WIFI_PASSWORD`, `PIPECAT_SMALLWEBRTC_URL` Don't use quotations, just values. (see Quick Start step 4).

What to look for in the logs:
- WiFi connects and shows an acquired IP
- "Camera initialized successfully" (or a warning if not present)
- "Camera streaming enabled"
- Periodic logs like "Sent N H.264 frames"

## Usage

1) Start server. 2) Power on ESP32. 3) Speak and point the camera.
To test for Vision, Try:
- "What do you see?"
- "Describe what's in front of you"
- "What color is this?"
- "Read the text you see"

*Be specific about the video because the model will often hallucinate if there's no camera feed, and tell you otherwise. 

## Project Structure

```
lanturn/
├── Lanturn_esp32_gemini_live_vision_bot.py  # Vision-enabled bot (Pipecat + Gemini Live)
├── Lanturn_esp32_gemini_live_alt_bot.py     # Audio-only alt bot
├── main.py                                  # Placeholder entry point
├── env.example                              # Sample env file
├── pyproject.toml                           # Python dependencies
└── README.md                                # This file
```

## Documentation

- `pipecat.ai` docs: https://docs.pipecat.ai
- Gemini Live: https://ai.google.dev/gemini-api/docs/multimodal-live

## Technical Details

### Vision Specifications

- **Camera**: GC0308 0.3MP sensor
- **Resolution**: QVGA (320x240)
- **Video Codec**: H.264 Baseline
- **Frame Rate**: ~1 FPS
- **Bitrate**: ~200 kbps target
- **Transport**: SmallWebRTC video track (H.264) + Opus audio

- Dependencies (ESP-IDF component registry):
  - `espressif/esp32-camera` (GC0308, RGB565 capture)
  - `espressif/esp_h264` (software H.264 encoder)
- Build notes:
  - ESP‑IDF 5.5.x, PSRAM required (8MB on AtomS3R‑CAM)
  - Video task pinned to Core 1; audio on Core 0
  - Camera configured RGB565 QVGA; converted to I420 for encoder
  - RTP video timestamp set to 1 fps for accurate pacing
- Pin map (GC0308) from M5 docs:
  - CAM_SDA=G12, CAM_SCL=G9, VSYNC=G10, HREF=G14, XCLK=G21, PCLK=G40,
    Y9=G13, Y8=G11, Y7=G17, Y6=G4, Y5=G48, Y4=G46, Y3=G42, Y2=G3, POWER_N=G18
- Performance notes:
  - ESP32‑S3 software H.264 is viable at low FPS/QVGA; IDR every frame for robustness
  - Use PSRAM for camera and encoder buffers
  - Expect ~1–2s end-to-end visual latency


## Known Issues

- ESP32 camera may not power on in some setups. We suspect an init/power sequencing issue or hardware power constraint. Contributions with stable init/power routines for AtomS3R‑CAM are welcome.

## Development

### Running Locally
```bash
uv run python Lanturn_esp32_gemini_live_vision_bot.py -t webrtc --esp32 --host YOUR_IP
```

### Testing Without Hardware
```bash
uv run python Lanturn_esp32_gemini_live_vision_bot.py -t webrtc --host YOUR_IP
# Then open: http://YOUR_IP:7860
```

### Monitoring ESP32
```bash
cd esp32/pipecat-esp32/esp32-m5stack-atoms3r
source ~/esp/esp-idf/export.sh
idf.py monitor
```

## Credits

- **Pipecat**: [pipecat.ai](https://pipecat.ai)
- **Pipecat-esp32**: [pipecat.ai](https://github.com/pipecat-ai/pipecat-esp32)
- **Gemini Live**: [Google AI](https://ai.google.dev)
- **ESP-IDF**: [Espressif](https://www.espressif.com)
- **M5Stack**: [m5stack.com](https://m5stack.com)
- **ESP32-Camera**: [esp32-camera library](https://github.com/espressif/esp32-camera)

## Resources

- [AtomS3R-CAM Documentation](https://docs.m5stack.com/en/core/AtomS3R-CAM%20AI%20Chatbot)
- [ESP H.264 use tips](https://developer.espressif.com/blog/2025/07/esp-h264-use-tips/)
- [Gemini Live API](https://ai.google.dev/gemini-api/docs/multimodal-live)
- [Pipecat Documentation](https://docs.pipecat.ai)

## License

BSD 2-Clause; see `LICENSE`.

## Hackathon Info

- **Project**: Lanturn
- **Goal**: Voice + Vision AI on ESP32 embedded hardware
- **Stack**: ESP32 Atoms3R-CAM + Pipecat + Gemini Live
- **Status**: Functional prototype with voice (vision not working yet)
- **Sponsor**: Google and Pipecat hackathon

---

**Made with ❤️ for the Google + Pipecat Hackathon**


<!-- Duplicate commands removed; see Quick Start -->
