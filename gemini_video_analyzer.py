import os
import time
import google.generativeai as genai
from flask import Flask, jsonify, send_file, request
import requests
import tempfile
import subprocess
import json

app = Flask(__name__)

# Version info
VERSION = "1.4.1"  # Semantic versioning: MAJOR.MINOR.PATCH

# Configure Gemini API
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

def download_video(video_url):
    """Download video or audio file from URL"""
    
    print(f"Downloading media from URL: {video_url}")
    
    try:
        # Detect file extension from URL
        from urllib.parse import urlparse, unquote
        parsed = urlparse(video_url)
        path = unquote(parsed.path)
        
        # Extract extension, default to .mp4 if not found
        _, ext = os.path.splitext(path)
        if not ext or ext.lower() not in ['.mp4', '.mov', '.avi', '.mkv', '.mp3', '.m4a', '.wav', '.aac', '.flac', '.ogg']:
            ext = '.mp4'  # Default to video
        
        print(f"Detected file extension: {ext}")
        
        response = requests.get(video_url, stream=True, timeout=600)
        response.raise_for_status()
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        
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
        
        print(f"Media downloaded to: {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        print(f"Error downloading media: {e}")
        raise ValueError(f"Could not download media from URL: {video_url}. Error: {str(e)}")

def get_mime_type(file_path):
    """Get MIME type from file extension"""
    
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    # MIME type mapping
    mime_types = {
        # Video formats
        '.mp4': 'video/mp4',
        '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska',
        
        # Audio formats
        '.mp3': 'audio/mpeg',
        '.m4a': 'audio/mp4',
        '.wav': 'audio/wav',
        '.aac': 'audio/aac',
        '.flac': 'audio/flac',
        '.ogg': 'audio/ogg',
    }
    
    mime_type = mime_types.get(ext)
    if mime_type:
        print(f"Using MIME type: {mime_type} for {ext}")
        return mime_type
    else:
        # Default to video/mp4 if unknown
        print(f"Unknown extension {ext}, defaulting to video/mp4")
        return 'video/mp4'

def is_audio_only(file_path):
    """Detect if file is audio-only (no video stream)"""
    
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_type',
            '-of', 'json',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            has_video = len(data.get('streams', [])) > 0
            is_audio = not has_video
            print(f"File type: {'audio-only' if is_audio else 'video'}")
            return is_audio
        else:
            # If we can't detect, assume it has video
            return False
            
    except Exception as e:
        print(f"Error detecting media type: {e}")
        return False

def get_video_duration(video_path):
    """Get media duration in seconds using ffprobe"""
    
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
            print(f"Media duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
            return duration
        else:
            print("Could not determine media duration, assuming segments needed")
            return None
            
    except Exception as e:
        print(f"Error getting duration: {e}")
        return None

def create_video_segment(video_path, start_time, duration, output_path):
    """Create a video or audio segment using ffmpeg"""
    
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

def transcribe_segment(video_file, segment_num, start_time, is_audio_only=False):
    """Transcribe a single video or audio segment with continuous timestamps"""
    
    media_type = "audio" if is_audio_only else "video"
    print(f"Transcribing {media_type} segment {segment_num} (starting at {start_time}s)...")
    
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
    
    prompt = f"""Transcribe ALL spoken audio in this {media_type} segment.

CRITICAL: This segment is part of a longer {media_type} and starts at timestamp [{start_minutes:02d}:{start_seconds:02d}].

Your timestamps MUST start at [{start_minutes:02d}:{start_seconds:02d}] and count UP from there.

For example, if this segment starts at [04:00]:
- First line should be [04:00] or [04:05] (not [00:00])
- Second line might be [04:15] (not [00:15])
- Continue counting up: [04:30], [04:45], [05:00], etc.

Format:
[MM:SS] Speaker: dialogue

Transcription starting at [{start_minutes:02d}:{start_seconds:02d}]:"""

    try:
        response = model.generate_content(
            [video_file, prompt],
            request_options={"timeout": 300}
        )
        
        transcript = response.text.strip()
        
        # Verify timestamps look correct (basic check)
        import re
        timestamps = re.findall(r'\[(\d{1,2}):(\d{2})\]', transcript)
        if timestamps:
            first_timestamp = int(timestamps[0][0]) * 60 + int(timestamps[0][1])
            expected_start = start_time
            
            # If timestamps are still starting near 0, post-process them
            if first_timestamp < 60 and expected_start > 60:
                print(f"Warning: Timestamps appear to restart. Adjusting...")
                transcript = adjust_timestamps(transcript, start_time)
        
        print(f"Segment {segment_num} transcribed: {len(transcript)} chars")
        
        return transcript
        
    except Exception as e:
        print(f"Error transcribing segment {segment_num}: {e}")
        return f"[Error transcribing segment starting at {start_minutes:02d}:{start_seconds:02d}]"


def adjust_timestamps(transcript, offset_seconds):
    """Adjust timestamps in transcript by adding offset"""
    
    import re
    
    def replace_timestamp(match):
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        
        # Add offset
        total_seconds = (minutes * 60 + seconds) + offset_seconds
        new_minutes = total_seconds // 60
        new_seconds = total_seconds % 60
        
        return f"[{new_minutes:02d}:{new_seconds:02d}]"
    
    # Replace all timestamps [MM:SS]
    adjusted = re.sub(r'\[(\d{1,2}):(\d{2})\]', replace_timestamp, transcript)
    
    return adjusted

def transcribe_video_in_segments(video_path, segment_duration=240, is_audio=None):
    """
    Transcribe video or audio by breaking it into segments
    
    Args:
        video_path: Path to the media file
        segment_duration: Duration of each segment in seconds (default 4 minutes = 240s)
        is_audio: Optional boolean, if provided skips media type detection
    """
    
    print(f"Starting segmented transcription (segments of {segment_duration}s)...")
    
    # OPTIMIZATION #2: Use provided is_audio flag to avoid re-detection
    if is_audio is None:
        is_audio = is_audio_only(video_path)
    
    # Get file extension for segments
    _, ext = os.path.splitext(video_path)
    
    # Get media duration
    total_duration = get_video_duration(video_path)
    
    if not total_duration:
        # If we can't get duration, process as single file
        print("Processing as single file...")
        mime_type = get_mime_type(video_path)
        video_file = genai.upload_file(
            path=video_path, 
            display_name="full_media",
            mime_type=mime_type
        )
        
        while video_file.state.name == "PROCESSING":
            time.sleep(5)
            video_file = genai.get_file(video_file.name)
        
        transcript = transcribe_segment(video_file, 1, 0, is_audio)
        genai.delete_file(video_file.name)
        
        return transcript
    
    # Calculate number of segments
    num_segments = int((total_duration // segment_duration) + (1 if total_duration % segment_duration > 0 else 0))
    print(f"Media will be split into {num_segments} segments")
    
    all_transcripts = []
    segment_files = []
    
    try:
        # Create and transcribe each segment
        for i in range(num_segments):
            start_time = i * segment_duration
            duration = min(segment_duration, total_duration - start_time)
            
            if duration <= 0:
                break
            
            # Create segment file with proper extension
            segment_path = tempfile.NamedTemporaryFile(delete=False, suffix=ext).name
            segment_files.append(segment_path)
            
            print(f"\nSegment {i+1}/{num_segments}: {start_time}s - {start_time+duration}s")
            
            if create_video_segment(video_path, start_time, duration, segment_path):
                # Upload segment to Gemini with explicit MIME type
                print(f"Uploading segment {i+1}...")
                mime_type = get_mime_type(segment_path)
                video_file = genai.upload_file(
                    path=segment_path, 
                    display_name=f"segment_{i+1}",
                    mime_type=mime_type
                )
                
                # Wait for processing
                while video_file.state.name == "PROCESSING":
                    time.sleep(3)
                    video_file = genai.get_file(video_file.name)
                
                if video_file.state.name == "FAILED":
                    print(f"Segment {i+1} processing failed")
                    all_transcripts.append(f"[Segment {i+1} processing failed]")
                else:
                    # Transcribe segment with audio flag
                    transcript = transcribe_segment(video_file, i+1, start_time, is_audio)
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

def get_video_context(video_file, transcript, is_audio):
    """Extract basic video/audio context: setting, mood, people, purpose
    
    Args:
        video_file: Already uploaded Gemini file object
        transcript: Full transcript text
        is_audio: Boolean indicating if media is audio-only
    """
    
    print("Analyzing media context...")
    
    # OPTIMIZATION #1 & #2: Use provided video_file and is_audio flag
    media_type = "audio" if is_audio else "video"
    
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config={
            "max_output_tokens": 2048,
            "temperature": 0.4,
        }
    )
    
    # For very long transcripts, provide excerpts
    if len(transcript) > 30000:
        third = len(transcript) // 3
        transcript_excerpt = (
            transcript[:third] + 
            "\n\n[...middle section...]\n\n" + 
            transcript[-third:]
        )
    else:
        transcript_excerpt = transcript
    
    # Adjust prompt based on media type
    if is_audio:
        prompt = f"""You are analyzing an audio recording to provide clear, observational context about what's happening.

AUDIO TRANSCRIPT:
{transcript_excerpt}

---

Please describe the following aspects of this audio in clear, straightforward language:

**Setting & Environment:**
Based on the audio and content, where does this appear to take place? What's the acoustic environment like? Are there background sounds or music? What clues suggest the location or context?

**Mood & Atmosphere:**
What's the overall emotional tone? Is it formal or casual? Tense or relaxed? Serious or lighthearted? What creates this feeling?

**People & Presence:**
How many speakers are there? What are their apparent roles or relationships? What can you infer about them from their voices and manner of speaking?

**Purpose & Intent:**
Why does this audio seem to exist? What appears to be its intended goal or message? Is it educational, entertainment, documentation, conversation, or something else?

Write in a natural, conversational style as if describing the audio to someone who hasn't heard it. Be specific and concrete in your observations."""
    else:
        prompt = f"""You are analyzing a video to provide clear, observational context about what's happening.

AUDIO TRANSCRIPT:
{transcript_excerpt}

---

Please describe the following aspects of this video in clear, straightforward language:

**Setting & Environment:**
Where does this appear to take place? What's the physical environment like? Indoor/outdoor? What can you observe about the location?

**Mood & Atmosphere:**
What's the overall emotional tone? Is it formal or casual? Tense or relaxed? Serious or lighthearted? What creates this feeling?

**People & Presence:**
How many people appear in the video? What are their apparent roles or relationships? If no people are visible, note what is shown instead.

**Purpose & Intent:**
Why does this video seem to exist? What appears to be its intended goal or message? Is it educational, entertainment, documentation, communication, or something else?

Write in a natural, conversational style as if describing the video to someone who hasn't seen it. Be specific and concrete in your observations."""

    try:
        response = model.generate_content(
            [video_file, prompt],
            request_options={"timeout": 300}  # 5 minute timeout for context
        )
        context = response.text
        print(f"Context analysis complete: {len(context)} characters")
        
        # OPTIMIZATION #1: Don't delete file here - managed by process_video
        return context
        
    except Exception as e:
        print(f"Error during context analysis: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        # Don't delete file here - will be cleaned up by process_video
        raise

def analyze_video_content(video_file, transcript, is_audio):
    """Generate accessible psychological analysis of the video or audio
    
    Args:
        video_file: Already uploaded Gemini file object
        transcript: Full transcript text
        is_audio: Boolean indicating if media is audio-only
    """
    
    print("Generating psychological analysis...")
    
    # OPTIMIZATION #1 & #2: Use provided video_file and is_audio flag
    media_type = "audio" if is_audio else "video"
    
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config={
            "max_output_tokens": 8192,
            "temperature": 0.7,
        }
    )
    
    # For very long transcripts, provide strategic excerpts
    if len(transcript) > 30000:
        print(f"Transcript is long ({len(transcript)} chars), using strategic excerpts for analysis...")
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
    
    # Adjust prompt based on media type
    if is_audio:
        visual_guidance = "Focus on what you can hear: tone of voice, speech patterns, pauses, background sounds, and emotional qualities in the audio."
        media_article = "an audio"
        audience_type = "listener"
        elements_type = "sounds, metaphors"
        modality = "auditory"
    else:
        visual_guidance = "Look at tone of voice, word choices, visual cues, body language, and the interplay between what's said and what's shown visually."
        media_article = "a video"
        audience_type = "camera/audience"
        elements_type = "images, metaphors"
        modality = "visual and verbal"
    
    prompt = f"""You are a thoughtful psychologist analyzing {media_article}. Your goal is to provide insights that are both sophisticated and accessible--written for a self-aware, emotionally intelligent adult who appreciates nuance but values clarity.

COMPLETE AUDIO TRANSCRIPT:
{transcript_for_prompt}

---

Please provide a psychological analysis that explores:

**1. Emotional Landscape**
What feelings and emotional states come through in this {media_type}? {visual_guidance} What might be happening beneath the surface? Are there tensions between what's said and what's felt?

**2. Patterns of Communication**
How do people in this {media_type} relate to each other (or to the {audience_type})? What communication styles emerge? Are there power dynamics, intimacy, distance, or other relational qualities worth noting?

**3. Symbolic Elements & Meaning**
What {elements_type}, or recurring themes appear? What might they represent beyond their literal meaning? How do {modality} elements work together to create meaning?

**4. Psychological Defenses & Coping**
Are there signs of how people are managing stress, vulnerability, or difficult emotions? This might include humor, deflection, intellectualization, or other protective strategies we all use.

**5. Narrative & Identity**
What story is being told--either explicitly or implicitly? How do the people in this {media_type} seem to see themselves and their situation? What worldview or perspective shapes their experience?

**6. Unconscious Themes**
What goes unsaid but seems important? Are there contradictions, slips, or moments where something unexpected emerges? What patterns might the speakers not be fully aware of?

**7. Cultural & Universal Elements**
Are there cultural references, shared experiences, or archetypal patterns (like the hero's journey, the struggle for belonging, etc.) that give this {media_type} broader resonance?

**8. Overall Psychological Impression**
Stepping back, what's the deeper human experience being expressed or explored here? What makes this psychologically meaningful or noteworthy?

---

**Writing Guidelines:**
- Write in clear, flowing prose--avoid jargon unless you explain it naturally
- Use specific examples from what you observe
- Balance intellectual insight with emotional awareness
- Be respectful and curious, not diagnostic or pathologizing
- Write as if speaking to an insightful friend, not writing a clinical report
- When referencing psychological concepts (like projection or attachment), explain them in context rather than assuming the reader knows the technical meaning

Your analysis should feel like a thoughtful conversation about the human dimensions of this {media_type}."""

    try:
        response = model.generate_content(
            [video_file, prompt],
            request_options={"timeout": 600}  # 10 minute timeout for analysis
        )
        analysis = response.text
        print(f"Psychological analysis complete: {len(analysis)} characters")
        
        # OPTIMIZATION #1: Don't delete file here - managed by process_video
        return analysis
        
    except Exception as e:
        print(f"Error during psychological analysis: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        # Don't delete file here - will be cleaned up by process_video
        raise

def process_video(video_url):
    """Main processing function with segmented transcription and dual analysis"""
    
    import time
    start_time = time.time()
    
    print("Starting media processing with segmented transcription...")
    
    video_path = download_video(video_url)
    
    try:
        # OPTIMIZATION #2: Detect media type ONCE at the start
        is_audio = is_audio_only(video_path)
        media_type = "audio" if is_audio else "video"
        print(f"Media type detected: {media_type}")
        
        # Get duration to decide segment size
        duration = get_video_duration(video_path)
        
        # Adjust segment duration based on media length
        if duration:
            if duration > 3600:  # > 1 hour
                segment_duration = 300  # 5 minutes
            elif duration > 1800:  # > 30 minutes
                segment_duration = 240  # 4 minutes
            else:
                segment_duration = 300  # 5 minutes for shorter media
        else:
            segment_duration = 240  # Default 4 minutes
        
        print(f"Using segment duration: {segment_duration}s ({segment_duration/60:.1f} minutes)")
        
        # Transcribe in segments (pass is_audio to avoid re-detection)
        transcript = transcribe_video_in_segments(video_path, segment_duration, is_audio)
        
        # OPTIMIZATION #1: Upload full video ONCE for both context and analysis
        print(f"Uploading full {media_type} for context and analysis...")
        mime_type = get_mime_type(video_path)
        video_file = genai.upload_file(
            path=video_path, 
            display_name=f"full_{media_type}_analysis",
            mime_type=mime_type
        )
        
        while video_file.state.name == "PROCESSING":
            print(f"Processing {media_type} for Gemini analysis...")
            time.sleep(5)
            video_file = genai.get_file(video_file.name)
        
        if video_file.state.name == "FAILED":
            raise ValueError(f"{media_type.capitalize()} upload failed for analysis")
        
        try:
            # Use the same uploaded file for both analyses (pass is_audio to avoid re-detection)
            context = get_video_context(video_file, transcript, is_audio)
            analysis = analyze_video_content(video_file, transcript, is_audio)
        finally:
            # Clean up uploaded file
            print(f"Cleaning up uploaded {media_type} from Gemini...")
            genai.delete_file(video_file.name)
        
        # Calculate processing time
        end_time = time.time()
        processing_time = end_time - start_time
        minutes = int(processing_time // 60)
        seconds = int(processing_time % 60)
        
        print(f"Processing complete! Total time: {minutes}m {seconds}s")
        
        return {
            "transcript": transcript,
            "transcript_length": len(transcript),
            "context": context,
            "context_length": len(context),
            "analysis": analysis,
            "analysis_length": len(analysis),
            "video_duration": duration,
            "processing_time_seconds": int(processing_time),
            "processing_time_formatted": f"{minutes}m {seconds}s"
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
            "version": VERSION,
            "message": "Video and audio analysis service with accessible psychological insights",
            "capabilities": {
                "max_media_length": "60+ minutes",
                "supported_formats": "video (mp4, mov, avi, mkv) and audio (mp3, m4a, wav, aac, flac, ogg)",
                "transcription": "Segmented for complete coverage",
                "context": "Setting, mood, people, and purpose",
                "analysis": "Accessible psychological insights"
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
            "context": result["context"],
            "context_length": result["context_length"],
            "analysis": result["analysis"],
            "analysis_length": result["analysis_length"],
            "video_duration_seconds": result.get("video_duration"),
            "processing_time_seconds": result.get("processing_time_seconds"),
            "processing_time_formatted": result.get("processing_time_formatted")
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
        "version": VERSION,
        "gemini_api_configured": bool(GOOGLE_API_KEY),
        "ffmpeg_available": os.system('which ffmpeg > /dev/null 2>&1') == 0,
        "supported_formats": {
            "video": ["mp4", "mov", "avi", "mkv"],
            "audio": ["mp3", "m4a", "wav", "aac", "flac", "ogg"]
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
