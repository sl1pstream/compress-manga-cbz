#!/usr/bin/env python3

import os
import sys
import zipfile
import subprocess
import shutil
from pathlib import Path
from PIL import Image
import io

# COMPRESSION GUIDE (by size) # 
# ≤ 600MB: Don't compress 
# ≤ 1.5GB: 500MB 
# ≤ 2.5GB: 1024MB 
# ≤ 3.5GB: 1500MB 
# ≤ 4.5GB: 2048MB
# ≤ 5.5GB: 2500MB
# ≤ 6.5GB: 3072MB
# ≤ 7.5GB: 3500MB
# ≤ 8.5GB: 4096MB
# ≤ 9.5GB: 4500MB


# ---------------- UI ---------------- #

def kdialog_select_folder(title):
    result = subprocess.run(
        ['kdialog', '--getexistingdirectory', os.path.expanduser('~'), '--title', title],
        capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


def kdialog_error(message):
    subprocess.run(['kdialog', '--error', message])


def kdialog_input(title, message, default=""):
    result = subprocess.run(
        ['kdialog', '--inputbox', message, default, '--title', title],
        capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None


# ---------------- IMAGE COMPRESSION ---------------- #

def compress_image_to_size(img, target_size):
    low, high = 10, 95
    best_data = None

    while low <= high:
        q = (low + high) // 2

        output = io.BytesIO()
        img.save(output, format='JPEG', quality=q, optimize=True)
        data = output.getvalue()
        size = len(data)

        if size > target_size:
            high = q - 1
        else:
            best_data = data
            low = q + 1

    return best_data if best_data else data


# ---------------- GLOBAL SCAN ---------------- #

def compute_total_image_size(cbz_files):
    total = 0

    for cbz in cbz_files:
        with zipfile.ZipFile(cbz, 'r') as z:
            for name in z.namelist():
                if name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    try:
                        total += len(z.read(name))
                    except:
                        pass
    return total


# ---------------- PER-CBZ PROCESSING ---------------- #

def compress_cbz_per_image(input_path, output_path, global_ratio):
    with zipfile.ZipFile(input_path, 'r') as zin:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:

            for item in zin.namelist():
                try:
                    data = zin.read(item)
                except:
                    continue

                if item.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    try:
                        img = Image.open(io.BytesIO(data))

                        if img.mode in ('RGBA', 'LA', 'P'):
                            img = img.convert('RGB')

                        original_size = len(data)
                        target_size = max(1024, int(original_size * global_ratio))

                        compressed = compress_image_to_size(img, target_size)

                        item = os.path.splitext(item)[0] + '.jpg'
                        zout.writestr(item, compressed)

                    except:
                        zout.writestr(item, data)
                else:
                    zout.writestr(item, data)


# ---------------- PASS SYSTEM ---------------- #

def run_pass(cbz_files, output_folder, ratio):
    if output_folder.exists():
        shutil.rmtree(output_folder)
    output_folder.mkdir(parents=True)

    total_files = len(cbz_files)
    for idx, cbz in enumerate(cbz_files, 1):
        out = output_folder / cbz.name
        compress_cbz_per_image(cbz, out, ratio)
        print(f"\rProgress: {idx}/{total_files}", end='', flush=True)
    
    print()  # New line after progress

    total = 0
    for f in output_folder.glob("*.cbz"):
        total += f.stat().st_size

    return total


def dynamic_compress(cbz_files, output_folder, target_size, tolerance=50*1024*1024):
    print("Scanning image sizes...")
    total_image_size = compute_total_image_size(cbz_files)

    if total_image_size == 0:
        raise RuntimeError("No images found")

    base_ratio = target_size / total_image_size
    current_ratio = base_ratio
    pass_num = 0

    while True:
        pass_num += 1
        print(f"\nPass {pass_num}")
        print(f"Testing ratio: {current_ratio:.4f}")

        final_size = run_pass(cbz_files, output_folder, current_ratio)
        diff = final_size - target_size

        print(f"Result: {final_size/1e6:.2f} MB | Target: {target_size/1e6:.2f} MB | Diff: {diff/1e6:+.2f} MB")

        # Accept only if at or below target, within tolerance
        if diff <= 0 and abs(diff) <= tolerance:
            print("✓ Within tolerance. Done.")
            return

        # Dynamically adjust ratio based on how far off we are
        adjustment_factor = target_size / final_size
        current_ratio *= adjustment_factor
        
        print(f"Adjusting ratio by {adjustment_factor:.4f}x → new ratio: {current_ratio:.4f}")


# ---------------- UTILS ---------------- #

def get_folder_size(folder):
    total = 0
    for f in folder.glob("*.cbz"):
        total += f.stat().st_size
    return total


# ---------------- MAIN ---------------- #

def main():
    source_folder = kdialog_select_folder("Select CBZ folder")
    if not source_folder:
        sys.exit(0)

    cbz_files = list(Path(source_folder).glob("*.cbz"))
    if not cbz_files:
        kdialog_error("No CBZ files found")
        sys.exit(1)

    save_dir = kdialog_select_folder("Select output folder")
    if not save_dir:
        sys.exit(0)

    if Path(source_folder).resolve() == Path(save_dir).resolve():
        kdialog_error("Output folder must be different")
        sys.exit(1)

    total_size_bytes = get_folder_size(Path(source_folder))
    total_size_mb = total_size_bytes / (1000 * 1000)
    total_size_gb = total_size_bytes / (1000 * 1000 * 1000)

    if total_size_mb >= 1000:
        size_display = f"{total_size_gb:.2f} GB"
        default_target = str(int(total_size_mb * 0.5))
    else:
        size_display = f"{total_size_mb:.2f} MB"
        default_target = str(int(total_size_mb * 0.5))

    target = kdialog_input(
        "Target Size",
        f"Total size of CBZ files: {size_display}\n\nEnter target size in MB:",
        default_target
    )

    if not target:
        sys.exit(0)

    try:
        target_size_mb = float(target)
        if target_size_mb <= 0:
            raise ValueError
    except:
        kdialog_error("Invalid target size")
        sys.exit(1)

    target_size_bytes = target_size_mb * 1000 * 1000

    output_folder = Path(save_dir) / Path(source_folder).name

    dynamic_compress(
        cbz_files,
        output_folder,
        target_size_bytes,
        tolerance=50 * 1024 * 1024
    )

    # Copy non-CBZ files
    for file in Path(source_folder).iterdir():
        if file.is_file() and not file.name.endswith('.cbz'):
            shutil.copy2(file, output_folder / file.name)


if __name__ == "__main__":
    main()
