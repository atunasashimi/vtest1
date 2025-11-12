import os
import time
import google.generativeai as genai
from flask import Flask, jsonify, send_file, request
import requests
import tempfile
import re

app = Flask(__name__)

# Configure Gemini API
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

def download_video(video_url):
    """Download video from URL"""
    
    print(f"Downloading video from URL: {video_url}")
    
    try:
        response = requests.get(video_url, stream=True, timeout=600)
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

def extract_last_timestamp(transcript):
    """Extract the last timestamp from the transcript"""
    # Look for patterns like [MM:SS] or [HH:MM:SS]
    timestamps = re.findall(r'\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]', transcript)
    if timestamps:
        last = timestamps[-1]
        if last[2]:  # HH:MM:SS format
            return int(last[0]) * 3600 + int(last[1]) * 60 + int(last[2])
        else:  # MM:SS format
            return int(last[0]) * 60 + int(last[1])
    return 0

def transcribe_audio_complete(video_file):
    """Get complete transcription using multiple passes if needed"""
    
    print("Starting complete transcription process...")
    
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config={
            "max_output_tokens": 8192,
            "temperature": 0.1,
        }
    )
    
    # First pass - get initial transcription
    initial_prompt = """Provide a COMPLETE word-for-word transcription of ALL audio in this video.

IMPORTANT: Transcribe the ENTIRE video from start to finish. Do not stop early.

Format:
[00:00] - Include timestamp every 30 seconds
Speaker 1: Actual spoken words
Speaker 2: Their response
[00:30] Continue throughout
[01:00] Keep going...

Include:
- Every single word spoken
- All speakers labeled
- [pause], [music], [laughter], [background noise] when relevant
- Continue ALL THE WAY to the end

Start transcription now and continue until the video ends:"""

    print("Pass 1: Getting initial transcription...")
    response1 = model.generate_content([video_file, initial_prompt])
    transcript = response1.text.strip()
    
    last_time = extract_last_timestamp(transcript)
    print(f"Pass 1 complete: {len(transcript)} chars, last timestamp: {last_time}s")
    
    # Additional passes if needed
    max_passes = 3
    for pass_num in range(2, max_passes + 1):
        # Check if we should continue
        if last_time > 0 and last_time < 300:  # Less than 5 minutes might indicate incomplete
            print(f"Pass {pass_num}: Requesting continuation from {last_time}s...")
            
            minutes = last_time // 60
            seconds = last_time % 60
            
            continuation_prompt = f"""The transcription stopped at [{minutes:02d}:{seconds:02d}]. 

Please continue transcribing from [{minutes:02d}:{seconds:02d}] onwards until the VERY END of the video.

Include:
- Start from [{minutes:02d}:{seconds:02d}]
- Continue with all remaining audio
- Maintain same format with timestamps
- Do not repeat what was already transcribed
- Continue until video ends

Continue transcription:"""
            
            try:
                response = model.generate_content([video_file, continuation_prompt])
                continuation = response.text.strip()
                
                if len(continuation) > 100:
                    print(f"Pass {pass_num}: Got {len(continuation)} additional chars")
                    transcript += f"\n\n{continuation}"
                    
                    new_last_time = extract_last_timestamp(continuation)
                    if new_last_time > last_time:
                        last_time = new_last_time
                        print(f"Updated last timestamp: {last_time}s")
                    else:
                        print("No progress in timestamp, stopping additional passes")
                        break
                else:
                    print("Continuation seems complete")
                    break
                    
            except Exception as e:
                print(f"Error in pass {pass_num}: {e}")
                break
        else:
            break
    
    print(f"Transcription complete: {len(transcript)} total characters")
    return transcript

def analyze_video_content(video_file, transcript):
    """Analyze the video using Gemini 2.5-flash with transcript context"""
    
    print("Generating psychoanalytic analysis...")
    
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config={
            "max_output_tokens": 8192,
            "temperature": 0.7,
        }
    )
    
    # Truncate transcript if too long for analysis (keep full version for user)
    transcript_for_analysis = transcript
    if len(transcript) > 30000:
        print(f"Transcript is very long ({len(transcript)} chars), using summary for analysis...")
        # Keep beginning and end, summarize middle
        transcript_for_analysis = transcript[:15000] + "\n\n[... middle section continues ...]\n\n" + transcript[-15000:]
    
    prompt = f"""You have been provided with a video and its audio transcript below.

AUDIO TRANSCRIPT:
{transcript_for_analysis}

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

    response = model.generate_content([video_file, prompt])
    
    analysis = response.text
    print(f"Analysis complete: {len(analysis)} characters")
    
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
        
        # Get complete transcription
        transcript = transcribe_audio_complete(video_file)
        
        # Analyze video with transcript
        analysis = analyze_video_content(video_file, transcript)
        
        # Clean up
        genai.delete_file(video_file.name)
        print("Processing complete")
        
        return {
            "transcript": transcript,
            "transcript_length": len(transcript),
            "analysis": analysis,
            "analysis_length": len(analysis)
        }
    
    finally:
        # Clean up downloaded file
        if os.path.exists(video_path):
            os.remove(video_path)
            print(f"Cleaned up temporary file: {video_path}")

@app.route('/')
def home():
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
        data = request.get_json()
        
        if not data or 'video_url' not in data:
            return jsonify({
                "status": "error",
                "message": "Please provide 'video_url' in the request body"
            }), 400
        
        video_url = data['video_url']
        
        if not video_url.startswith(('http://', 'https://')):
            return jsonify({
                "status": "error",
                "message": "Invalid URL. Must start with http:// or https://"
            }), 400
        
        result = process_video(video_url)
        
        return jsonify({
            "status": "success",
            "video_url": video_url,
            "transcript": result["transcript"],
            "transcript_length": result["transcript_length"],
            "analysis": result["analysis"],
            "analysis_length": result["analysis_length"]
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
