# Lantern 🏮

A hackathon project connecting the Gemini Live API to an ESP32 Atoms3r-CAM device for **voice + vision** conversations on embedded hardware.

## Overview

Lantern demonstrates real-time AI voice conversations with **vision capabilities** running on an ESP32 microcontroller. The project uses:
- **ESP32 Atoms3r-CAM**: M5Stack device with WiFi, microphone, speaker, and **camera**
- **Pipecat**: AI voice and media orchestration framework for building voice agents
- **Gemini Live API**: Google's multimodal realtime speech-to-speech api with low-latency voice and **vision** capabilities

## Features

- ✅ Real-time voice conversations
- ✅ **Real-time vision processing with camera**
- ✅ Gemini Live multimodal AI integration
- ✅ ESP32 hardware support
- ✅ WebRTC audio + vision streaming
- ✅ Automatic greeting on connection
- ✅ Voice Activity Detection (VAD)
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
5. Audio streams back to the ESP32 speaker

## Prerequisites

### Hardware
- ESP32 Atoms3r-CAM (M5Stack) with GC0308 camera
- USB-C cable for programming/power
- WiFi network on the 2.4ghz band with AP Isolation Disabled

### Software
- Python 3.13+
- uv (Python package manager)
- ESP-IDF toolchain (installed at `~/esp/esp-idf`)

## Setup

### 1) Start the Pipecat server (Python)

1. Install Python dependencies
   ```bash
   cd /Users/petermcgrath/lanturn
   uv sync
   ```
2. Set your Gemini API key (either export it or use a `.env` file). The Python app reads `GEMINI_API_KEY`:
   ```bash
   export GEMINI_API_KEY=your_api_key_here
   ```
3. Start the Pipecat WebRTC server (SmallWebRTC prebuilt, default HTTP port 7860):
   ```bash
   uv run python gemini_esp32_vision_bot.py -t webrtc --esp32 --host YOUR_COMPUTER_IP
   ```
   - The ESP32 will POST its WebRTC offer to: `http://YOUR_COMPUTER_IP:7860/api/offer`
   - Ensure your firewall allows inbound connections to port 7860 on `YOUR_COMPUTER_IP`.

Notes:
- The server enables audio-in, audio-out, and video-in; video-out to ESP32 is disabled.
- Voice Activity Detection (Silero) uses a 0.5s stop timeout.

### 2) Build and flash the ESP32 firmware

The ESP32 firmware requires three environment variables at build time (compiled in):
- `WIFI_SSID`: your WiFi network name
- `WIFI_PASSWORD`: your WiFi password
- `PIPECAT_SMALLWEBRTC_URL`: `http://YOUR_COMPUTER_IP:7860/api/offer`

Steps:
```bash
# ESP-IDF environment
cd /Users/petermcgrath/Desktop/pipecat-esp32-main/esp32-m5stack-atoms3r
source ~/esp/esp-idf/export.sh

# Set connection and signaling info (replace with your values)
export WIFI_SSID="your_wifi_network"
export WIFI_PASSWORD="your_wifi_password"
export PIPECAT_SMALLWEBRTC_URL="http://YOUR_COMPUTER_IP:7860/api/offer"

# Build for ESP32-S3 target and flash
idf.py set-target esp32s3
idf.py build
# Replace PORT with your serial device, e.g. /dev/tty.usbmodemXXXX or /dev/cu.usbserial-XXXXX
idf.py -p PORT flash

# (optional) View logs
idf.py monitor
```

What to look for in the ESP32 logs:
- WiFi connects and shows an acquired IP
- "Camera initialized successfully" (or a warning if not present)
- "Camera streaming enabled"
- Periodic logs like "Sent N H.264 frames"

## Usage

1. Start the Pipecat server first
2. Power on the ESP32 (it auto-connects to WiFi and posts an offer to the server)
3. Speak into the ESP32 microphone and point the camera at objects/scenes
4. Try prompts like:
   - "What do you see?"
   - "Describe what's in front of you"
   - "What color is this?"
   - "Read the text you see"

## Project Structure

```
lanturn/
├── gemini_esp32_vision_bot.py  # Vision-enabled bot (Pipecat + Gemini Live)
├── main.py                     # Placeholder entry point
├── pyproject.toml              # Python dependencies
└── README.md                   # This file
```

