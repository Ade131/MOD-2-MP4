import os
import subprocess
import threading
import time
import re
from tkinter import Tk, Button, filedialog, StringVar
from collections import Counter


def log_message(message, overwrite=False):
    """
    Logs a message with a timestamp.

    Args:
        message (str): The message to log.
        overwrite (bool): If True, overwrite the current line in the console.
    """
    timestamp = time.strftime('%H:%M:%S')
    full_message = f"[{timestamp}] {message}"
    if overwrite:
        print(f"\r{full_message}", end='')
    else:
        print(f"\r{full_message}\n", end='')


def get_total_frames(file_path):
    """
    Gets the total number of frames in a video file using ffprobe.

    Args:
        file_path (str): Path to the video file.

    Returns:
        int: Total number of frames, or None if an error occurs.
    """
    try:
        # Command to get frame rate and duration of the video
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=duration,r_frame_rate", "-of", "default=nokey=1:noprint_wrappers=1", file_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        frame_rate_str, duration_str = result.stdout.strip().split('\n')

        # Calculate frame rate
        if '/' in frame_rate_str:
            numerator, denominator = map(float, frame_rate_str.split('/'))
            frame_rate = numerator / denominator
        else:
            frame_rate = float(frame_rate_str)

        # Calculate total frames
        duration = float(duration_str)
        total_frames = duration * frame_rate

        return int(total_frames)
    except Exception as e:
        log_message(f"Error estimating total frames: {e}")
        return None


def track_progress(process, total_frames, current_file, total_files):
    """
    Tracks and displays the progress of the video conversion.

    Args:
        process (subprocess.Popen): The subprocess running the conversion.
        total_frames (int): Total number of frames in the video.
        current_file (int): Index of the current file being converted.
        total_files (int): Total number of files to convert.
    """
    start_time = time.time()
    bar_length = 20
    pattern = re.compile(r"frame=\s*(\d+)")

    while True:
        line = process.stderr.readline()
        if line == '' and process.poll() is not None:
            break

        matches = pattern.search(line)
        if matches:
            current_frame = int(matches.group(1))
            progress = min((current_frame / total_frames) * 100, 100.0)
            filled_length = int(bar_length * current_frame // total_frames)
            bar = '|' * filled_length + '-' * (bar_length - filled_length)

            if progress >= 100.0:
                total_time = time.time() - start_time
                log_message(
                    f"[{current_file}/{total_files}] Conversion Complete: 100% - Time taken: {total_time:.2f} seconds",
                    overwrite=True)
                print()  # Move to the next line after completion
                break
            else:
                log_message(f"[{current_file}/{total_files}] Progress on file - {progress:.2f}% - [{bar}]",
                            overwrite=True)


def count_mod_files(directory):
    """
    Counts the number of .MOD files in a directory.

    Args:
        directory (str): The directory to scan.

    Returns:
        int: The number of .MOD files found.
    """
    log_message("Scanning...")
    count = sum(1 for _, _, files in os.walk(directory) for file in files if file.endswith(".MOD"))
    log_message(f"Found {count} .MOD files")
    return count


def most_common_date(dates):
    """
    Finds the most common date in a list of dates.

    Args:
        dates (list): A list of date strings.

    Returns:
        str: The most common date, or None if the list is empty.
    """
    if dates:
        return Counter(dates).most_common(1)[0][0]
    return None


def extract_date(file_path):
    """
    Extracts the last modified date from a file.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The last modified date in 'dd-mm-YYYY - HHMM' format or 'unknown_date'.
    """
    try:
        last_modified_timestamp = os.path.getmtime(file_path)
        return time.strftime('%d-%m-%Y - %H%M', time.localtime(last_modified_timestamp))
    except Exception as e:
        log_message(f"Date extraction failed: {e}")
        return "unknown_date"


def convert_and_rename(directory, total_files, start_button, failed_files):
    """
    Converts MOD files to MP4 and moves original MOD, MOI, and PGI files to 'Original files' folder.

    Args:
        directory (str): Directory to scan for MOD files.
        total_files (int): Total number of MOD files to convert.
        start_button (Button): The start button from the GUI.
        failed_files (list): List to append names of files that failed to convert.
    """
    log_message("Starting conversion process...")
    converted_count = 0

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d.lower() != 'original files']
        mod_files = [f for f in files if f.endswith(".MOD")]
        additional_files = [f for f in files if f.endswith((".MOI", ".PGI"))]

        if not mod_files:
            continue

        original_folder = os.path.join(root, "Original files")
        os.makedirs(original_folder, exist_ok=True)

        for file_name in mod_files:
            mod_file = os.path.join(root, file_name)
            mp4_file = os.path.join(root, os.path.splitext(file_name)[0] + ".MP4")

            total_frames = get_total_frames(mod_file)
            if total_frames is None:
                failed_files.append(mod_file)
                log_message(f"Skipping file due to error in frame count: {mod_file}")
                continue

            try:
                log_message(f"Starting conversion for {mod_file}")
                process = subprocess.Popen(["ffmpeg", "-i", mod_file, mp4_file], stderr=subprocess.PIPE, text=True)
                progress_thread = threading.Thread(target=track_progress,
                                                   args=(process, total_frames, converted_count + 1, total_files),
                                                   daemon=True)
                progress_thread.start()
                process.wait()
                progress_thread.join()
                process.stderr.close()

                log_message(f"Conversion completed for {mod_file}")
                os.rename(mod_file, os.path.join(original_folder, os.path.basename(mod_file)))
                converted_count += 1
            except subprocess.CalledProcessError as e:
                failed_files.append(mod_file)
                log_message(f"Error converting {mod_file}: {e.stderr.decode().strip()}")

        # Move additional files after all MOD files are processed
        for file in additional_files:
            if os.path.exists(file):
                try:
                    os.rename(file, os.path.join(original_folder, os.path.basename(file)))
                except Exception as e:
                    log_message(f"Error moving file {file}: {e}")

        log_message(f"Conversion complete for folder '{root}'. Converted {len(mod_files)} files.")
        if failed_files:
            log_message("Unable to convert some files:\n- " + "\n- ".join(failed_files))

    start_button['state'] = 'normal'


