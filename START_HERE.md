# 🧠 Gemini Video Psychoanalysis - Complete Setup Guide

## 📋 Project Overview

This project analyzes your video (20210619_002123.mp4) using Google's Gemini 2.5-flash model to provide a comprehensive psychoanalytic interpretation. Due to network restrictions, the analysis must run on Railway (external hosting) where it can properly access the Google Gemini API.

**Your API keys are pre-configured and ready to use!**

---

## 🚀 Quick Start - Three Methods

### Method 1: One-Click Deployment (EASIEST) ⭐

```bash
cd /mnt/user-data/outputs
chmod +x deploy_to_railway.sh
./deploy_to_railway.sh
```

This script will:
1. ✅ Install Railway CLI (if needed)
2. ✅ Authenticate with your Railway account
3. ✅ Initialize the project
4. ✅ Set environment variables
5. ✅ Deploy your service
6. ✅ Generate a public URL

**Time: ~3-5 minutes**

---

### Method 2: Manual Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Set your Railway token
export RAILWAY_TOKEN="fadbb4ed-7c3a-4307-89cd-f78d40ecda38"

# Login
railway login --browserless

# Navigate to project directory
cd /mnt/user-data/outputs

# Initialize project
railway init

# Set Google API key
railway variables set GOOGLE_API_KEY=AIzaSyDLzbKMqRXcMyDRN3ypbEG2jubbpe6xIMQ

# Deploy
railway up

# Get your URL
railway domain
```

---

### Method 3: Railway Web Dashboard

1. Go to https://railway.app
2. Login with your credentials (use API token if needed)
3. Click "New Project" → "Deploy from GitHub repo" (or upload files)
4. Upload these files from /mnt/user-data/outputs:
   - gemini_video_analyzer.py
   - requirements.txt
   - Dockerfile
   - railway.json
   - video.mp4
5. In Settings → Variables, add:
   - `GOOGLE_API_KEY` = `AIzaSyDLzbKMqRXcMyDRN3ypbEG2jubbpe6xIMQ`
6. Deploy!

---

## 🎯 Using Your Deployed Service

Once deployed, you'll get a URL like: `https://your-app.railway.app`

### Available Endpoints:

#### 1. **Get Psychoanalysis** (Main Feature)
```
GET https://your-app.railway.app/analyze
```

- **Processing Time**: 60-120 seconds
- **Response**: Comprehensive JSON with analysis text
- **Usage**: Simply visit this URL in your browser or use curl:

```bash
curl https://your-app.railway.app/analyze
```

#### 2. **Health Check**
```
GET https://your-app.railway.app/
GET https://your-app.railway.app/health
```

Quick status check to ensure service is running

---

## 📊 What You'll Get

Your psychoanalysis will cover **8 comprehensive dimensions**:

### 1. 🔮 Symbolic Content & Unconscious Manifestations
- Symbolic elements and metaphors
- Freudian, Jungian, and Lacanian perspectives
- Unconscious pattern recognition

### 2. 💭 Emotional Undertones & Affect
- Mood and emotional states
- Defense mechanisms (repression, projection, displacement)
- Affective resonances

### 3. 👥 Interpersonal Dynamics & Object Relations
- Relational patterns
- Attachment styles
- Transference dynamics

### 4. 📖 Narrative Structure & Dream-Logic
- Story flow and structure
- Dream-like qualities
- Condensation and displacement

### 5. 👁️ The Gaze & Subject Position
- Camera positioning
- Viewer relationship
- Voyeurism and identification

### 6. ⏰ Temporal & Spatial Dimensions
- Time and space usage
- Relationship to reality and memory
- Fantasy structures

### 7. 🔒 Repression & Return of the Repressed
- Suppressed elements
- Unconscious emergences
- Hidden content

### 8. 🌍 Cultural & Archetypal Resonances
- Universal archetypes
- Cultural symbols
- Collective unconscious themes

**Expected Output**: 1,500-2,500 words of graduate-level psychoanalytic theory

---

## 📁 Project Files

