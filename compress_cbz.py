#!/usr/bin/env python3

# COMPRESSION GUIDE (by size) #
# ≤ 600MB: Don't compress 
# ≤ 1.5GB: 500MB
# ≤ 2.5GB: 1024MB
# ≤ 3.5GB: 1500MB
# ≤ 4.5GB: 2048MB

import os
import sys
import zipfile
import subprocess
import shutil
from pathlib import Path
from PIL import Image
import io

def kdialog_select_folder(title):
    result = subprocess.run(['kdialog', '--getexistingdirectory', os.path.expanduser('~'), '--title', title], 
                          capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None

def kdialog_error(message):
    subprocess.run(['kdialog', '--error', message])

def kdialog_input(title, message, default=""):
    result = subprocess.run(['kdialog', '--inputbox', message, default, '--title', title],
                          capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None

def get_folder_size(folder):
    total = 0
    for file in Path(folder).glob('*.cbz'):
        total += file.stat().st_size
    return total

def compress_image_to_target(img_data, target_ratio):
    img = Image.open(io.BytesIO(img_data))
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')
    
    original_size = len(img_data)
    target_size = original_size * target_ratio
    
    # Try different quality levels
    for quality in [85, 75, 65, 55, 45, 35, 25]:
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        if len(output.getvalue()) <= target_size:
            return output.getvalue()
    
    # If still too large, resize and compress
    for scale in [0.9, 0.8, 0.7, 0.6, 0.5]:
        resized = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        output = io.BytesIO()
        resized.save(output, format='JPEG', quality=70, optimize=True)
        if len(output.getvalue()) <= target_size:
            return output.getvalue()
    
    # Last resort
    output = io.BytesIO()
    resized = img.resize((int(img.width * 0.4), int(img.height * 0.4)), Image.LANCZOS)
    resized.save(output, format='JPEG', quality=50, optimize=True)
    return output.getvalue()

def compress_cbz(input_path, output_path, target_ratio):
    with zipfile.ZipFile(input_path, 'r') as zip_in:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            for item in zip_in.namelist():
                data = zip_in.read(item)
                if item.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    try:
                        data = compress_image_to_target(data, target_ratio)
                        if not item.lower().endswith('.jpg'):
                            item = os.path.splitext(item)[0] + '.jpg'
                    except:
                        pass
                zip_out.writestr(item, data)

# Step 1: Select source folder
source_folder = kdialog_select_folder("Select folder containing CBZ files")
if not source_folder:
    sys.exit(0)

cbz_files = list(Path(source_folder).glob('*.cbz'))
if not cbz_files:
    kdialog_error("No CBZ files found in selected folder")
    sys.exit(1)

# Step 2: Select save directory
save_dir = kdialog_select_folder("Select save directory (must be different)")
if not save_dir:
    sys.exit(0)

if Path(source_folder).resolve() == Path(save_dir).resolve():
    kdialog_error("Save directory must be different from source folder")
    sys.exit(1)

# Step 3: Show total size and ask for target
total_size_bytes = get_folder_size(source_folder)
total_size_mb = total_size_bytes / (1000 * 1000)
total_size_gb = total_size_bytes / (1000 * 1000 * 1000)

if total_size_mb >= 1000:
    size_display = f"{total_size_gb:.2f} GB"
    default_target = str(int(total_size_mb * 0.5))
else:
    size_display = f"{total_size_mb:.2f} MB"
    default_target = str(int(total_size_mb * 0.5))

target_size = kdialog_input("Target Size", 
                           f"Total size of CBZ files: {size_display}\n\nEnter target size in MB:",
                           default_target)
if not target_size:
    sys.exit(0)

try:
    target_size_mb = float(target_size)
    if target_size_mb <= 0:
        raise ValueError
except:
    kdialog_error("Invalid target size")
    sys.exit(1)

# Step 4: Calculate target ratio and compress
target_size_bytes = target_size_mb * 1000 * 1000
target_ratio = target_size_bytes / total_size_bytes

folder_name = Path(source_folder).name
output_folder = Path(save_dir) / folder_name
output_folder.mkdir(exist_ok=True)

# Get all files to process
all_files = list(Path(source_folder).iterdir())
total_files = len([f for f in all_files if f.is_file()])
current_file = 0

for cbz_file in cbz_files:
    output_path = output_folder / cbz_file.name
    compress_cbz(cbz_file, output_path, target_ratio)
    current_file += 1
    print(f"\rProgress: {current_file} of {total_files}", end='', flush=True)

# Copy non-CBZ files
for file in Path(source_folder).iterdir():
    if file.is_file() and not file.name.endswith('.cbz'):
        shutil.copy2(file, output_folder / file.name)
        current_file += 1
        print(f"\rProgress: {current_file} of {total_files}", end='', flush=True)

print()  # New line after progress
final_size = get_folder_size(output_folder)
final_size_mb = final_size / (1000 * 1000)
final_size_gb = final_size / (1000 * 1000 * 1000)

if final_size_mb >= 1000:
    final_display = f"{final_size_gb:.2f} GB"
else:
    final_display = f"{final_size_mb:.2f} MB"

if target_size_mb >= 1000:
    target_display = f"{target_size_mb / 1000:.2f} GB"
else:
    target_display = f"{target_size_mb:.2f} MB"

print(f"Compressed {len(cbz_files)} files to {output_folder}\nFinal size: {final_display} (Target: {target_display})")
