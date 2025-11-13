import os
import time
import google.generativeai as genai
from flask import Flask, jsonify, send_file, request
import requests
import tempfile
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

# Version info
VERSION = "1.5.0"  # Semantic versioning: MAJOR.MINOR.PATCH

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

def detect_silence_ratio(segment_path, silence_threshold_db=-35, min_silence_duration=2.0):
    """
    Detect the ratio of silence in an audio/video segment.
    
    Args:
        segment_path: Path to the media segment
        silence_threshold_db: dB level below which audio is considered silent (default: -35)
        min_silence_duration: Minimum duration of silence to count in seconds (default: 2.0)
    
    Returns:
        float: Ratio of silence (0.0 to 1.0), or None if detection fails
    """
    
    try:
        # Use ffmpeg silencedetect filter to find silent periods
        cmd = [
            'ffmpeg',
            '-i', segment_path,
            '-af', f'silencedetect=noise={silence_threshold_db}dB:d={min_silence_duration}',
            '-f', 'null',
            '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        stderr = result.stderr
        
        # Parse silence_start and silence_end from output
        import re
        silence_starts = re.findall(r'silence_start: ([\d.]+)', stderr)
        silence_ends = re.findall(r'silence_end: ([\d.]+)', stderr)
        
        if not silence_starts:
            # No silence detected - segment has continuous audio
            return 0.0
        
        # Get segment duration
        duration_cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json',
            segment_path
        ]
        
        duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=30)
        
        if duration_result.returncode != 0:
            print(f"Could not determine segment duration for silence detection")
            return None
        
        segment_duration = float(json.loads(duration_result.stdout)['format']['duration'])
        
        # Calculate total silence duration
        total_silence = 0.0
        
        for i in range(len(silence_ends)):
            if i < len(silence_starts):
                start = float(silence_starts[i])
                end = float(silence_ends[i])
                total_silence += (end - start)
        
        # Calculate silence ratio
        silence_ratio = total_silence / segment_duration if segment_duration > 0 else 0.0
        
        return silence_ratio
        
    except Exception as e:
        print(f"Error detecting silence: {e}")
        return None

def analyze_media_content_density(video_path, sample_duration=60):
    """
    Analyze a sample of the media to determine content density.
    Used to adaptively choose segment duration.
    
    Args:
        video_path: Path to the full media file
        sample_duration: Duration of sample to analyze in seconds (default: 60)
    
    Returns:
        str: 'sparse', 'moderate', or 'dense'
    """
    
    try:
        # Create a sample segment from the middle of the file
        duration = get_video_duration(video_path)
        
        if not duration or duration < sample_duration:
            return 'moderate'  # Default for short files
        
        # Sample from the middle
        start_time = duration / 2
        sample_path = tempfile.NamedTemporaryFile(delete=False, suffix='.tmp').name
        
        # Extract sample
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', str(start_time),
            '-t', str(sample_duration),
            '-c', 'copy',
            '-y',
            sample_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print("Could not create sample for content density analysis")
            return 'moderate'
        
        # Detect silence ratio in sample
        silence_ratio = detect_silence_ratio(sample_path)
        
        # Clean up sample
        try:
            os.remove(sample_path)
        except:
            pass
        
        if silence_ratio is None:
            return 'moderate'
        
        # Classify based on silence ratio
        if silence_ratio > 0.6:
            print(f"Content density: SPARSE (silence ratio: {silence_ratio:.2f})")
            return 'sparse'
        elif silence_ratio > 0.3:
            print(f"Content density: MODERATE (silence ratio: {silence_ratio:.2f})")
            return 'moderate'
        else:
            print(f"Content density: DENSE (silence ratio: {silence_ratio:.2f})")
            return 'dense'
            
    except Exception as e:
        print(f"Error analyzing content density: {e}")
        return 'moderate'  # Default to moderate on error

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
        model_name="gemini-2.5-flash",
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

