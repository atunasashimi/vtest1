import os
import time
import google.generativeai as genai
from flask import Flask, jsonify, send_file, request
import requests
import tempfile
import subprocess
import json

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
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        for chunk in response.iter_content(chunk_size=8192):
            temp_file.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                percent = (downloaded / total_size) * 100
                if downloaded % (1024 * 1024 * 10) == 0:  # Log every 10MB
                    print(f"Download progress: {percent:.1f}%")
        
        temp_file.close()
        
        print(f"Video downloaded to: {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        print(f"Error downloading video: {e}")
        raise ValueError(f"Could not download video from URL: {video_url}. Error: {str(e)}")

def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe"""
    
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration = float(data['format']['duration'])
            print(f"Video duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
            return duration
        else:
            print("Could not determine video duration, assuming segments needed")
            return None
            
    except Exception as e:
        print(f"Error getting duration: {e}")
        return None

def create_video_segment(video_path, start_time, duration, output_path):
    """Create a video segment using ffmpeg"""
    
    try:
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', str(start_time),
            '-t', str(duration),
            '-c', 'copy',  # Fast copy without re-encoding
            '-y',  # Overwrite output
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"Created segment: {start_time}s-{start_time+duration}s")
            return True
        else:
            print(f"Error creating segment: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error in segment creation: {e}")
        return False

def transcribe_segment(video_file, segment_num, start_time):
    """Transcribe a single video segment"""
    
    print(f"Transcribing segment {segment_num} (starting at {start_time}s)...")
    
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config={
            "max_output_tokens": 8192,
            "temperature": 0.0,
        }
    )
    
    # Format start time for display
    start_minutes = int(start_time // 60)
    start_seconds = int(start_time % 60)
    
    prompt = f"""Transcribe ALL spoken audio in this video segment.

This segment starts at [{start_minutes:02d}:{start_seconds:02d}] in the full video.

Format each line as:
[MM:SS] Speaker: What they said

Include:
- Every word spoken
- Speaker labels (Speaker 1, Speaker 2, etc.)
- [pause] for silences over 2 seconds
- [music], [laughter], [background noise] where relevant

Adjust timestamps to reflect the actual time in the FULL video (starting from [{start_minutes:02d}:{start_seconds:02d}]).

Transcription:"""

    try:
        response = model.generate_content(
            [video_file, prompt],
            request_options={"timeout": 300}
        )
        
        transcript = response.text.strip()
        print(f"Segment {segment_num} transcribed: {len(transcript)} chars")
        
        return transcript
        
    except Exception as e:
        print(f"Error transcribing segment {segment_num}: {e}")
        return f"[Error transcribing segment starting at {start_minutes:02d}:{start_seconds:02d}]"

def transcribe_video_in_segments(video_path, segment_duration=240):
    """
    Transcribe video by breaking it into segments
    
    Args:
        video_path: Path to the video file
        segment_duration: Duration of each segment in seconds (default 4 minutes = 240s)
    """
    
    print(f"Starting segmented transcription (segments of {segment_duration}s)...")
    
    # Get video duration
    total_duration = get_video_duration(video_path)
    
    if not total_duration:
        # If we can't get duration, process as single video
        print("Processing as single video...")
        video_file = genai.upload_file(path=video_path, display_name="full_video")
        
        while video_file.state.name == "PROCESSING":
            time.sleep(5)
            video_file = genai.get_file(video_file.name)
        
        transcript = transcribe_segment(video_file, 1, 0)
        genai.delete_file(video_file.name)
        
        return transcript
    
    # Calculate number of segments
    num_segments = int((total_duration // segment_duration) + (1 if total_duration % segment_duration > 0 else 0))
    print(f"Video will be split into {num_segments} segments")
    
    all_transcripts = []
    segment_files = []
    
    try:
        # Create and transcribe each segment
        for i in range(num_segments):
            start_time = i * segment_duration
            duration = min(segment_duration, total_duration - start_time)
            
            if duration <= 0:
                break
            
            # Create segment file
            segment_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
            segment_files.append(segment_path)
            
            print(f"\nSegment {i+1}/{num_segments}: {start_time}s - {start_time+duration}s")
            
            if create_video_segment(video_path, start_time, duration, segment_path):
                # Upload segment to Gemini
                print(f"Uploading segment {i+1}...")
                video_file = genai.upload_file(path=segment_path, display_name=f"segment_{i+1}")
                
                # Wait for processing
                while video_file.state.name == "PROCESSING":
                    time.sleep(3)
                    video_file = genai.get_file(video_file.name)
                
                if video_file.state.name == "FAILED":
                    print(f"Segment {i+1} processing failed")
                    all_transcripts.append(f"[Segment {i+1} processing failed]")
                else:
                    # Transcribe segment
                    transcript = transcribe_segment(video_file, i+1, start_time)
                    all_transcripts.append(transcript)
                
                # Cleanup Gemini file
                genai.delete_file(video_file.name)
            else:
                all_transcripts.append(f"[Segment {i+1} creation failed]")
        
        # Combine all transcripts
        combined_transcript = "\n\n".join(all_transcripts)
        
        print(f"\nTranscription complete: {len(combined_transcript)} total characters")
        print(f"Processed {num_segments} segments")
        
        return combined_transcript
        
    finally:
        # Cleanup segment files
        for segment_file in segment_files:
            try:
                if os.path.exists(segment_file):
                    os.remove(segment_file)
            except:
                pass

def analyze_video_content(video_path, transcript):
    """Analyze the complete video with full transcript"""
    
    print("Generating psychoanalytic analysis...")
    
    # Upload full video for analysis
    print("Uploading full video for analysis...")
    video_file = genai.upload_file(path=video_path, display_name="full_video_analysis")
    
    while video_file.state.name == "PROCESSING":
        print("Processing video for analysis...")
        time.sleep(5)
        video_file = genai.get_file(video_file.name)
    
    if video_file.state.name == "FAILED":
        raise ValueError("Video processing failed for analysis")
    
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config={
            "max_output_tokens": 8192,
            "temperature": 0.7,
        }
    )
    
    # For very long transcripts, provide a summary in the analysis prompt
    if len(transcript) > 30000:
        print(f"Transcript is long ({len(transcript)} chars), using strategic excerpts for analysis...")
        # Use beginning, middle, and end
        third = len(transcript) // 3
        transcript_for_prompt = (
            transcript[:third] + 
            "\n\n[...middle section continues...]\n\n" + 
            transcript[third:2*third][:5000] +
            "\n\n[...continues...]\n\n" +
            transcript[-third:]
        )
    else:
        transcript_for_prompt = transcript
    
    prompt = f"""You have been provided with a video and its complete audio transcript below.

COMPLETE AUDIO TRANSCRIPT:
{transcript_for_prompt}

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

    try:
        response = model.generate_content([video_file, prompt])
        analysis = response.text
        print(f"Analysis complete: {len(analysis)} characters")
        
        # Cleanup
        genai.delete_file(video_file.name)
        
        return analysis
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        genai.delete_file(video_file.name)
        raise

def process_video(video_url):
    """Main processing function with segmented transcription"""
    
    print("Starting video processing with segmented transcription...")
    
    video_path = download_video(video_url)
    
    try:
        # Get duration to decide segment size
        duration = get_video_duration(video_path)
        
        # Adjust segment duration based on video length
        if duration:
            if duration > 3600:  # > 1 hour
                segment_duration = 300  # 5 minutes
            elif duration > 1800:  # > 30 minutes
                segment_duration = 240  # 4 minutes
            else:
                segment_duration = 300  # 5 minutes for shorter videos
        else:
            segment_duration = 240  # Default 4 minutes
        
        print(f"Using segment duration: {segment_duration}s ({segment_duration/60:.1f} minutes)")
        
        # Transcribe in segments
        transcript = transcribe_video_in_segments(video_path, segment_duration)
        
        # Analyze with full video
        analysis = analyze_video_content(video_path, transcript)
        
        print("Processing complete!")
        
        return {
            "transcript": transcript,
            "transcript_length": len(transcript),
            "analysis": analysis,
            "analysis_length": len(analysis),
            "video_duration": duration
        }
    
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
            print(f"Cleaned up: {video_path}")

@app.route('/')
def home():
    try:
        return send_file('index.html')
    except:
        return jsonify({
            "status": "ready",
            "message": "Video psychoanalysis service with segmented transcription",
            "capabilities": {
                "max_video_length": "60+ minutes",
                "transcription": "Segmented for complete coverage",
                "analysis": "Full video psychoanalytic analysis"
            }
        })

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        
        if not data or 'video_url' not in data:
            return jsonify({
                "status": "error",
                "message": "Provide 'video_url' in request body"
            }), 400
        
        video_url = data['video_url']
        
        if not video_url.startswith(('http://', 'https://')):
            return jsonify({
                "status": "error",
                "message": "URL must start with http:// or https://"
            }), 400
        
        result = process_video(video_url)
        
        return jsonify({
            "status": "success",
            "video_url": video_url,
            "transcript": result["transcript"],
            "transcript_length": result["transcript_length"],
            "analysis": result["analysis"],
            "analysis_length": result["analysis_length"],
            "video_duration_seconds": result.get("video_duration"),
            "note": "Complete transcription using segmented approach"
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
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
        "gemini_api_configured": bool(GOOGLE_API_KEY),
        "ffmpeg_available": os.system('which ffmpeg > /dev/null 2>&1') == 0
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
