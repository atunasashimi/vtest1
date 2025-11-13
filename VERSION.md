# Version History

## Semantic Versioning Strategy

Format: `MAJOR.MINOR.PATCH`

- **MAJOR** (X.0.0): Breaking changes or complete rewrites
- **MINOR** (1.X.0): New features, processing changes (resets PATCH to 0)
- **PATCH** (1.0.X): Visual/UI changes, bug fixes, documentation

---

## Version History

### v1.3.0 (Current)
**Type**: MINOR - Processing & Analysis Change
**Date**: 2024

**Changes**:
- **Simplified psychoanalytic language**: Analysis now written in accessible, conversational style for emotionally intelligent adults
- **New Video Context section**: Added separate analysis for setting, mood, number of people, and video purpose
- **Dual analysis approach**: Split into two separate AI calls:
  1. Context analysis (observational, descriptive)
  2. Psychological analysis (insights, patterns, meaning)
- **Updated prompts**: Rewritten to produce clear, sophisticated prose without heavy jargon
- **New UI section**: Added "Video Context" display with green styling
- **Enhanced copy functionality**: New "Copy Context" and "Copy All" buttons
- **Progress updates**: Changed from 4 to 5 steps to reflect dual analysis

**Files Changed**:
- `gemini_video_analyzer.py` - Added `get_video_context()`, rewrote `analyze_video_content()`, updated `process_video()`
- `index.html` - Added context section, updated progress steps, new copy buttons

**User Impact**:
- More readable, relatable analysis suitable for general audiences
- Better understanding of video's basic context before diving into psychology
- Clearer separation between what's observed vs. what's interpreted

---

### v1.2.1
**Type**: PATCH - Visual Changes
**Date**: 2024

**Changes**:
- Added semantic version number to page title and subtitle
- Cleaned up interface by removing:
  - "Analysis Includes" section
  - "Analysis Dimensions" grid
  - "What to Expect" section
- Added version to backend `/health` endpoint
- Cleaner, more minimal interface

**Files Changed**:
- `index.html` - Visual cleanup + version display
- `gemini_video_analyzer.py` - Added VERSION constant

---

### v1.2.0
**Type**: MINOR - Processing Change
**Date**: 2024

**Changes**:
- Fixed timestamp continuity across segments
- Timestamps now flow continuously (0:00 → 4:00 → 8:00)
- Added fallback post-processing to adjust timestamps
- Enhanced prompts to emphasize timestamp continuation

**Files Changed**:
- `gemini_video_analyzer.py` - Updated `transcribe_segment()` and added `adjust_timestamps()`

---

### v1.1.0
**Type**: MINOR - Processing Change
**Date**: 2024

**Changes**:
- Added segmented transcription for long videos
- Supports 60+ minute videos
- Uses ffmpeg to split videos into 4-5 minute segments
- Each segment transcribed separately
- Complete transcripts without token limits

**Files Changed**:
- `gemini_video_analyzer.py` - Complete rewrite with segmentation
- `Dockerfile` - Added ffmpeg installation
- `railway.json` - Increased timeout to 600 seconds

---

### v1.0.0
**Type**: MAJOR - Initial Release
**Date**: 2024

**Changes**:
- Initial video psychoanalysis system
- Dynamic URL input for videos
- Audio transcription via Gemini API
- 8-dimensional psychoanalytic analysis
- Freudian, Jungian, and Lacanian perspectives
- Google Cloud Storage integration
- Railway deployment

**Features**:
- Video URL input field
- Complete audio transcription
- Psychoanalytic analysis
- Copy to clipboard functionality
- Real-time progress indicators

---

## How to Update Version

### For Visual/UI Changes (PATCH):
```python
# In gemini_video_analyzer.py
VERSION = "1.3.1"  # Increment PATCH

# In index.html title and subtitle
<title>Gemini Video Psychoanalysis v1.3.1</title>
<span>• v1.3.1</span>
```

### For Processing Changes (MINOR):
```python
# In gemini_video_analyzer.py
VERSION = "1.4.0"  # Increment MINOR, reset PATCH to 0

# In index.html
<title>Gemini Video Psychoanalysis v1.4.0</title>
<span>• v1.4.0</span>
```

### For Breaking Changes (MAJOR):
```python
# In gemini_video_analyzer.py
VERSION = "2.0.0"  # Increment MAJOR, reset MINOR and PATCH to 0

# In index.html
<title>Gemini Video Psychoanalysis v2.0.0</title>
<span>• v2.0.0</span>
```

---

## Deployment Checklist

When releasing a new version:

1. ✅ Update `VERSION` constant in `gemini_video_analyzer.py`
2. ✅ Update version in `index.html` (title + subtitle)
3. ✅ Update this VERSION.md file with changes
4. ✅ Commit with message: `Release v1.X.X: Description`
5. ✅ Push to GitHub
6. ✅ Verify deployment on Railway
7. ✅ Test `/health` endpoint shows correct version
8. ✅ Verify UI displays correct version number

---

## Quick Reference

| Version | Type | Description |
|---------|------|-------------|
| 1.3.0 | MINOR | Simplified analysis + video context |
| 1.2.1 | PATCH | Clean UI + version display |
| 1.2.0 | MINOR | Fix timestamp continuity |
| 1.1.0 | MINOR | Segmented transcription |
| 1.0.0 | MAJOR | Initial release |

---

## Current Version

**v1.3.0** - Accessible psychological insights with video context analysis
