#!/usr/bin/env python3

import os
import sys
import zipfile
import subprocess
import shutil
import random
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


def kdialog_yesno(title, message):
    result = subprocess.run(
        ['kdialog', '--yesno', message, '--title', title],
        capture_output=True, text=True
    )
    return result.returncode == 0


# ---------------- IMAGE COMPRESSION ---------------- #

def compress_image_to_size(img, target_size):
    low, high = 10, 100
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


def calculate_next_ratio(attempt_history, target_size, add_randomization=False):
    """Calculate next attempt's starting ratio based on trajectory analysis.
    
    Args:
        attempt_history: List of attempt trajectories, each containing:
                        {'first_pass': (ratio, size), 'final_pass': (ratio, size), 'trajectory': [(ratio, size), ...]}
        target_size: Target size in bytes
        add_randomization: If True, adds ±5% randomization to avoid getting stuck in same pattern
    
    Returns:
        Suggested starting ratio for next attempt, or None if converged
    """
    if not attempt_history:
        return None
    
    # Check for convergence across attempts
    if len(attempt_history) >= 3:
        recent_final_sizes = [attempt['final_pass'][1] for attempt in attempt_history[-3:]]
        size_variance = max(recent_final_sizes) - min(recent_final_sizes)
        if size_variance < 10 * 1024 * 1024:  # Less than 10MB variance
            return None  # Signal convergence
    
    last_attempt = attempt_history[-1]
    first_ratio, first_size = last_attempt['first_pass']
    final_ratio, final_size = last_attempt['final_pass']
    
    # Analyze the trajectory
    trajectory = last_attempt['trajectory']
    first_diff = first_size - target_size
    final_diff = final_size - target_size
    
    # Calculate how much the attempt converged
    convergence = abs(first_diff) - abs(final_diff)
    
    # Determine adjustment based on first pass result and trajectory
    if abs(final_diff) < 50 * 1024 * 1024:  # Within 50MB of target
        # Very close - make small adjustment to first pass ratio
        if final_diff > 0:  # Slightly over
            adjustment = 0.95
        else:  # Slightly under
            adjustment = 1.05
    elif convergence > 0:  # Trajectory was converging well
        # Good convergence - adjust first pass based on how far off it was
        if first_diff > 0:  # Started over target
            # Reduce starting ratio proportionally
            adjustment = 0.85 if abs(first_diff) > 100 * 1024 * 1024 else 0.92
        else:  # Started under target
            adjustment = 1.15 if abs(first_diff) > 100 * 1024 * 1024 else 1.08
    else:  # Poor convergence or diverging
        # Make more aggressive adjustment
        if final_diff > 0:
            adjustment = 0.80
        else:
            adjustment = 1.20
    
    suggested_ratio = first_ratio * adjustment
    
    # Add randomization for retry attempts (helps escape local minima)
    if add_randomization:
        # Add ±5% random variation
        random_factor = random.uniform(0.95, 1.05)
        suggested_ratio *= random_factor
    
    # Avoid ratios too close to previous first passes
    for attempt in attempt_history:
        prev_first_ratio = attempt['first_pass'][0]
        if abs(suggested_ratio - prev_first_ratio) < 0.01:
            suggested_ratio += 0.02 if suggested_ratio > prev_first_ratio else -0.02
    
    # Sanity bounds
    suggested_ratio = max(0.05, min(1.0, suggested_ratio))
    
    return suggested_ratio


