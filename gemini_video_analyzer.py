import os
import time
import google.generativeai as genai
from flask import Flask, jsonify, send_file, request
import requests
import tempfile

app = Flask(__name__)

# Configure Gemini API
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

# Video can be local file or URL
VIDEO_PATH = os.environ.get('VIDEO_PATH', '/app/video.mp4')
VIDEO_URL = os.environ.get('VIDEO_URL', '')

def get_video_file():
    """Get video file path, downloading from URL if necessary"""
    
    # If local file exists, use it
    if os.path.exists(VIDEO_PATH):
        print(f"Using local video file: {VIDEO_PATH}")
        return VIDEO_PATH
    
    # If VIDEO_URL is provided, download it
    if VIDEO_URL:
        print(f"Downloading video from URL: {VIDEO_URL}")
        try:
            response = requests.get(VIDEO_URL, stream=True)
            response.raise_for_status()
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            temp_file.close()
            
            print(f"Video downloaded to: {temp_file.name}")
            return temp_file.name
        except Exception as e:
            print(f"Error downloading video: {e}")
            raise ValueError(f"Could not download video from URL: {VIDEO_URL}")
    
    # If no video available
    raise ValueError("No video file found. Set VIDEO_PATH or VIDEO_URL environment variable.")

def analyze_video():
    """Upload and analyze the video using Gemini 2.5-flash"""
    
    print("Starting video analysis...")
    
    # Get video file
    video_path = get_video_file()
    
    # Upload the video file
    print("Uploading video to Gemini...")
    video_file = genai.upload_file(path=video_path, display_name="psychoanalysis_video")
    
    print(f"Video uploaded: {video_file.uri}")
    
    # Wait for video processing
    while video_file.state.name == "PROCESSING":
        print("Waiting for video processing...")
        time.sleep(5)
        video_file = genai.get_file(video_file.name)
    
    if video_file.state.name == "FAILED":
        raise ValueError("Video processing failed")
    
    print("Video processed successfully")
    
    # Create the model
    model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp")
    
    # Psychoanalytic prompt
    prompt = """Please provide a deep psychoanalytic analysis of this video. Consider:

1. **Symbolic Content & Unconscious Manifestations**: What symbolic elements, metaphors, or recurring patterns appear? What might they represent from a psychoanalytic perspective (Freudian, Jungian, Lacanian, etc.)?

2. **Emotional Undertones & Affect**: What emotions, moods, or affective states are present? What defense mechanisms might be at play (repression, projection, displacement, etc.)?

3. **Interpersonal Dynamics & Object Relations**: If people are present, analyze the relational dynamics. What attachment styles, transferences, or interpersonal patterns emerge?

4. **Narrative Structure & Dream-Logic**: Does the video follow a narrative? Are there dream-like qualities, condensation, or displacement of meaning?

5. **The Gaze & Subject Position**: How does the camera position the viewer? What does this suggest about voyeurism, identification, or the construction of subjectivity?

6. **Temporal & Spatial Dimensions**: How are time and space used? What might this reveal about the psyche's relationship to reality, memory, or fantasy?

7. **Repression & the Return of the Repressed**: Are there elements that seem suppressed or that emerge unexpectedly? What might be "unsaid" or unconscious?

8. **Cultural & Archetypal Resonances**: Are there universal archetypes or culturally specific symbols that connect to collective unconscious themes?

Please provide a comprehensive, nuanced analysis that draws on psychoanalytic theory while remaining grounded in what is actually observable in the video."""

    # Generate analysis
    print("Generating psychoanalytic analysis...")
    response = model.generate_content([video_file, prompt])
    
    # Clean up
    genai.delete_file(video_file.name)
    print("Analysis complete")
    
    return response.text

@app.route('/')
def home():
    # Try to serve the HTML interface if it exists
    try:
        return send_file('index.html')
    except:
        return jsonify({
            "status": "ready",
            "message": "Video psychoanalysis service is running",
            "endpoints": {
                "analyze": "/analyze",
                "health": "/health"
            },
            "configuration": {
                "video_path": VIDEO_PATH if os.path.exists(VIDEO_PATH) else "Not found",
                "video_url": VIDEO_URL if VIDEO_URL else "Not set"
            }
        })

@app.route('/analyze')
def analyze():
    try:
        analysis = analyze_video()
        return jsonify({
            "status": "success",
            "analysis": analysis
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "video_available": os.path.exists(VIDEO_PATH) or bool(VIDEO_URL)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
