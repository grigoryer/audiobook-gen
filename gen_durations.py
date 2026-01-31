import csv
from pathlib import Path
from mutagen.mp3 import MP3

# Configuration
audio_dir = Path("./audio")
chapters_dir = Path("./chapters")
output_csv = "chapter_durations.csv"
SUSPICIOUS_SIZE_MB = 3  # Flag files smaller than this


def get_audio_duration(mp3_file: Path) -> tuple[str, int, float]:
    """Get the duration of an MP3 file
    Returns: (formatted_time, total_seconds, file_size_mb)
    """
    try:
        audio = MP3(mp3_file)
        duration_seconds = int(audio.info.length)
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        
        # Get file size in MB
        file_size_mb = mp3_file.stat().st_size / (1024 * 1024)
        
        return f"{minutes}:{seconds:02d}", duration_seconds, file_size_mb
    except Exception as e:
        print(f"Error reading {mp3_file.name}: {e}")
        return "0:00", 0, 0.0


def get_chapter_title(chapter_num: str) -> str:
    """Get the chapter title from the first line of the text file"""
    chapter_file = chapters_dir / f"ch_{chapter_num}.txt"
    try:
        with open(chapter_file, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            return first_line if first_line else "Unknown Title"
    except Exception as e:
        print(f"Error reading title from {chapter_file.name}: {e}")
        return "Unknown Title"


def main():
    # Find all MP3 files
    mp3_files = list(audio_dir.glob("ch_*.mp3"))
    
    if not mp3_files:
        print(f"No MP3 files found in {audio_dir}/")
        return
    
    # Sort numerically by chapter number
    mp3_files.sort(key=lambda x: int(x.stem.replace("ch_", "")))
    
    print(f"Found {len(mp3_files)} audio file(s)")
    print(f"Analyzing durations...\n")
    
    # Collect data
    chapter_data = []
    total_seconds = 0
    suspicious_files = []
    
    for mp3_file in mp3_files:
        # Extract chapter number from filename (e.g., "ch_1.mp3" -> "1")
        chapter_num = mp3_file.stem.replace("ch_", "")
        
        # Get title from text file
        title = get_chapter_title(chapter_num)
        
        # Get duration and size
        duration, seconds, size_mb = get_audio_duration(mp3_file)
        total_seconds += seconds
        
        # Flag suspicious files
        flag = ""
        if size_mb < SUSPICIOUS_SIZE_MB:
            flag = "⚠"
            suspicious_files.append((chapter_num, size_mb, duration))
        
        chapter_data.append({
            'chapter': chapter_num,
            'title': title,
            'duration': duration,
            'size_mb': f"{size_mb:.2f}"
        })
        
        print(f"{flag} ch_{chapter_num}: {title} - {duration} ({size_mb:.2f} MB)")
    
    # Write to CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['chapter', 'title', 'duration', 'size_mb']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(chapter_data)
    
    total_minutes = total_seconds // 60
    total_hours = total_minutes / 60
    
    print(f"\n✓ CSV created: {output_csv}")
    print(f"Total audio length: {total_minutes} minutes ({total_hours:.2f} hours)")
    
    if suspicious_files:
        print(f"\n⚠ Found {len(suspicious_files)} suspicious file(s) < {SUSPICIOUS_SIZE_MB} MB:")
        for ch_num, size, dur in suspicious_files:
            print(f"  ch_{ch_num}: {size:.2f} MB ({dur})")
        print(f"\nCreate 'chapters_to_regenerate.txt' with these chapter numbers:")
        for ch_num, _, _ in suspicious_files:
            print(ch_num)
    
    print(f"\nYou can now import '{output_csv}' into Google Sheets!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        raise