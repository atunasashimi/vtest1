#!/bin/bash

# Gemini Video Psychoanalysis - One-Click Railway Deployment
# This script deploys your video analysis service to Railway

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  🧠 Gemini Video Psychoanalysis - Railway Deployment          ║"
echo "║     Powered by Google Gemini 2.5-flash                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if we're in the right directory
if [ ! -f "video.mp4" ]; then
    echo "❌ Error: video.mp4 not found!"
    echo "   Please run this script from /home/claude/"
    exit 1
fi

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "📦 Railway CLI not found. Installing..."
    npm install -g @railway/cli
    if [ $? -eq 0 ]; then
        echo "✅ Railway CLI installed successfully"
    else
        echo "❌ Failed to install Railway CLI"
        echo "   Please install manually: npm install -g @railway/cli"
        exit 1
    fi
else
    echo "✅ Railway CLI is installed"
fi

# Set Railway token
echo ""
echo "🔐 Setting up Railway authentication..."
export RAILWAY_TOKEN="fadbb4ed-7c3a-4307-89cd-f78d40ecda38"

# Login to Railway
echo "🔑 Logging in to Railway..."
railway login --browserless

if [ $? -ne 0 ]; then
    echo "❌ Railway login failed"
    exit 1
fi

# Initialize Railway project
echo ""
echo "🏗️  Initializing Railway project..."
railway init

if [ $? -ne 0 ]; then
    echo "❌ Project initialization failed"
    exit 1
fi

# Set environment variables
echo ""
echo "🔧 Setting environment variables..."
railway variables set GOOGLE_API_KEY=AIzaSyDLzbKMqRXcMyDRN3ypbEG2jubbpe6xIMQ

if [ $? -ne 0 ]; then
    echo "❌ Failed to set environment variables"
    exit 1
fi

# Deploy the application
echo ""
echo "🚀 Deploying to Railway..."
echo "   (This may take 2-3 minutes)"
echo ""
railway up

if [ $? -ne 0 ]; then
    echo "❌ Deployment failed"
    exit 1
fi

# Generate domain
echo ""
echo "🌐 Setting up public domain..."
railway domain

# Get the deployment info
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ✅ DEPLOYMENT SUCCESSFUL!                                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "🎉 Your video psychoanalysis service is now live!"
echo ""
echo "📍 Your service URL will be displayed above"
echo ""
echo "🔗 Endpoints:"
echo "   • Health Check: https://your-url.railway.app/"
echo "   • Analyze Video: https://your-url.railway.app/analyze"
echo ""
echo "💡 Usage:"
echo "   1. Visit the /analyze endpoint in your browser"
echo "   2. Wait 1-2 minutes for the analysis to complete"
echo "   3. View your comprehensive psychoanalytic report"
echo ""
echo "⏱️  Note: First request may take longer (cold start)"
echo ""
echo "📊 To view logs: railway logs"
echo "🔧 To redeploy: railway up"
echo "❌ To delete: railway delete"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
