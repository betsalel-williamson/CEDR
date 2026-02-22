# Serial console on macOS (screen and device ID)

This doc explains how to connect to a serial device (e.g. Xilinx JTAG+Serial, Arduino, boards over USB) from macOS using `screen`, and how to find the correct device path.

## Why `/dev/ttyACM0` doesn’t exist on Mac

On **Linux**, USB serial (CDC ACM) devices usually show up as:

- `/dev/ttyACM0`, `/dev/ttyACM1`, …
- or `/dev/ttyUSB0`, `/dev/ttyUSB1`, … (FTDI, etc.)

On **macOS**, the same kind of device gets different names. There is no `ttyACM`; use the paths below instead.

## Finding the correct device ID on macOS

### 1. List serial (call-out) devices

Use the **`cu.*`** devices for initiating connections (e.g. with `screen`):

```bash
ls /dev/cu.usbserial-* /dev/cu.usbmodem-* 2>/dev/null
```

Typical names:

- **FTDI / Xilinx JTAG+Serial:** `/dev/cu.usbserial-<SERIAL>`
- **Arduino / CDC ACM:** `/dev/cu.usbmodem*`

You may see two entries per physical adapter (e.g. two ports). Try the first; if it’s the wrong port, try the second.

### 2. Match the device with USB info (optional)

To see which USB device corresponds to which `/dev/cu.*` name:

```bash
system_profiler SPUSBDataType
```

Look for the serial number in the USB tree; it appears in the device path, e.g. `/dev/cu.usbserial-88022500023D0`.

### 3. Quick reference

| Platform | Example device path        |
|----------|----------------------------|
| Linux    | `/dev/ttyACM0`, `/dev/ttyUSB0` |
| macOS    | `/dev/cu.usbserial-*`, `/dev/cu.usbmodem*` |

On macOS, prefer **`/dev/cu.*`** over **`/dev/tty.*`** for tools like `screen`.

## Connecting with screen

### Basic usage

```bash
screen <device> <baud_rate>
```

Example (Xilinx JTAG+Serial at 115200, second port):

```bash
screen /dev/cu.usbserial-88022500023D1 115200
```

Use your actual device path from `ls /dev/cu.*`. Common baud rates: `9600`, `115200`, `921600`.

### Screen commands

| Action | Keys |
|--------|------|
| Detach (leave session running) | `Ctrl+A`, then `D` |
| Kill session | `Ctrl+A`, then `K`, then confirm |
| Reattach to a session | `screen -r` |

To exit completely, you can also type `exit` in the session or use `Ctrl+A` then `K`.

## Troubleshooting

- **Permission denied:** On macOS the device is often world-readable (`crw-rw-rw-`). If not, check that your user has access to the device node.
- **No output or wrong port:** Try the other `cu.usbserial-*` or `cu.usbmodem*` device for the same hardware (e.g. `...23D0` vs `...23D1`).
- **Device disappears after unplug:** Run `ls /dev/cu.*` again after reconnecting; the path is stable for a given serial number and port.
