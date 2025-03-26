# Python Edge RGB (Terminal Control)

A Python script that renders moving RGB lights along the edges of your computer screen(s) on Windows. This version is controlled entirely through the terminal, allowing for multi-monitor selection at startup.

## Features

*   Displays smoothly moving RGB rainbow patterns on screen borders.
*   Runs on Windows.
*   **Terminal Control:** Select target monitors (specific, multiple, all, primary) via terminal prompt on launch.
*   **Multi-Monitor Support:** Can display lights simultaneously on selected multiple monitors.
*   **Customizable:** Adjust thickness, animation speed, brightness, saturation, and segment size via a configuration file (`edge_rgb_settings.json`).
*   **Lightweight:** Uses standard Python libraries (`tkinter`, `colorsys`, etc.) plus `screeninfo`. No bulky frameworks or vendor software needed.
*   **Persistent Settings:** Appearance settings (not monitor selection) are saved and loaded automatically.

## Requirements

*   **Python 3.x**
*   **Windows Operating System**
*   Python Libraries:
    *   `screeninfo` (for detecting monitors)
    *   Standard libraries: `tkinter`, `colorsys`, `math`, `time`, `threading`, `json`, `os`, `sys` (usually included with Python)

## Installation

1.  **Clone or Download:**
    ```bash
    git clone https://github.com/BTawaifi/Python-EdgeRGB-Terminal.git
    cd Python-EdgeRGB-Terminal
    ```
    Or download the ZIP file and extract it.

2.  **Install Dependencies:**
    ```bash
    pip install tkinter
    pip install screeninfo
    ```

## Usage

1.  **Open Terminal:** Navigate to the script's directory in your terminal (Command Prompt, PowerShell, etc.).
    ```bash
    cd path/to/Python-EdgeRGB-Terminal
    ```

2.  **Run the Script:**
    ```bash
    python edge_rgb_terminal.py
    ```

3.  **Select Monitors:** The script will list detected monitors and prompt you for selection:
    ```
    --- Monitor Selection ---
      [0] \\.\DISPLAY1 1920x1080@0,0 (Primary)
      [1] \\.\DISPLAY2 1920x1080@1920,0
    Enter monitor numbers (e.g., 0,1), 'all', or leave blank for [Primary only (0)]:
    ```
    *   Enter specific numbers separated by commas (e.g., `0,1`).
    *   Enter `all` to enable on all detected monitors.
    *   Press `Enter` (leave blank) to default to the primary monitor.

4.  **Enjoy:** The RGB lights should appear on the edges of your selected screen(s).

5.  **Stop the Script:** Press `Ctrl+C` in the terminal where the script is running.

## Configuration

The script automatically creates and uses a file named `edge_rgb_settings.json` in the same directory to store appearance settings. You can manually edit this file (while the script is not running) to fine-tune the effect:

*   `"thickness"`: Thickness of the light bars in pixels (e.g., `5`).
*   `"update_ms"`: Target time in milliseconds between updates (lower is faster, e.g., `15` for ~66fps target). Performance depends on your system.
*   `"hue_speed"`: How fast the color spectrum cycles (lower is slower, e.g., `0.005`).
*   `"brightness"`: Overall brightness (0.1 to 1.0).
*   `"saturation"`: Color intensity (0.0 for white/gray, 1.0 for full color).
*   `"segment_len"`: Approximate length of each colored segment in pixels (e.g., `30`). Smaller values mean more segments and potentially higher CPU usage.

**Note:** Monitor selection (`selected_monitors`) and the enabled state are **not** saved in this file for the terminal version; selection happens live each time you run it.

## How It Works

The script uses Python's built-in `tkinter` library to create four borderless, always-on-top, click-through windows positioned at the edges of the selected monitor(s). It then draws colored rectangles (segments) on these windows and animates their colors using `colorsys` and a background `threading.Thread` to simulate the moving RGB effect without blocking the main thread (which waits for Ctrl+C). `screeninfo` is used to get monitor dimensions and positions.

## Limitations

*   **Not a True Overlay:** These are actual windows, although set to be click-through (`-disabled`, `-toolwindow` attributes). They might still interfere with *some* specific full-screen applications or edge interactions depending on the application and Windows behavior.
*   **Full-Screen Applications:** Behavior with exclusive full-screen games or applications can be unpredictable. The lights might be hidden or cause issues. Windowed or borderless full-screen modes generally work better.
*   **Performance:** Can consume some CPU resources, especially with very small `segment_len` values, low `update_ms`, or across multiple high-resolution monitors. Adjust settings if you notice performance impacts.
*   **Window Positioning:** Exact edge alignment might have minor offsets due to Tkinter/Windows positioning nuances or OS scaling settings.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
