# edge_rgb_terminal.py

import tkinter as tk
# No ttk needed anymore
import colorsys
import math
import time
import threading
import json
import os
import sys
import screeninfo
# No pystray or PIL needed anymore
import traceback # For detailed error printing

# --- Constants ---
SETTINGS_FILE = "edge_rgb_settings.json"

# Default values - Monitor selection will be ignored from file/defaults now
DEFAULT_SETTINGS = {
    "thickness": 5,
    "update_ms": 15,
    "hue_speed": 0.005,
    "brightness": 1.0,
    "saturation": 1.0,
    "segment_len": 30,
    # "enabled": True, # We'll assume enabled if run
    # "selected_monitors": [0] # This will be determined at runtime
}

# --- Lighting Controller Class (Mostly Unchanged) ---
# [Keep the LightingController class exactly as it was in the previous full code listing]
# ... (Including __init__, stop, _shutdown_tk, run, _create_monitor_lights, _create_edge_window, _get_color, update_colors)
# Important: Make sure the debug prints inside LightingController are still present if you want detailed logs.

class LightingController(threading.Thread):
    def __init__(self, settings, monitors, selected_indices):
        super().__init__(daemon=True)
        self.settings = settings # Should contain thickness, speed etc.
        self.monitors = monitors # List of screeninfo.Monitor objects
        self.selected_indices = selected_indices # List of monitor indices to use
        self._stop_event = threading.Event()
        self.tk_root = None
        self.monitor_elements = {} # Store canvases and rects per monitor
        print("DEBUG: LightingController.__init__")

        # Apply defaults for non-monitor settings if missing
        for key, value in DEFAULT_SETTINGS.items():
            self.settings.setdefault(key, value)

    def stop(self):
        print("DEBUG: LightingController.stop() called.")
        self._stop_event.set()
        if self.tk_root:
            print("DEBUG: LightingController.stop() - Scheduling _shutdown_tk.")
            self.tk_root.after(0, self._shutdown_tk)
        else:
             print("DEBUG: LightingController.stop() - No tk_root to schedule shutdown for.")

    def _shutdown_tk(self):
        print("DEBUG: LightingController._shutdown_tk() called.")
        if self.tk_root:
            print("DEBUG: LightingController._shutdown_tk() - Root exists, attempting quit/destroy.")
            try:
                self.tk_root.quit()
                self.tk_root.destroy()
                print("DEBUG: LightingController._shutdown_tk() - Root quit and destroyed.")
            except tk.TclError as e:
                print(f"DEBUG: LightingController._shutdown_tk() - TclError during quit/destroy (normal if already closing): {e}")
                pass
            except Exception as e:
                print(f"ERROR: LightingController._shutdown_tk() - Unexpected error during quit/destroy: {e}")
                traceback.print_exc()
            finally:
                self.tk_root = None
                self.monitor_elements = {}
        else:
             print("DEBUG: LightingController._shutdown_tk() - tk_root was already None.")

    def run(self):
        """Main loop for the lighting thread."""
        print("DEBUG: LightingController.run() - Thread started.")
        if not self.selected_indices:
            print("DEBUG: LightingController.run() - Exiting: No monitors selected during startup.")
            return

        print(f"DEBUG: LightingController.run() - Target monitor indices: {self.selected_indices}")

        try:
            print("DEBUG: LightingController.run() - Creating Tk root.")
            self.tk_root = tk.Tk()
            self.tk_root.withdraw()

            # Create windows ONLY for selected monitors
            for i in self.selected_indices:
                if 0 <= i < len(self.monitors):
                    monitor = self.monitors[i]
                    print(f"DEBUG: LightingController.run() - Initializing lights for Monitor {i} ({monitor.width}x{monitor.height} at {monitor.x},{monitor.y})")
                    self._create_monitor_lights(monitor, i)
                else:
                    print(f"WARNING: LightingController.run() - Invalid monitor index {i} encountered (should have been caught earlier). Skipping.")


            if not self.monitor_elements:
                print("ERROR: LightingController.run() - No valid monitor elements created. Exiting thread.")
                if self.tk_root: self.tk_root.destroy()
                self.tk_root = None
                return

            print("DEBUG: LightingController.run() - Starting animation loop (scheduling update_colors).")
            self.hue_offset = 0.0
            self.tk_root.after(0, self.update_colors)
            print("DEBUG: LightingController.run() - Starting Tkinter mainloop.")
            self.tk_root.mainloop()
            print("DEBUG: LightingController.run() - Tkinter mainloop finished.")

        except Exception as e:
            print(f"ERROR: LightingController.run() - Unhandled exception in thread: {e}")
            traceback.print_exc()
        finally:
            print("DEBUG: LightingController.run() - Finally block reached, ensuring cleanup.")
            if self.tk_root: self._shutdown_tk()
            print("DEBUG: LightingController.run() - Thread finished.")

    def _create_monitor_lights(self, monitor, monitor_index):
        """Creates the four edge windows for a specific monitor."""
        print(f"DEBUG: LightingController._create_monitor_lights({monitor_index})")
        thickness = self.settings.get("thickness", 5)
        seg_len = self.settings.get("segment_len", 30)

        m_width = monitor.width; m_height = monitor.height
        m_x = monitor.x; m_y = monitor.y

        segments_h = max(1, m_width // seg_len)
        segments_v = max(1, m_height // seg_len)
        total_segments = 2 * segments_h + 2 * segments_v

        seg_width = m_width / segments_h if segments_h > 0 else m_width
        seg_height = m_height / segments_v if segments_v > 0 else m_height

        print(f"DEBUG: Monitor {monitor_index} - Segments H: {segments_h}, V: {segments_v}, Total: {total_segments}")
        print(f"DEBUG: Monitor {monitor_index} - Seg W: {seg_width:.2f}, H: {seg_height:.2f}")

        canvases = {}; rect_ids = {'top': [], 'bottom': [], 'left': [], 'right': []}

        try:
            canvases['top'], rect_ids['top'] = self._create_edge_window(f"{m_width}x{thickness}+{m_x}+{m_y}",'horizontal', segments_h, seg_width, thickness, monitor_index, 'top')
            canvases['bottom'], rect_ids['bottom'] = self._create_edge_window(f"{m_width}x{thickness}+{m_x}+{m_y + m_height - thickness}",'horizontal', segments_h, seg_width, thickness, monitor_index, 'bottom')
            canvases['left'], rect_ids['left'] = self._create_edge_window(f"{thickness}x{m_height}+{m_x}+{m_y}",'vertical', segments_v, thickness, seg_height, monitor_index, 'left')
            canvases['right'], rect_ids['right'] = self._create_edge_window(f"{thickness}x{m_height}+{m_x + m_width - thickness}+{m_y}",'vertical', segments_v, thickness, seg_height, monitor_index, 'right')

            self.monitor_elements[monitor_index] = {'canvases': canvases, 'rect_ids': rect_ids, 'segments_h': segments_h, 'segments_v': segments_v, 'total_segments': total_segments}
            print(f"DEBUG: LightingController._create_monitor_lights({monitor_index}) - Successfully created windows.")
        except Exception as e:
             print(f"ERROR: LightingController._create_monitor_lights({monitor_index}) - Failed to create windows: {e}")
             traceback.print_exc()

    def _create_edge_window(self, geometry, orientation, num_segments, seg_w, seg_h, monitor_index, edge_name):
        """Helper function to create a single borderless edge window."""
        print(f"DEBUG: _create_edge_window({monitor_index}, {edge_name}) - Geo: {geometry}")
        if not self.tk_root:
            print(f"ERROR: _create_edge_window({monitor_index}, {edge_name}) - tk_root is None!")
            return None, []
        try:
            win = tk.Toplevel(self.tk_root)
            win.overrideredirect(True); win.geometry(geometry)
            win.attributes("-topmost", True); win.attributes("-disabled", True); win.attributes("-toolwindow", True)
            canvas = tk.Canvas(win, highlightthickness=0, bg='black')
            canvas.pack(fill=tk.BOTH, expand=tk.YES)
            rect_ids = []
            for i in range(num_segments):
                if orientation == 'horizontal': x1, y1, x2, y2 = i * seg_w, 0, (i + 1) * seg_w, seg_h
                else: x1, y1, x2, y2 = 0, i * seg_h, seg_w, (i + 1) * seg_h
                x1, y1, x2, y2 = map(math.floor, [x1, y1, x2, y2])
                x2 = max(x1 + 1, x2); y2 = max(y1 + 1, y2)
                rect_id = canvas.create_rectangle(x1, y1, x2, y2, fill='black', outline='')
                rect_ids.append(rect_id)
            print(f"DEBUG: _create_edge_window({monitor_index}, {edge_name}) - Created {len(rect_ids)} segments.")
            return canvas, rect_ids
        except Exception as e_create:
             print(f"ERROR: _create_edge_window({monitor_index}, {edge_name}) - Exception: {e_create}")
             traceback.print_exc()
             return None, []

    def _get_color(self, segment_index, total_segments, current_hue_offset):
        hue_fraction = segment_index / max(1, total_segments)
        hue = (current_hue_offset + hue_fraction) % 1.0
        sat = max(0.0, min(1.0, self.settings.get("saturation", 1.0)))
        bri = max(0.0, min(1.0, self.settings.get("brightness", 1.0)))
        r, g, b = colorsys.hsv_to_rgb(hue, sat, bri)
        return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

    def update_colors(self):
        if self._stop_event.is_set(): return
        if not self.tk_root or not hasattr(self.tk_root, 'winfo_exists') or not self.tk_root.winfo_exists(): return

        try:
            start_time = time.perf_counter()
            hue_speed = self.settings.get("hue_speed", 0.005)
            self.hue_offset = (self.hue_offset + hue_speed) % 1.0

            for monitor_index, elements in list(self.monitor_elements.items()):
                # No need to check selected_indices here, only created elements for selected ones
                canvases = elements.get('canvases'); rect_ids = elements.get('rect_ids')
                segments_h = elements.get('segments_h'); segments_v = elements.get('segments_v')
                total_segments = elements.get('total_segments')

                if not canvases or not rect_ids or segments_h is None or segments_v is None or total_segments is None: continue
                if not all(c and hasattr(c, 'winfo_exists') and c.winfo_exists() for c in canvases.values()): continue

                current_segment = 0
                def update_edge(edge, count, reverse_index=False):
                    nonlocal current_segment
                    rect_list = rect_ids.get(edge, []); canvas = canvases.get(edge)
                    if not canvas or not rect_list: return
                    for i in range(count):
                        list_index = (count - 1 - i) if reverse_index else i
                        if 0 <= list_index < len(rect_list):
                            color = self._get_color(current_segment, total_segments, self.hue_offset)
                            if canvas.find_withtag(rect_list[list_index]): canvas.itemconfig(rect_list[list_index], fill=color)
                        current_segment += 1
                update_edge('top', segments_h); update_edge('right', segments_v)
                update_edge('bottom', segments_h, reverse_index=True); update_edge('left', segments_v, reverse_index=True)

            update_ms = self.settings.get("update_ms", 15)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            delay = max(1, update_ms - int(elapsed_ms))

            if not self._stop_event.is_set() and self.tk_root and self.tk_root.winfo_exists():
                self.tk_root.after(delay, self.update_colors)
            # else: print("DEBUG: update_colors - Not scheduling next update.") # Too noisy
        except tk.TclError as e:
            if "invalid command name" in str(e): pass # print(f"WARNING: update_colors - TclError (widget destroyed): {e}")
            else: print(f"ERROR: update_colors - TclError: {e}"); traceback.print_exc(); self.stop()
        except Exception as e:
            print(f"ERROR: update_colors - Unexpected error: {e}"); traceback.print_exc(); self.stop()

# --- Main Application Class (Simplified) ---

class EdgeRgbAppTerminal:
    def __init__(self):
        print("DEBUG: EdgeRgbAppTerminal.__init__ - Start")
        self.settings = self.load_settings() # Load non-monitor settings
        self.monitors = []
        try:
            self.monitors = screeninfo.get_monitors()
        except screeninfo.common.ScreenInfoError as e:
            print(f"ERROR getting monitor info: {e}")
        except Exception as e:
            print(f"UNEXPECTED ERROR getting monitor info: {e}")
            traceback.print_exc()

        self.lighting_thread = None
        self.selected_monitor_indices = []

        print(f"DEBUG: EdgeRgbAppTerminal.__init__ - Settings loaded: {self.settings}")
        print("DEBUG: EdgeRgbAppTerminal.__init__ - End")

    def load_settings(self):
        """Loads settings, ignoring 'selected_monitors' and 'enabled'."""
        print(f"DEBUG: load_settings() - Attempting to load '{SETTINGS_FILE}'...")
        loaded_settings = {}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    loaded_settings = json.load(f)
                print("DEBUG: load_settings() - File found and loaded.")
                if not isinstance(loaded_settings, dict):
                    print(f"ERROR: Invalid format in {SETTINGS_FILE} (not a dict). Using defaults only.")
                    loaded_settings = {}
            except json.JSONDecodeError as e:
                print(f"ERROR: Could not decode {SETTINGS_FILE}: {e}. Using defaults only.")
                loaded_settings = {}
            except Exception as e:
                 print(f"ERROR loading settings from {SETTINGS_FILE}: {e}. Using defaults only.")
                 traceback.print_exc()
                 loaded_settings = {}
        else:
            print(f"DEBUG: load_settings() - {SETTINGS_FILE} not found. Using defaults only.")

        # Apply defaults for keys not found in the file
        final_settings = DEFAULT_SETTINGS.copy() # Start with defaults
        final_settings.update(loaded_settings) # Override with loaded values

        # Explicitly remove keys we don't want to persist or load
        final_settings.pop("selected_monitors", None)
        final_settings.pop("enabled", None)

        return final_settings

    def save_settings(self):
        """Saves settings, excluding 'selected_monitors' and 'enabled'."""
        print(f"DEBUG: save_settings() - Saving to '{SETTINGS_FILE}'")
        settings_to_save = self.settings.copy()
        settings_to_save.pop("selected_monitors", None)
        settings_to_save.pop("enabled", None)

        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings_to_save, f, indent=4)
            print("DEBUG: save_settings() - Save successful.")
        except Exception as e:
            print(f"ERROR saving settings to {SETTINGS_FILE}: {e}")
            traceback.print_exc()

    def select_monitors_terminal(self):
        """Displays monitors and prompts user for selection via terminal input."""
        print("\n--- Monitor Selection ---")
        if not self.monitors:
            print("No monitors detected. Cannot start lighting.")
            return False

        monitor_details = []
        primary_index = -1
        for i, m in enumerate(self.monitors):
            primary_str = ""
            if m.is_primary:
                primary_str = " (Primary)"
                primary_index = i
            monitor_name = m.name if hasattr(m, 'name') and m.name else '[No Name]'
            details = f"  [{i}] {monitor_name} {m.width}x{m.height}@{m.x},{m.y}{primary_str}"
            monitor_details.append(details)
            print(details)

        # Construct prompt string
        prompt_default = f"Primary only ({primary_index})" if primary_index != -1 else "No primary found"
        prompt = f"Enter monitor numbers (e.g., 0,1), 'all', or leave blank for [{prompt_default}]: "

        while True:
            try:
                raw_input = input(prompt).strip().lower() # Read input, trim whitespace, make lowercase

                # Option 1: Empty input (Default to Primary)
                if not raw_input:
                     if primary_index != -1:
                         self.selected_monitor_indices = [primary_index]
                         print(f"Defaulting to primary monitor: {self.selected_monitor_indices}")
                         return True
                     else:
                          print("Could not determine primary monitor. Please enter a number or 'all'.")
                          continue # Re-prompt

                # Option 2: Select 'all'
                elif raw_input == 'all':
                     self.selected_monitor_indices = list(range(len(self.monitors)))
                     print(f"Selected ALL monitors: {self.selected_monitor_indices}")
                     return True

                # Option 3: Comma-separated numbers
                else:
                    selected_strings = [s.strip() for s in raw_input.split(',')]
                    selected_indices_temp = []
                    valid_input = True
                    max_index = len(self.monitors) - 1

                    for s in selected_strings:
                        if not s: continue # Skip empty parts like in "0,,1"
                        if not s.isdigit():
                            print(f"Error: Input '{s}' is not a valid number.")
                            valid_input = False
                            break
                        index = int(s)
                        if 0 <= index <= max_index:
                            if index not in selected_indices_temp:
                                selected_indices_temp.append(index)
                        else:
                            print(f"Error: Monitor number '{index}' is out of range (0-{max_index}).")
                            valid_input = False
                            break

                    if valid_input and selected_indices_temp:
                        self.selected_monitor_indices = sorted(selected_indices_temp)
                        print(f"Selected monitors: {self.selected_monitor_indices}")
                        return True
                    elif valid_input and not selected_indices_temp:
                         print("No valid monitor numbers entered. Please try again.")
                    # If not valid_input, error was already printed

            except ValueError: # Should be caught by isdigit now, but as fallback
                print("Error: Invalid input. Please enter numbers (0,1), 'all', or leave blank.")
            except Exception as e:
                 print(f"An unexpected error occurred during input: {e}")
                 traceback.print_exc()
                 return False # Exit selection on error

    def start_lighting(self):
        """Starts the LightingController thread with current settings and selection."""
        print("DEBUG: start_lighting() - Entered")
        # Stop previous thread first (if any)
        if self.lighting_thread and self.lighting_thread.is_alive():
            print("DEBUG: start_lighting() - Previous thread found alive, stopping it.")
            self.stop_lighting()
        elif self.lighting_thread:
            self.lighting_thread = None # Clear ref if exists but not alive

        if not self.selected_monitor_indices:
            print("DEBUG: start_lighting() - No monitors selected, not starting thread.")
            return

        print(f"DEBUG: start_lighting() - Starting thread for monitors: {self.selected_monitor_indices}")
        try:
            # Pass settings and the selected indices
            self.lighting_thread = LightingController(
                self.settings.copy(), # Pass copy of non-monitor settings
                self.monitors,
                self.selected_monitor_indices.copy() # Pass copy of selection
            )
            self.lighting_thread.start()
            print("DEBUG: start_lighting() - lighting_thread.start() called.")
            time.sleep(0.05)
            if self.lighting_thread.is_alive():
                print("DEBUG: start_lighting() - lighting_thread is alive after start.")
            else:
                print("ERROR: start_lighting() - lighting_thread is NOT alive shortly after start.")
        except Exception as e:
            print(f"ERROR: start_lighting() - Exception during thread creation/start: {e}")
            traceback.print_exc()
            self.lighting_thread = None
        print("DEBUG: start_lighting() - Exiting function.")

    def stop_lighting(self):
        """Stops the LightingController thread."""
        thread_to_stop = self.lighting_thread
        if thread_to_stop and thread_to_stop.is_alive():
            print("DEBUG: stop_lighting() - Thread found alive, attempting stop...")
            thread_to_stop.stop()
            print("DEBUG: stop_lighting() - Joining thread (timeout 2s)...")
            thread_to_stop.join(timeout=2.0)
            if thread_to_stop.is_alive(): print("ERROR: stop_lighting() - Thread did not stop gracefully.")
            else: print("DEBUG: stop_lighting() - Thread stopped and joined.")
        # Clear reference
        if self.lighting_thread == thread_to_stop: self.lighting_thread = None


    def shutdown(self):
        """Performs clean shutdown."""
        print("DEBUG: shutdown() - Initiating shutdown...")
        self.stop_lighting()
        # Save other settings if desired?
        # self.save_settings()
        print("Edge RGB application stopped.")

    def run(self):
        """Main application entry point."""
        print("--- Edge RGB (Terminal Control) ---")

        if not self.select_monitors_terminal():
            print("Monitor selection failed or cancelled. Exiting.")
            return # Exit if selection fails

        # Monitors selected, start the lighting
        self.start_lighting()

        if not self.lighting_thread or not self.lighting_thread.is_alive():
             print("Failed to start lighting effect. Exiting.")
             return

        print("\nRGB lighting effect started. Press Ctrl+C to stop.")

        # Keep the main thread alive until Ctrl+C
        try:
            while True:
                # Check if the lighting thread died unexpectedly
                if not self.lighting_thread.is_alive():
                     print("\nERROR: Lighting thread stopped unexpectedly. Exiting.")
                     break
                time.sleep(1) # Keep main thread alive but idle
        except KeyboardInterrupt:
            print("\nCtrl+C detected. Shutting down...")
        finally:
            self.shutdown() # Call cleanup method


# --- Main Execution Block ---

if __name__ == "__main__":
    print("--- Script Execution Start ---")
    app = None
    try:
        print("DEBUG: Initializing EdgeRgbAppTerminal...")
        app = EdgeRgbAppTerminal()
        print("DEBUG: Starting EdgeRgbAppTerminal.run()...")
        app.run() # Contains the main loop now
        print("DEBUG: EdgeRgbAppTerminal.run() returned.")
    except Exception as e_main:
        print(f"\nFATAL ERROR in main execution scope: {e_main}")
        traceback.print_exc()
        if app:
             print("DEBUG: Attempting shutdown after fatal error.")
             app.shutdown() # Attempt cleanup
    finally:
        # No lock file handling needed in this version
        print("--- Script Execution End ---")