## Documentation

- `pipecat.ai` docs: https://docs.pipecat.ai
- Gemini Live: https://ai.google.dev/gemini-api/docs/multimodal-live

## Technical Details

### Vision Specifications

- **Camera**: GC0308 0.3MP sensor
- **Resolution**: QVGA (320x240)
- **Video Codec**: H.264
- **Frame Rate**: ~1 FPS
- **Transport**: SmallWebRTC video track (H.264) + Opus audio

### WebRTC Configuration
- SmallWebRTC transport (HTTP signaling endpoint: `/api/offer` on port 7860)
- Audio in/out enabled; video in enabled; video out disabled to ESP32

### VAD Settings
- Silero VAD analyzer
- Stop timeout: 0.5 seconds (matches Gemini Live)

### Audio Format
- Sample rate: 16kHz
- Channels: Mono
- Codec: Opus (WebRTC standard)

## Performance (indicative)

- Audio latency: ~200–500ms
- Vision latency: ~1–2s (1 FPS capture + processing)
- Memory: ESP32 uses PSRAM for frame buffers

## Troubleshooting

### ESP32 Won't Connect
- Verify WiFi credentials/.env vars in firmware
- Check IP address matches in both ESP32 and server
- Ensure both devices on same network
- Check firewall settings (port 7860)
- Make sure you're on 2.4ghz not 5.0ghz.

### Camera Issues
- Check ESP32 monitor: `idf.py monitor`
- Look for "Camera initialized successfully"
- Verify "Camera streaming enabled" message
- Verify frames in Pipecat Logs.
- Check for "Sent X camera frames" logs

### Audio Issues
- Verify microphone/speaker on ESP32
- Check audio levels in monitor logs
- Ensure VAD is working properly

### Vision Not Working
- Ensure you're running `gemini_esp32_vision_bot.py` with `-t webrtc --esp32`
- Verify `PIPECAT_SMALLWEBRTC_URL` matches your server IP and port 7860
- Confirm firewall allows inbound `:7860`
- Verify `GEMINI_API_KEY` is set

## Development

### Running Locally
```bash
# Run vision bot (Pipecat server) on your machine
uv run python gemini_esp32_vision_bot.py -t webrtc --esp32 --host YOUR_IP
```

### Testing Without Hardware
You can test with a web browser instead of ESP32:
```bash
uv run python gemini_esp32_vision_bot.py -t webrtc --host YOUR_IP
# Then open: http://YOUR_IP:7860
```

### Monitoring ESP32
```bash
cd /Users/petermcgrath/Desktop/pipecat-esp32-main/esp32-m5stack-atoms3r
source ~/esp/esp-idf/export.sh
idf.py monitor
```

## Credits

- **Pipecat**: [pipecat.ai](https://pipecat.ai)
- **Gemini Live**: [Google AI](https://ai.google.dev)
- **ESP-IDF**: [Espressif](https://www.espressif.com)
- **M5Stack**: [m5stack.com](https://m5stack.com)
- **ESP32-Camera**: [esp32-camera library](https://github.com/espressif/esp32-camera)

## Resources

- [AtomS3R-CAM Documentation](https://docs.m5stack.com/en/core/AtomS3R-CAM%20AI%20Chatbot)
- [Gemini Live API](https://ai.google.dev/gemini-api/docs/multimodal-live)
- [Pipecat Documentation](https://docs.pipecat.ai)

## License

This hackathon project is provided as-is for educational purposes.

## Hackathon Info

- **Project**: Lanturn
- **Goal**: Voice + Vision AI on ESP32 embedded hardware
- **Stack**: ESP32 Atoms3R-CAM + Pipecat + Gemini Live
- **Status**: ✅ Functional prototype with voice + vision
- **Sponsor**: Google and Pipecat hackathon

---

**Made with ❤️ for the Google + Pipecat Hackathon**


Server Start:
uv run python gemini_esp32_vision_bot.py -t webrtc --esp32 --host 192.168.0.138

ESP32 Start:
cd /Users/petermcgrath/lanturn/esp32/pipecat-esp32/esp32-m5stack-atoms3r
idf.py build flash monitor