def dynamic_compress(cbz_files, output_folder, target_size, tolerance=50*1024*1024):
    total_image_size = compute_total_image_size(cbz_files)

    if total_image_size == 0:
        raise RuntimeError("No images found")

    base_ratio = target_size / total_image_size
    current_ratio = base_ratio
    pass_num = 0
    previous_size = None
    attempt_history = []  # Track full trajectory of each attempt
    current_attempt_trajectory = []  # Track passes within current attempt
    attempt_num = 0
    first_pass_of_attempt = None  # Track first pass of current attempt

    while True:
        pass_num += 1
        print(f"\nPass {pass_num}")
        print(f"Testing ratio: {current_ratio:.4f}")

        final_size = run_pass(cbz_files, output_folder, current_ratio)
        diff = final_size - target_size

        print(f"Result: {final_size/1e6:.2f} MB | Target: {target_size/1e6:.2f} MB | Diff: {diff/1e6:+.2f} MB")

        # Record this pass in current attempt trajectory
        current_attempt_trajectory.append((current_ratio, final_size))
        
        # Record first pass of this attempt
        if first_pass_of_attempt is None:
            first_pass_of_attempt = (current_ratio, final_size)

        # Check for stagnation (if this isn't the first pass)
        if previous_size is not None:
            size_change = abs(final_size - previous_size)
            
            # If size changed less than 5MB between passes
            if size_change < 5 * 1024 * 1024:
                print(f"⚠ Stagnant ({size_change/1e6:.2f}MB change between passes)")
                
                # Record this complete attempt
                attempt_num += 1
                attempt_history.append({
                    'first_pass': first_pass_of_attempt,
                    'final_pass': (current_ratio, final_size),
                    'trajectory': current_attempt_trajectory.copy()
                })
                
                # If we're still far from target, we've hit a ceiling
                if diff > 0 or abs(diff) > tolerance:
                    print(f"✓ Attempt {attempt_num} stagnated at {final_size/1e6:.2f}MB")
                    
                    # Calculate suggested next ratio based on trajectory
                    # Add randomization for attempts after the first to avoid repeating same pattern
                    use_randomization = attempt_num > 1
                    suggested_ratio = calculate_next_ratio(attempt_history, target_size, add_randomization=use_randomization)
                    
                    if suggested_ratio is None:
                        print("\n⚠ Compression attempts converging. Cannot get closer to target.")
                        user_retry = kdialog_yesno(
                            "Compression Stagnated",
                            f"Attempts have converged around {final_size/1e6:.2f}MB.\n"
                            f"Target: {target_size/1e6:.2f}MB\n\n"
                            f"Try another compression ratio anyway?"
                        )
                        if not user_retry:
                            print(f"\n✓ Keeping result: {final_size/1e6:.2f}MB")
                            return
                        # User wants to try anyway, use fallback
                        suggested_ratio = first_pass_of_attempt[0] * (0.9 if diff > 0 else 1.1)
                    
                    # Show history and ask user
                    history_str = "\n".join(
                        f"  Attempt {i+1}: Started {a['first_pass'][1]/1e6:.2f}MB → Stagnated {a['final_pass'][1]/1e6:.2f}MB ({len(a['trajectory'])} passes)"
                        for i, a in enumerate(attempt_history)
                    )
                    
                    user_retry = kdialog_yesno(
                        "Try Different Compression?",
                        f"Current result: {final_size/1e6:.2f}MB\n"
                        f"Target: {target_size/1e6:.2f}MB\n"
                        f"Difference: {diff/1e6:+.2f}MB\n\n"
                        f"Previous attempts:\n{history_str}\n\n"
                        f"Suggested starting ratio: {suggested_ratio:.4f}\n\n"
                        f"Try this ratio?"
                    )
                    
                    if user_retry:
                        print(f"\n🔄 Starting new attempt with ratio {suggested_ratio:.4f}")
                        current_ratio = suggested_ratio
                        previous_size = None
                        pass_num = 0
                        current_attempt_trajectory = []
                        first_pass_of_attempt = None
                        continue
                    else:
                        print(f"\n✓ Keeping result: {final_size/1e6:.2f}MB")
                        return
                else:
                    # Close enough to target
                    print("✓ Within tolerance. Done.")
                    return

        # Accept only if at or below target, within tolerance
        if diff <= 0 and abs(diff) <= tolerance:
            print("✓ Within tolerance. Done.")
            return

        # Save current size for next iteration
        previous_size = final_size
        
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

    # Calculate default target based on compression guide
    if total_size_mb <= 600:
        default_target = str(int(total_size_mb))  # Don't compress
    elif total_size_mb <= 1500:
        default_target = "500"
    elif total_size_mb <= 2500:
        default_target = "1024"
    elif total_size_mb <= 3500:
        default_target = "1500"
    elif total_size_mb <= 4500:
        default_target = "2048"
    elif total_size_mb <= 5500:
        default_target = "2500"
    elif total_size_mb <= 6500:
        default_target = "3072"
    elif total_size_mb <= 7500:
        default_target = "3500"
    elif total_size_mb <= 8500:
        default_target = "4096"
    elif total_size_mb <= 9500:
        default_target = "4500"
    else:
        default_target = str(int(total_size_mb * 0.5))  # 50% for very large files

    if total_size_mb >= 1000:
        size_display = f"{total_size_gb:.2f} GB"
    else:
        size_display = f"{total_size_mb:.2f} MB"

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

    # Check if target is larger than original
    if target_size_bytes > total_size_bytes:
        print(f"\n⚠ Error: Target size ({target_size_mb:.2f} MB) is larger than original size ({total_size_mb:.2f} MB).")
        print("This script is only meant for compression (you wouldn't even get any extra quality).")
        print("Please enter a target size smaller than the original.\n")
        sys.exit(1)

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
