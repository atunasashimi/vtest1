# Gemini Video Psychoanalysis

Web application for analyzing videos using Google's Gemini 2.5-flash AI model.

## Features

- 🎤 Complete audio transcription (supports 60+ minute videos)
- 🧠 8-dimensional psychoanalytic analysis
- ⏰ Continuous timestamps across video segments
- 🔗 Dynamic URL input for any publicly accessible video

## Version

Current: v1.2.1

## Tech Stack

- Backend: Python Flask + Gemini API
- Frontend: HTML/CSS/JavaScript
- Video Processing: ffmpeg
- Deployment: Railway

## Setup

### Prerequisites

- Python 3.11+
- Google AI Studio API key
- Railway account (for deployment)
- ffmpeg installed

### Environment Variables

Required in Railway dashboard:
```
GOOGLE_API_KEY=your_key_here
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable
export GOOGLE_API_KEY=your_key_here

# Run locally
python gemini_video_analyzer.py
```

### Deployment

Deploy to Railway:
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway up
```

## File Structure
```
├── gemini_video_analyzer.py  # Main application
├── index.html                 # Web interface
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container config
├── railway.json              # Railway deployment config
├── VERSION.md                # Version history
└── README.md                 # This file
```

## Usage

1. Visit the deployed app
2. Enter a publicly accessible video URL (MP4)
3. Click "Analyze"
4. Wait 5-20 minutes (depending on video length)
5. View transcript and analysis

## Supported Video Hosts

- Google Cloud Storage
- Dropbox (with `dl=1` parameter)
- Any direct MP4 URL

## API Endpoints

- `GET /` - Web interface
- `POST /analyze` - Analyze video (body: `{"video_url": "..."}`)
- `GET /health` - Health check

## License

[Your choice - MIT, Apache, etc.]
```

---

## 🔄 **Impact on Deployment Process:**

### **✅ NO IMPACT - Everything Still Works!**

**Before (Private Repo):**
```
1. Push to GitHub (private)
2. Railway deploys automatically
3. Uses environment variables from Railway dashboard
```

**After (Public Repo):**
```
1. Push to GitHub (public)  ← Only this changes
2. Railway deploys automatically  ← Same
3. Uses environment variables from Railway dashboard  ← Same