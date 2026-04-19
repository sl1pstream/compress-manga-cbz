> **DISCLAIMER:** While there is (clearly) no harmful code in this script, which can be verified by reading through the python script, it is the responsibility of the end user to verify that for themselves. There are plenty of bad actors in the scene, especially with python scripts. **Never run a script you found on the internet unless you understand what the code actually does. Even if the script has comments, it should still not be blindly trusted.**

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

*This is currently very roughly done. Please be aware that it isn't easy to get the exact target size. If you have a better method that gets the final resulting total size closer to the target size, open a pull request*

### Example Run
<img width="534" height="503" alt="image" src="https://github.com/user-attachments/assets/c56f7498-30ee-484a-8bb8-3b195e2a6e58" />


### Compression Guidelines
The script includes recommended compression target sizes based on the original total size (total size *not* including non-cbz files):
- ≤ 600MB: Don't compress
- ≤ 1.5GB: Target 500MB
- ≤ 2.5GB: Target 1024MB
- ≤ 3.5GB: Target 1500MB
- ≤ 4.5GB: Target 2048MB
- ≤ 5.5GB: Target 2500MB
- ≤ 6.5GB: Target 3072MB
- ≤ 7.5GB: Target 3500MB
- ≤ 8.5GB: Target 4069MB
- ≤ 9.5GB: Target 4500MB


(these are also included at the top of the script file itself)