# GUI Setup
window = Tk()
window.title("MOD to MP4 Converter")

# StringVar to hold the path of the selected directory
directory_text = StringVar(window)
directory_text.set("No directory selected")


def select_directory(directory_text, select_directory_button, start_button):
    """
    Opens a dialog for the user to select a directory and updates the GUI accordingly.

    Args:
        directory_text (StringVar): StringVar associated with the directory path.
        select_directory_button (Button): Button for selecting directory.
        start_button (Button): Button to start the conversion process.
    """
    directory = filedialog.askdirectory()
    if directory:
        directory_text.set(f"Selected Directory: {directory}")
        start_button['state'] = 'normal'
        log_message("Directory selected: " + directory)
    window.update()


# Button to select the directory for conversion
select_directory_button = Button(window, text="Select Directory",
                                 command=lambda: select_directory(directory_text, select_directory_button,
                                                                  start_button))
select_directory_button.pack(side='top', pady=5)  # Add the button to the window

# Button to start the conversion process, initially disabled
start_button = Button(window, text="Start", state='disabled',
                      command=lambda: start_conversion_thread(directory_text.get().replace("Selected Directory: ", ""),
                                                              start_button, select_directory_button))
start_button.pack(side='top', pady=5)  # Add the start button to the window


def start_conversion_thread(directory, start_button, select_directory_button):
    """
    Starts the conversion process in a separate thread.

    Args:
        directory (str): The selected directory for conversion.
        start_button (Button): Button to start the conversion process.
        select_directory_button (Button): Button for selecting directory.
    """

    def thread_target():
        # Disable buttons while conversion is in progress
        select_directory_button['state'] = 'disabled'
        start_button['state'] = 'disabled'
        failed_files = []  # List to track failed conversions

        total_mod_files = count_mod_files(directory)  # Count the number of MOD files
        log_message(f"Found {total_mod_files} .MOD files across all folders")

        # Start the conversion process
        convert_and_rename(directory, total_mod_files, start_button, failed_files)

        # Re-enable buttons after conversion is complete
        start_button['state'] = 'normal'
        select_directory_button['state'] = 'normal'

    # Start the conversion in a separate thread to keep the GUI responsive
    threading.Thread(target=thread_target, daemon=True).start()


window.mainloop()
