# CBZ Compression Tool

A Python utility for batch compressing CBZ (Comic Book ZIP) files with interactive GUI dialogs and intelligent image optimization.

## Why?
You're not gonna notice that small loss in image quality unless you zoom in a ton, or unless you're reading manga on your TV. Why not save some space?

## OS Requirements

- **Linux** (might work with WSL/WSL2 but primarily tested on Linux)
- `kdialog` for GUI dialogs (standard on KDE)

## Features

- Automatic size calculation and compression ratio determination (roughly)
- Preserves non-CBZ files in output directory (i.e. series info for Komga)
- Progress tracking in-terminal during compressio
  
## Usage

### Basic Usage
```bash
python3 compress_cbz.py
```

### Workflow
1. Select source folder containing CBZ files
2. Select output directory (must be different from source. New folder created will have the same name as the original, so this avoids conflicts or loss of data)
3. Review total size and enter target size in MB
4. Script compresses all CBZ files to target size (roughly)

### Compression Guidelines
The script includes recommended compression target sizes based on the original total size (total size *not* including non-cbz files):
- ≤ 600MB: Don't compress
- ≤ 1.5GB: Target 500MB
- ≤ 2.5GB: Target 1024MB
- ≤ 3.5GB: Target 1500MB
- ≤ 4.5GB: Target 2048MB

(these are also included at the top of the script file itself)