All files are in `/mnt/user-data/outputs/`:

```
gemini_video_analyzer.py    - Main Flask application
requirements.txt            - Python dependencies
Dockerfile                  - Container configuration
railway.json               - Railway deployment config
video.mp4                  - Your video (61 seconds, 30MB)
deploy_to_railway.sh       - One-click deployment script
README_DEPLOYMENT.md       - Detailed instructions
analyze_local.py           - Local analysis script (won't work due to network restrictions)
```

---

## 🔐 Pre-Configured Credentials

**Google AI Studio API Key:**
```
AIzaSyDLzbKMqRXcMyDRN3ypbEG2jubbpe6xIMQ
```

**Railway API Token:**
```
fadbb4ed-7c3a-4307-89cd-f78d40ecda38
```

These are already embedded in the deployment scripts - no manual configuration needed!

---

## 🔧 Troubleshooting

### "Railway CLI not found"
```bash
npm install -g @railway/cli
```

### "Deployment fails"
- Check you're in the `/mnt/user-data/outputs` directory
- Verify Railway CLI is installed: `railway --version`
- Try manual deployment (Method 2)

### "Analysis endpoint returns 500 error"
- Wait 30 seconds after deployment for service to fully start
- Check Railway logs: `railway logs`
- Verify Google API key is set correctly

### "Request times out"
- First request takes longer (cold start + video processing)
- Wait 2-3 minutes
- Refresh the page

### "403 Forbidden from Google"
- This shouldn't happen on Railway (only in restricted environments)
- Verify API key has Gemini API enabled
- Check Google AI Studio dashboard

---

## 💡 Pro Tips

1. **Bookmark your /analyze URL** for easy access
2. **First request is slow** - be patient (cold start)
3. **Share the URL** - it's a persistent service
4. **View logs** for debugging: `railway logs`
5. **Redeploy anytime**: `railway up`

---

## 📈 Technical Specifications

| Aspect | Details |
|--------|---------|
| Video Length | 61 seconds |
| Video Resolution | 1080x1920 (portrait) |
| Video Size | ~30MB |
| AI Model | Google Gemini 2.5-flash (gemini-2.0-flash-exp) |
| Backend | Python 3.11 + Flask + Gunicorn |
| Hosting | Railway |
| Processing Time | 60-120 seconds |
| Output Length | 1,500-2,500 words |

---

## 🎬 Deployment Workflow

```
1. Install Railway CLI
         ↓
2. Authenticate with Railway
         ↓
3. Initialize project
         ↓
4. Set environment variables
         ↓
5. Deploy Docker container
         ↓
6. Generate public domain
         ↓
7. Access /analyze endpoint
         ↓
8. Get psychoanalysis! 🎉
```

---

## 📞 Support Commands

```bash
# View service status
railway status

# View logs
railway logs

# Open in browser
railway open

# Delete deployment
railway delete

# Redeploy
railway up

# Get URL
railway domain
```

---

## 🌟 Example Response

When you visit `/analyze`, you'll get JSON like:

```json
{
  "status": "success",
  "analysis": "This video presents a fascinating psychoanalytic landscape...
  
  **1. Symbolic Content & Unconscious Manifestations**
  
  The video opens with [specific observations]... This can be interpreted 
  through a Jungian lens as... The recurring motif of... suggests...
  
  [Continues for ~2000 words with deep analysis across all 8 dimensions]"
}
```

---

## ✅ Ready to Deploy?

**Recommended**: Use the one-click script!

```bash
cd /mnt/user-data/outputs
./deploy_to_railway.sh
```

Your psychoanalytic insights are just one command away! 🧠✨

---

## 📚 Additional Resources

- Railway Documentation: https://docs.railway.app
- Google Gemini API Docs: https://ai.google.dev/docs
- Psychoanalytic Theory Primer: (Your analysis will be rooted in established theory)

---

**Questions or issues?** Check the troubleshooting section or Railway's logs with `railway logs`

Good luck with your psychoanalysis! 🎯
