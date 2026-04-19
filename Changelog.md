## 2026-04-19
- Housekeeping changes to the terminal output
- Changes the default target sizes shown in the pop-up to match the compression guide, so the user will most likely just have to confirm. Everything larger than 9.5GB will still default to 50% of the original size
- Fix edge case where total size "ceiling" is too low causing the script to run indefinitely
---
## 2026-04-18
- Compression is now dynamic and uses a multi-pass system - a lot less hardcoding involved
- Compressed files *should* be within 50MB of the target size, not exceeding the target size
