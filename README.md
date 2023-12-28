# MOD to MP4 Converter

## Introduction
This tool is designed to efficiently convert MOD video files to the MP4 format. Utilizing `ffmpeg` for batch processing of video files. The program is capable of scanning through multiple subfolders inside a chosen parent folder to locate and convert all MOD files.

## Features
- **Batch Conversion**: Converts all MOD files found in the selected directory and its subdirectories to MP4 format.
- **Preservation of Original Files**: Original MOD files are moved to a new folder named "Original files" within their respective directories.
- **Recursive Directory Scanning**: Capable of traversing through multiple layers of subfolders to find and convert MOD files.
- **Progress Tracking**: Displays progress for each file being converted, and overall tracker for number of files converted.
- **Error Handling**: In case of conversion failures, the program moves on to the next file.
- **Simple GUI**: GUI for selecting folder, terminal output for progress and conversion status.

## Requirements
- Python 3.x
- `ffmpeg`
- Tkinter
