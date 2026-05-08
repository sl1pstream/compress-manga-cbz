## 2026-05-08
- Fixed logic error with stagnation
- Added option to retry compression post-stagnation using different raitio, including some randomization so no two second (third, fourth, etc) attempts for the same set of cbz files will only yield a single result. This further decreases the chance of the script quitting due to stagnation where it should should hit the target size/window in theory
- Fixed lgoic error with randomization
- Script now compresses multiple .cbz files at once. Speed increase from this depends on CPU

\* _This is probably not efficient, but it should effectively solve this issue. If I change how this part of the script works, it's likely because I found a faster way_

---
## 2026-05-07
- Script no longer allows user to enter a target size larger than the original total size. No idea why someone would even think this is a good idea, but now you can't
---
## 2026-04-19
- Housekeeping changes to the terminal output
- Changes the default target sizes shown in the pop-up to match the compression guide, so the user will most likely just have to confirm. Everything larger than 9.5GB will still default to 50% of the original size
- Fix edge case where total size "ceiling" is too low causing the script to run indefinitely
---
## 2026-04-18
- Compression is now dynamic and uses a multi-pass system - a lot less hardcoding involved
- Compressed files *should* be within 50MB of the target size, not exceeding the target size
