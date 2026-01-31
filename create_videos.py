import os
import subprocess
from pathlib import Path
from mutagen.mp3 import MP3
from concurrent.futures import ProcessPoolExecutor, as_completed
from config import get_config, VIDEO_MAX_WORKERS

# Get current book configuration
config = get_config()

# --- Configuration ---
image_file = f"./images/{config['cover_image']}"
audio_dir = Path("./audio")
output_dir = Path("./videos")
TARGET_DURATION_MINUTES = config["target_video_duration"]
max_workers = VIDEO_MAX_WORKERS

output_dir.mkdir(exist_ok=True)


def get_audio_duration_seconds(mp3_file: Path) -> float:
    """Get the duration of an MP3 file in seconds"""
    try:
        audio = MP3(mp3_file)
        return audio.info.length
    except Exception as e:
        print(f"Error reading duration for {mp3_file.name}: {e}")
        return 0.0


def create_video_from_audios(audio_files: list, start_num: str, end_num: str, total_duration: float):
    """Create video by concatenating audio files with a static image"""
    output_video = output_dir / f"{start_num}_{end_num}.mp4"
    
    # Check if video already exists
    if output_video.exists():
        print(f"⊘ Skipping {start_num}_{end_num} (already exists)")
        mins = int(total_duration // 60)
        return output_video, len(audio_files), mins, True
    
    # Build multiple audio inputs
    input_args = []
    for audio_file in audio_files:
        input_args.extend(["-i", str(audio_file)])
    
    # Build filter_complex for both video scaling and audio concat
    # Video: scale image to ensure even dimensions (required for H.264)
    # Audio: concatenate all audio files
    audio_filter = "".join(f"[{i+1}:0]" for i in range(len(audio_files)))
    filter_complex = f"[0:v]scale=trunc(iw/2)*2:trunc(ih/2)*2[v];{audio_filter}concat=n={len(audio_files)}:v=0:a=1[outa]"
    
    # Full FFmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-framerate", "1",
        "-i", image_file,
        *input_args,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "[outa]",
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(output_video)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    
    mins = int(total_duration // 60)
    return output_video, len(audio_files), mins, False


def process_group(group_info):
    """Process a group of chapters into a single video"""
    audio_files, start_num, end_num, total_duration = group_info
    
    try:
        output_video, num_chapters, mins, skipped = create_video_from_audios(
            audio_files, start_num, end_num, total_duration
        )
        return {
            'success': True,
            'video': output_video.name,
            'chapters': num_chapters,
            'duration': mins,
            'start': int(start_num),
            'end': int(end_num),
            'skipped': skipped
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'start': int(start_num),
            'end': int(end_num),
            'skipped': False
        }


def group_chapters_by_duration(audio_files_with_duration, target_minutes):
    """Group chapters until reaching target duration"""
    groups = []
    current_group = []
    current_duration = 0
    target_seconds = target_minutes * 60
    
    for audio_file, duration, chapter_num in audio_files_with_duration:
        current_group.append(audio_file)
        current_duration += duration
        
        if current_duration >= target_seconds:
            start_num = current_group[0].stem.replace("ch_", "")
            end_num = current_group[-1].stem.replace("ch_", "")
            groups.append((current_group.copy(), start_num, end_num, current_duration))
            current_group = []
            current_duration = 0
    
    if current_group:
        start_num = current_group[0].stem.replace("ch_", "")
        end_num = current_group[-1].stem.replace("ch_", "")
        groups.append((current_group.copy(), start_num, end_num, current_duration))
    
    return groups


def main():
    print("="*60)
    print("Video Creator - Grouping by Duration")
    print("="*60)
    
    audio_files = sorted(audio_dir.glob("ch_*.mp3"), key=lambda x: int(x.stem.replace("ch_", "")))
    
    if not audio_files:
        print(f"No audio files found in {audio_dir}/")
        return
    
    print(f"Found {len(audio_files)} audio file(s)")
    print(f"Target duration per video: {TARGET_DURATION_MINUTES} minutes")
    print(f"Analyzing durations...\n")
    
    audio_files_with_duration = []
    for audio_file in audio_files:
        duration = get_audio_duration_seconds(audio_file)
        chapter_num = audio_file.stem.replace("ch_", "")
        audio_files_with_duration.append((audio_file, duration, chapter_num))
    
    groups = group_chapters_by_duration(audio_files_with_duration, TARGET_DURATION_MINUTES)
    
    print(f"Creating {len(groups)} video(s)\n")
    
    total_chapters = len(audio_files)
    processed_chapters = 0
    completed_videos = 0
    skipped_videos = 0
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_group, group) for group in groups]
        
        for future in as_completed(futures):
            result = future.result()
            
            if result['success']:
                if result['skipped']:
                    skipped_videos += 1
                else:
                    completed_videos += 1
                    print(f"✓ Finished: {result['video']} ({result['chapters']} chapters, {result['duration']} mins)")
                
                processed_chapters = result['end']
                print(f"  Chapters processed: {processed_chapters}/{total_chapters}\n")
            else:
                print(f"✗ Failed: chapters {result['start']}-{result['end']}")
                print(f"  Error: {result['error']}\n")
    
    print("="*60)
    print(f"✓ Video processing complete!")
    print(f"Created: {completed_videos} | Skipped: {skipped_videos}")
    print(f"Output directory: {output_dir.absolute()}")
    print("="*60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        raise