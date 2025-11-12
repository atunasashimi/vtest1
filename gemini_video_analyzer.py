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

def download_video(video_url):
    """Download video from URL"""
    
    print(f"Downloading video from URL: {video_url}")
    
    try:
        response = requests.get(video_url, stream=True, timeout=300)
        response.raise_for_status()
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        
        # Download with progress
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                percent = (downloaded / total_size) * 100
                print(f"Download progress: {percent:.1f}%")
        
        temp_file.close()
        
        print(f"Video downloaded to: {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        print(f"Error downloading video: {e}")
        raise ValueError(f"Could not download video from URL: {video_url}. Error: {str(e)}")

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

def analyze_video_content(video_file, transcript):
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

def process_video(video_url):
    """Main function to process video: download, upload, transcribe, and analyze"""
    
    print("Starting video processing...")
    
    # Download video from URL
    video_path = download_video(video_url)
    
    try:
        # Upload the video file to Gemini
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
        analysis = analyze_video_content(video_file, transcript)
        
        # Clean up
        genai.delete_file(video_file.name)
        print("Processing complete")
        
        return {
            "transcript": transcript,
            "analysis": analysis
        }
    
    finally:
        # Clean up downloaded file
        if os.path.exists(video_path):
            os.remove(video_path)
            print(f"Cleaned up temporary file: {video_path}")

@app.route('/')
def home():
    # Serve the HTML interface
    try:
        return send_file('index.html')
    except:
        return jsonify({
            "status": "ready",
            "message": "Video psychoanalysis service is running",
            "endpoints": {
                "analyze": "POST /analyze with {\"video_url\": \"...\"}",
                "health": "/health"
            }
        })

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Get video URL from request
        data = request.get_json()
        
        if not data or 'video_url' not in data:
            return jsonify({
                "status": "error",
                "message": "Please provide 'video_url' in the request body"
            }), 400
        
        video_url = data['video_url']
        
        # Validate URL
        if not video_url.startswith(('http://', 'https://')):
            return jsonify({
                "status": "error",
                "message": "Invalid URL. Must start with http:// or https://"
            }), 400
        
        # Process video
        result = process_video(video_url)
        
        return jsonify({
            "status": "success",
            "video_url": video_url,
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
        "gemini_api_configured": bool(GOOGLE_API_KEY)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