def transcribe_segment_worker(segment_path, segment_num, start_time, duration, is_audio):
    """
    Worker function to transcribe a single segment - designed for parallel execution.
    
    Args:
        segment_path: Path to the segment file
        segment_num: Segment number (for logging)
        start_time: Start time in seconds from beginning of full media
        duration: Duration of this segment
        is_audio: Whether this is audio-only media
    
    Returns:
        dict: Result containing transcript or error info
    """
    
    try:
        # Check for silence first (OPTIMIZATION #1: Smart Silence Detection)
        silence_ratio = detect_silence_ratio(segment_path)
        
        if silence_ratio is not None and silence_ratio > 0.80:
            # Segment is >80% silent - skip transcription
            start_minutes = int(start_time // 60)
            start_seconds = int(start_time % 60)
            end_time = start_time + duration
            end_minutes = int(end_time // 60)
            end_seconds = int(end_time % 60)
            
            print(f"⏭️  Segment {segment_num} is {silence_ratio*100:.1f}% silent - skipping transcription")
            
            return {
                'success': True,
                'segment_num': segment_num,
                'transcript': f"[{start_minutes:02d}:{start_seconds:02d} - {end_minutes:02d}:{end_seconds:02d}] [Mostly silent - no significant audio content]",
                'skipped': True
            }
        
        # Upload segment to Gemini
        print(f"Uploading segment {segment_num}...")
        mime_type = get_mime_type(segment_path)
        video_file = genai.upload_file(
            path=segment_path,
            display_name=f"segment_{segment_num}",
            mime_type=mime_type
        )
        
        # Wait for processing
        while video_file.state.name == "PROCESSING":
            time.sleep(3)
            video_file = genai.get_file(video_file.name)
        
        if video_file.state.name == "FAILED":
            return {
                'success': False,
                'segment_num': segment_num,
                'transcript': f"[Segment {segment_num} processing failed]",
                'skipped': False
            }
        
        # Transcribe segment
        transcript = transcribe_segment(video_file, segment_num, start_time, is_audio)
        
        # Cleanup
        genai.delete_file(video_file.name)
        
        return {
            'success': True,
            'segment_num': segment_num,
            'transcript': transcript,
            'skipped': False
        }
        
    except Exception as e:
        print(f"Error in segment {segment_num} worker: {e}")
        start_minutes = int(start_time // 60)
        start_seconds = int(start_time % 60)
        return {
            'success': False,
            'segment_num': segment_num,
            'transcript': f"[Error transcribing segment starting at {start_minutes:02d}:{start_seconds:02d}: {str(e)}]",
            'skipped': False
        }

def transcribe_video_in_segments(video_path, segment_duration=240, is_audio=None, max_workers=4):
    """
    Transcribe video or audio by breaking it into segments with intelligent optimizations.
    
    OPTIMIZATIONS IMPLEMENTED:
    1. Smart Silence Detection - Skips segments that are >80% silent
    2. Adaptive Segment Duration - Adjusts segment size based on content density
    3. Parallel Processing - Processes multiple segments simultaneously
    
    Args:
        video_path: Path to the media file
        segment_duration: Base duration of each segment in seconds (may be adjusted)
        is_audio: Optional boolean, if provided skips media type detection
        max_workers: Maximum number of parallel transcription workers (default: 4)
    """
    
    print(f"Starting OPTIMIZED segmented transcription...")
    
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
    
    # OPTIMIZATION #2: Adaptive Segment Duration Based on Content
    print("Analyzing content density for adaptive segmentation...")
    content_density = analyze_media_content_density(video_path)
    
    # Adjust segment duration based on content density
    if content_density == 'sparse':
        segment_duration = 600  # 10 minutes for sparse content (lots of silence)
        print(f"📊 Using LONG segments (10 min) for sparse content")
    elif content_density == 'dense':
        segment_duration = 180  # 3 minutes for dense content
        print(f"📊 Using SHORT segments (3 min) for dense content")
    else:
        segment_duration = 300  # 5 minutes for moderate content
        print(f"📊 Using MEDIUM segments (5 min) for moderate content")
    
    # Calculate number of segments
    num_segments = int((total_duration // segment_duration) + (1 if total_duration % segment_duration > 0 else 0))
    print(f"Media will be split into {num_segments} segments of ~{segment_duration}s each")
    
    all_segment_files = []
    segment_info = []  # Store segment metadata
    
    try:
        # Step 1: Create ALL segments first (fast - just file splitting)
        print(f"\n🔪 Creating {num_segments} segments...")
        for i in range(num_segments):
            start_time = i * segment_duration
            duration = min(segment_duration, total_duration - start_time)
            
            if duration <= 0:
                break
            
            # Create segment file with proper extension
            segment_path = tempfile.NamedTemporaryFile(delete=False, suffix=ext).name
            all_segment_files.append(segment_path)
            
            if create_video_segment(video_path, start_time, duration, segment_path):
                segment_info.append({
                    'path': segment_path,
                    'segment_num': i + 1,
                    'start_time': start_time,
                    'duration': duration
                })
            else:
                segment_info.append({
                    'path': None,
                    'segment_num': i + 1,
                    'start_time': start_time,
                    'duration': duration,
                    'creation_failed': True
                })
        
        print(f"✅ Created {len(segment_info)} segments")
        
        # Step 2: OPTIMIZATION #3 - Process segments in PARALLEL
        print(f"\n🚀 Processing {len(segment_info)} segments with {max_workers} parallel workers...")
        
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all transcription jobs
            future_to_segment = {}
            
            for seg_info in segment_info:
                if seg_info.get('creation_failed'):
                    # Handle failed segment creation immediately
                    results.append({
                        'success': False,
                        'segment_num': seg_info['segment_num'],
                        'transcript': f"[Segment {seg_info['segment_num']} creation failed]",
                        'skipped': False
                    })
                else:
                    # Submit for parallel processing
                    future = executor.submit(
                        transcribe_segment_worker,
                        seg_info['path'],
                        seg_info['segment_num'],
                        seg_info['start_time'],
                        seg_info['duration'],
                        is_audio
                    )
                    future_to_segment[future] = seg_info['segment_num']
            
            # Collect results as they complete
            for future in as_completed(future_to_segment):
                segment_num = future_to_segment[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Log completion
                    if result.get('skipped'):
                        print(f"✓ Segment {segment_num} skipped (silent)")
                    else:
                        print(f"✓ Segment {segment_num} completed")
                        
                except Exception as e:
                    print(f"✗ Segment {segment_num} failed: {e}")
                    results.append({
                        'success': False,
                        'segment_num': segment_num,
                        'transcript': f"[Segment {segment_num} failed: {str(e)}]",
                        'skipped': False
                    })
        
        # Step 3: Sort results by segment number and combine transcripts
        results.sort(key=lambda x: x['segment_num'])
        all_transcripts = [r['transcript'] for r in results]
        combined_transcript = "\n\n".join(all_transcripts)
        
        # Calculate statistics
        total_segments = len(results)
        skipped_segments = sum(1 for r in results if r.get('skipped', False))
        failed_segments = sum(1 for r in results if not r.get('success', True))
        processed_segments = total_segments - skipped_segments - failed_segments
        
        print(f"\n✅ Transcription complete!")
        print(f"   📊 Statistics:")
        print(f"      • Total segments: {total_segments}")
        print(f"      • Transcribed: {processed_segments}")
        print(f"      • Skipped (silent): {skipped_segments}")
        print(f"      • Failed: {failed_segments}")
        print(f"   📝 Total transcript: {len(combined_transcript)} characters")
        
        return combined_transcript
        
    finally:
        # Cleanup all segment files
        for segment_file in all_segment_files:
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
        model_name="gemini-2.5-flash",
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

**Names Mentioned:**
List all names of people mentioned in the audio (not just the speakers, but anyone referenced). For each name, indicate approximately how many times it was mentioned. Format as:
- Name 1 (mentioned X times)
- Name 2 (mentioned X times)
If no names are mentioned, simply note "No specific names mentioned."

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

**Names Mentioned:**
List all names of people mentioned in the video (both speakers and anyone referenced). For each name, indicate approximately how many times it was mentioned. Format as:
- Name 1 (mentioned X times)
- Name 2 (mentioned X times)
If no names are mentioned, simply note "No specific names mentioned."

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
        model_name="gemini-2.5-flash",
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
    """Main processing function with optimized segmented transcription and dual analysis"""
    
    import time
    start_time = time.time()
    
    print("Starting OPTIMIZED media processing...")
    print("Optimizations: Silence Detection + Adaptive Segments + Parallel Processing")
    
    video_path = download_video(video_url)
    
    try:
        # OPTIMIZATION: Detect media type ONCE at the start
        is_audio = is_audio_only(video_path)
        media_type = "audio" if is_audio else "video"
        print(f"Media type detected: {media_type}")
        
        # Get duration for statistics
        duration = get_video_duration(video_path)
        
        # Transcribe with all optimizations enabled
        # Adaptive segment duration is now handled inside transcribe_video_in_segments
        transcript = transcribe_video_in_segments(
            video_path, 
            segment_duration=300,  # Base duration, will be adjusted adaptively
            is_audio=is_audio,
            max_workers=4  # Parallel processing with 4 workers
        )
        
        # OPTIMIZATION: Upload full video ONCE for both context and analysis
        print(f"\nUploading full {media_type} for context and analysis...")
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
            # Use the same uploaded file for both analyses
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
        
        print(f"\n🎉 Processing complete! Total time: {minutes}m {seconds}s")
        
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
            "message": "OPTIMIZED video and audio analysis with Gemini 2.5 Flash",
            "capabilities": {
                "max_media_length": "120+ minutes (2+ hours)",
                "supported_formats": "video (mp4, mov, avi, mkv) and audio (mp3, m4a, wav, aac, flac, ogg)",
                "transcription": "Intelligent segmentation with silence detection",
                "processing": "Parallel processing for 40-60% faster results",
                "context": "Setting, mood, people, purpose, and names mentioned",
                "analysis": "Accessible psychological insights"
            },
            "optimizations": [
                "Smart silence detection - skips empty segments",
                "Adaptive segment duration - adjusts based on content density",
                "Parallel processing - 4 simultaneous workers"
            ]
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
        },
        "optimizations": {
            "silence_detection": "Skips segments >80% silent",
            "adaptive_segments": "Adjusts segment size based on content density",
            "parallel_processing": "Processes 4 segments simultaneously"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
