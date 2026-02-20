# Dot. Quote/0 for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A custom Home Assistant integration for [Dot. Quote/0](https://dot.mindreset.tech/docs/quote_0) e-ink devices by MindReset.

Monitor device status and push text or image content to your Quote/0 directly from Home Assistant.

## Features

### Sensors
- **Power State** — current device power mode (Power Active, Battery Active, etc.)
- **Battery Status** — charging state
- **Wi-Fi Signal** — signal strength in dBm
- **Firmware Version** — current firmware
- **Last Render** — timestamp of the last screen update
- **Next Render (Battery / Power)** — scheduled next update times

### Binary Sensor
- **Online** — connectivity status

### Controls (on the device page)
- **Next Content** — cycle to the next item in the content loop
- **Send Text** — push text to the device using the Title, Message, and Signature input fields
- **Send Image** — push an image to the device using the Image Data input field
- **Text Title / Text Message / Text Signature** — editable text fields for composing content
- **Image Data** — input field for base64-encoded PNG (296×152px) or an absolute file path
- **Dither Type** — dropdown to select dithering algorithm (DIFFUSION, ORDERED, NONE)

### Service Actions
- `dot_quote0.send_text` — push text content with full parameter control
- `dot_quote0.send_image` — push image content with dithering and border options

## Prerequisites

1. A paired [Quote/0](https://dot.mindreset.tech/docs/quote_0) device connected to Wi-Fi
2. An API key from the Dot. App (More → API Key → Create API Key)
3. Your device serial number (More → Device List → Device → Device Serial Number)

## Installation

### HACS (recommended)

1. Open HACS → Integrations → ⋮ menu → **Custom repositories**
2. Add `https://github.com/Never2land/HA-dot-quote0` with category **Integration**
3. Install **Dot. Quote/0**
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/dot_quote0/` folder into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Dot. Quote/0**
3. Enter your API key
4. All your Quote/0 devices will be discovered automatically

## Usage

### Device Controls

After setup, go to **Settings → Devices** and select your Quote/0 device. The Controls section provides:

- Text input fields to compose content (title, message, signature)
- **Send Text** button to push the composed text to your device
- Image data input and dither type selector
- **Send Image** button to push an image to your device
- **Next Content** button to cycle display content

### Service Actions

You can also use service actions in automations and scripts:

```yaml
# Send text to device
service: dot_quote0.send_text
data:
  device_id: "YOUR_DEVICE_ID"
  title: "Hello"
  message: "World"
  signature: "From Home Assistant"
  refresh_now: true
```

```yaml
# Send image to device
service: dot_quote0.send_image
data:
  device_id: "YOUR_DEVICE_ID"
  image: "<base64-encoded PNG data>"
  dither_type: "DIFFUSION"
  border: 0
  refresh_now: true
```

## API Reference

This integration uses the [Dot. Developer Platform](https://dot.mindreset.tech/docs/service/open) cloud API. All communication goes through `https://dot.mindreset.tech`. There is no local API.

- Rate limit: 10 requests per second
- Polling interval: 5 minutes (device status)
- Image resolution: 296×152px PNG
- Icon resolution: 40×40px PNG

## License

MIT
