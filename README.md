# TiVo DVR Integration for Unfolded Circle Remote

[![GitHub Release](https://img.shields.io/github/v/release/johncarey70/uc-integration-tivo?style=flat-square)](https://github.com/johncarey70/uc-integration-tivo/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue?style=flat-square)
[![GitHub issues](https://img.shields.io/github/issues/johncarey70/uc-integration-tivo?style=flat-square)](https://github.com/johncarey70/uc-integration-tivo/issues)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/johncarey70/uc-integration-tivo/total?style=flat-square)


An Unfolded Circle Remote integration for controlling TiVo DVR and TiVo Mini devices over the local network using the TiVo TCP remote control protocol.

## Features

- Local network control
- TiVo remote button support
- Send Command support for custom TiVo commands
- Automatic connection to the configured TiVo device
- Device state reporting to the Unfolded Circle Remote
- Designed for TiVo DVR and TiVo Mini devices that support TCP control

## Requirements

- Unfolded Circle Remote
- TiVo DVR or TiVo Mini on the same routed network
- TiVo network remote control enabled
- TCP access to the TiVo control port

Default TiVo control port:

```text
31339
```

## TiVo Setup

On the TiVo device, enable network remote control:

```text
Menu -> Settings -> Remote, CableCARD & Devices -> Network Remote Control
```

Set Network Remote Control to:

```text
Enabled
```


## Configuration

During setup, the integration attempts to discover supported TiVo devices automatically using mDNS. Manual host and port entry is only required if the TiVo device is not discovered.

Example manual configuration:

```text
Host: 192.168.16.36
Port: 31339
Name: TiVo Mini
```

## Supported Commands

The integration sends TiVo remote commands using the TiVo `IRCODE` protocol.

Examples:

```text
IRCODE GUIDE
IRCODE SELECT
IRCODE TIVO
IRCODE LIVETV
IRCODE THUMBSUP
IRCODE THUMBSDOWN
```

## Send Command

The remote entity supports `send_cmd`.

Example command:

```text
GUIDE
```

This sends:

```text
IRCODE GUIDE
```

Use this for commands that are not directly exposed as buttons.

## Common TiVo Commands

```text
TIVO
LIVETV
GUIDE
INFO
SELECT
UP
DOWN
LEFT
RIGHT
BACK
EXIT
CLEAR
PLAY
PAUSE
STOP
REPLAY
ADVANCE
REVERSE
FORWARD
RECORD
THUMBSUP
THUMBSDOWN
NUM0
NUM1
NUM2
NUM3
NUM4
NUM5
NUM6
NUM7
NUM8
NUM9
CHANNELUP
CHANNELDOWN
```


## License

This project is licensed under the [Mozilla Public License 2.0](LICENSE).
