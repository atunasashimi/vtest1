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
            response = requests.get(VIDEO_URL, stream=True, timeout=300)
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

def transcribe_audio(video_file):
    """Transcribe audio from the video"""
    
    print("Transcribing audio...")
    
    # Create the model
    model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp")
    
    # Transcription prompt
    transcript_prompt = """Please provide a complete, accurate transcription of all spoken audio in this video.

Format:
- Include all dialogue and speech
- Use speaker labels if multiple speakers (e.g., "Speaker 1:", "Speaker 2:")
- Include [pause], [music], [sound effects] for non-speech audio where relevant
- Preserve natural speech patterns including fillers (um, uh, etc.)
- Use timestamps for longer videos if helpful

Transcription:"""

    # Generate transcript
    response = model.generate_content([video_file, transcript_prompt])
    
    transcript = response.text.strip()
    print("Transcription complete")
    
    return transcript

def analyze_video(video_file, transcript):
    """Analyze the video using Gemini 2.5-flash with transcript context"""
    
    print("Generating psychoanalytic analysis...")
    
    # Create the model
    model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp")
    
    # Psychoanalytic prompt with transcript
    prompt = f"""You have been provided with a video and its audio transcript below.

AUDIO TRANSCRIPT:
{transcript}

---

Please provide a deep psychoanalytic analysis of this video, incorporating insights from both the visual content and the spoken words. Consider:

1. **Symbolic Content & Unconscious Manifestations**: What symbolic elements, metaphors, or recurring patterns appear in both visual and verbal content? What might they represent from a psychoanalytic perspective (Freudian, Jungian, Lacanian, etc.)?

2. **Emotional Undertones & Affect**: What emotions, moods, or affective states are present in speech patterns, tone, and visual content? What defense mechanisms might be at play (repression, projection, displacement, etc.)?

3. **Interpersonal Dynamics & Object Relations**: If people are present, analyze the relational dynamics through their words and interactions. What attachment styles, transferences, or interpersonal patterns emerge?

4. **Narrative Structure & Dream-Logic**: How do the spoken narrative and visual narrative interact? Are there dream-like qualities, condensation, or displacement of meaning?

5. **The Gaze & Subject Position**: How does the camera position the viewer? What does the verbal content reveal about perspective and subjectivity?

6. **Temporal & Spatial Dimensions**: How are time and space used verbally and visually? What might this reveal about the psyche's relationship to reality, memory, or fantasy?

7. **Repression & the Return of the Repressed**: Are there elements in speech or visuals that seem suppressed or that emerge unexpectedly? What might be "unsaid" or unconscious despite being spoken?

8. **Cultural & Archetypal Resonances**: Are there universal archetypes or culturally specific symbols in language or imagery that connect to collective unconscious themes?

Please provide a comprehensive, nuanced analysis that draws on psychoanalytic theory while remaining grounded in what is actually observable in the video and audible in the transcript."""

    # Generate analysis
    response = model.generate_content([video_file, prompt])
    
    analysis = response.text
    print("Analysis complete")
    
    return analysis

def process_video():
    """Main function to process video: upload, transcribe, and analyze"""
    
    print("Starting video processing...")
    
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
    
    # Transcribe audio
    transcript = transcribe_audio(video_file)
    
    # Analyze video with transcript
    analysis = analyze_video(video_file, transcript)
    
    # Clean up
    genai.delete_file(video_file.name)
    print("Processing complete")
    
    return {
        "transcript": transcript,
        "analysis": analysis
    }

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
        result = process_video()
        return jsonify({
            "status": "success",
            "transcript": result["transcript"],
            "analysis": result["analysis"]
        })
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
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
