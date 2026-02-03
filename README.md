# Audiobook Production Pipeline

Automated pipeline to convert EPUB books into audiobook videos. Supports multiple book projects with easy switching via centralized configuration.

**Pipeline:** EPUB → Chapters → Audio (Edge TTS) → Videos (FFmpeg) → Google Drive

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/grigoryer/audiobook-pipeline.git
cd audiobook-pipeline

# 2. Install dependencies
pip3 install -r requirements.txt
sudo apt-get install ffmpeg rclone  # or: brew install ffmpeg rclone

# 3. Add your book files
cp your_book.epub rtoc.epub
cp your_cover.jpg images/rtoc_cover.jpg

# 4. Configure (optional - defaults work for most cases)
nano config.py

# 5. Run pipeline
./run_pipeline.sh
```

---

## Installation

### System Requirements
- Python 3.8+
- FFmpeg
- 8+ GB RAM
- ~10 GB storage per 100 chapters

### Dependencies

**System packages:**
```bash
# Ubuntu/Debian
sudo apt-get install -y ffmpeg rclone python3-pip

# macOS
brew install ffmpeg rclone
```

**Python packages:**
```bash
pip3 install -r requirements.txt
```

Contents of `requirements.txt`:
- `ebooklib` - EPUB parsing
- `beautifulsoup4` - HTML/XML parsing
- `lxml` - XML processing
- `edge-tts` - Text-to-speech (Microsoft Edge TTS API)
- `mutagen` - Audio metadata reading

---

## Configuration

### Multi-Book Setup

Edit `config.py` to manage multiple book projects:

```python
# Switch between books by changing this:
BOOK_ID = "rtoc"  # Current book

# Define your books:
BOOKS = {
    "rtoc": {
        "name": "Reverend Insanity",
        "epub_file": "rtoc.epub",
        "cover_image": "rtoc_cover.jpg",
        "gdrive_folder": "Audiobooks/RTOC",
        "target_video_duration": 120,
        "voice": "en-US-AndrewNeural",
        "speech_rate": "+15%",
    },
    
    "your_book": {
        "name": "Your Book Name",
        "epub_file": "your_book.epub",
        "cover_image": "your_cover.jpg",
        "gdrive_folder": "Audiobooks/YourBook",
        "target_video_duration": 120,
        "voice": "en-US-AndrewNeural",
        "speech_rate": "+15%",
    },
}
```

### Adding a New Book

1. **Add book to config:**
```python
# In config.py
BOOKS = {
    # ... existing books ...
    
    "newbook": {
        "name": "New Book Title",
        "epub_file": "newbook.epub",
        "cover_image": "newbook_cover.jpg",
        "gdrive_folder": "Audiobooks/NewBook",
        "target_video_duration": 120,
        "voice": "en-US-AndrewNeural",
        "speech_rate": "+15%",
    },
}
```

2. **Add files:**
```bash
cp your_epub.epub newbook.epub
cp your_cover.jpg images/newbook_cover.jpg
```

3. **Switch to new book:**
```python
# In config.py
BOOK_ID = "newbook"
```

4. **Run pipeline:**
```bash
./run_pipeline.sh
```

### Configuration Options

**Per-book settings:**
- `epub_file` - Source EPUB filename
- `cover_image` - Cover art filename (in `images/` folder)
- `gdrive_folder` - Google Drive upload destination
- `target_video_duration` - Minutes per video (default: 120)
- `voice` - TTS voice (see Voice Options below)
- `speech_rate` - Speed adjustment (e.g., "+15%", "+20%", "+0%")

**System settings (same for all books):**
- `AUDIO_CONCURRENCY` - Worker threads for audio generation (4-8 recommended)
- `MAX_RETRIES` - Retry attempts for failed chapters (default: 3)
- `VIDEO_MAX_WORKERS` - CPU cores for video creation (None = auto-detect)
- `ENABLE_GDRIVE_UPLOAD` - Enable/disable Google Drive upload

### Voice Options

Available TTS voices:
- `en-US-AndrewNeural` - Male, clear (default)
- `en-US-AriaNeural` - Female, natural
- `en-US-GuyNeural` - Male, news presenter
- `en-GB-RyanNeural` - Male, British accent
- `en-GB-SoniaNeural` - Female, British accent

Full list: https://github.com/rany2/edge-tts#voice-list

---

## Usage

### Full Pipeline

```bash
# Automatic - processes everything
./run_pipeline.sh

# Background processing
nohup ./run_pipeline.sh > pipeline.log 2>&1 &
tail -f pipeline.log
```

### Individual Steps

```bash
# 1. Split EPUB
python3 epub_chapter_splitter.py rtoc.epub chapters

# 2. Generate audio
python3 gen_audio.py

# 3. Analyze durations
python3 get_durations.py

# 4. Create videos
python3 create_videos.py

# 5. Upload to Google Drive
rclone copy ./videos gdrive:Audiobooks/RTOC -P
```

### Partial Processing

**Generate specific chapter range:**
```python
# Edit gen_audio.py
START_CHAPTER = 100
END_CHAPTER = 200

# Then run
python3 gen_audio.py
```

**Regenerate failed chapters:**
```bash
# Check for issues
python3 get_durations.py

# Create list of failed chapters
echo "126
127
130" > chapters_to_regenerate.txt

# Regenerate
python3 regen_audio.py
```

---

## Google Drive Setup

```bash
# Configure rclone
rclone config
```

**Steps:**
1. New remote: `n`
2. Name: `gdrive`
3. Storage: `drive`
4. Client ID/Secret: [leave blank]
5. Scope: `1` (full access)
6. Advanced: `n`
7. Auto config: `n` (for servers) or `y` (local)

**For remote servers (AWS):**
```bash
# Server shows URL - on LOCAL machine run:
rclone authorize "drive" "TOKEN_FROM_SERVER"

# Copy output token back to server
```

**Verify:**
```bash
rclone listremotes  # Should show: gdrive:
rclone lsd gdrive:  # Test connection
```

---

## File Structure

```
audiobook-pipeline/
├── config.py              # Multi-book configuration
├── requirements.txt       # Python dependencies
├── run_pipeline.sh       # Main automation script
│
├── Scripts:
│   ├── epub_chapter_splitter.py
│   ├── gen_audio.py
│   ├── get_durations.py
│   ├── create_videos.py
│   └── regen_audio.py
│
├── Input (add your files):
│   ├── rtoc.epub
│   ├── lotm.epub
│   └── images/
│       ├── rtoc_cover.jpg
│       └── lotm_cover.jpg
│
└── Output (auto-generated):
    ├── chapters/          # Text files
    ├── audio/             # MP3 files
    ├── videos/            # MP4 files
    └── chapter_durations.csv
```

---

## Troubleshooting

### Audio Files Too Small

**Symptom:** Files < 2 MB, short duration despite long chapters

**Cause:** Too many concurrent API calls

**Fix:**
```python
# In config.py, reduce:
AUDIO_CONCURRENCY = 4  # Lower from 6-8
```

### FFmpeg Width Error

**Symptom:** `width not divisible by 2 (1199x752)`

**Cause:** Cover image has odd width (H.264 requires even dimensions)

**Fix:**
```bash
# Resize cover to even dimensions
ffmpeg -i images/cover.jpg -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" images/cover_fixed.jpg
mv images/cover_fixed.jpg images/rtoc_cover.jpg
```

Now handled automatically by the pipeline.

### Videos Not Skipping

**Symptom:** Videos regenerate every run

**Solution:** Use latest `create_videos.py` which includes skip logic

### Missing Chapters

**Symptom:** Some chapter numbers missing (ch_143, ch_211)

**Cause:** Chapters don't exist in EPUB

**Solution:** Expected behavior - EPUB may skip numbers

---

## Performance Tuning

### Audio Generation

**Critical:** Too many workers causes truncated audio

**Safe values:**
- Local Mac: 4-6 workers
- AWS c6i.2xlarge (8 cores): 6-8 workers
- If truncation occurs: reduce to 4

```python
# In config.py
AUDIO_CONCURRENCY = 6
```

### Video Creation

Use all CPU cores for video encoding:

```python
# In config.py
VIDEO_MAX_WORKERS = None  # Auto-detect (recommended)
```

---

## Output Specifications

### Audio Files
- Format: MP3
- Bitrate: 48 kbps
- Sample rate: 24000 Hz
- Channels: Mono
- Size: ~3-10 MB per chapter

### Video Files
- Container: MP4
- Video codec: H.264
- Video bitrate: Minimal (1fps still image)
- Audio codec: AAC 192 kbps
- Duration: ~120 minutes per video
- Size: ~50-60 MB per video

### Processing Time (640 chapters on AWS c6i.2xlarge)
- EPUB splitting: < 5 min
- Audio generation: 3-4 hours
- Video creation: 2-3 hours
- Total: ~6-8 hours

---

## AWS Deployment

### Launch Instance

```bash
# Recommended: c6i.2xlarge spot instance
# 8 vCPUs, 16 GB RAM, 50 GB storage
# Cost: ~$0.10/hour (spot) or $0.34/hour (on-demand)
```

### Setup

```bash
ssh -i key.pem ubuntu@instance-ip

# Install dependencies
sudo apt-get update
sudo apt-get install -y ffmpeg python3-pip rclone git

# Clone and setup
git clone https://github.com/yourusername/audiobook-pipeline.git
cd audiobook-pipeline
pip3 install -r requirements.txt

# Configure
rclone config  # Setup Google Drive
nano config.py  # Set BOOK_ID

# Add files
# Upload EPUB and cover via scp or download with wget

# Run
nohup ./run_pipeline.sh > pipeline.log 2>&1 &
```

### Monitor

```bash
# Watch progress
tail -f pipeline.log

# Check status
ps aux | grep python
ls -1 videos/*.mp4 | wc -l
```

### Cleanup

```bash
# After completion, terminate instance to stop billing
# Verify files uploaded to Google Drive first:
rclone ls gdrive:Audiobooks/RTOC
```

---

## Switching Between Books

### Example Workflow

**Currently processing "rtoc":**
```python
# config.py
BOOK_ID = "rtoc"
```

**Switch to "lotm":**
```python
# config.py
BOOK_ID = "lotm"
```

**Files are automatically isolated:**
- Same folders (`chapters/`, `audio/`, `videos/`) are reused
- Each book uses its own EPUB and cover from config
- Outputs upload to different Google Drive folders
- No file conflicts between books

**Clean slate for new book:**
```bash
# Remove old outputs (optional)
rm -rf chapters/ audio/ videos/

# Run pipeline for new book
./run_pipeline.sh
```

---

## Common Commands

```bash
# Check which book is active
python3 -c "from config import BOOK_ID; print(BOOK_ID)"

# List configured books
python3 -c "from config import BOOKS; print(list(BOOKS.keys()))"

# Count outputs
echo "Chapters: $(ls -1 chapters/*.txt 2>/dev/null | wc -l)"
echo "Audio: $(ls -1 audio/*.mp3 2>/dev/null | wc -l)"
echo "Videos: $(ls -1 videos/*.mp4 2>/dev/null | wc -l)"

# Find suspicious audio files
python3 get_durations.py | grep "⚠"

# Stop pipeline
pkill -f run_pipeline

# Download from Google Drive
rclone copy gdrive:Audiobooks/RTOC ./videos -P
```

---

## Tips

1. **Test with small batch first** - Set `END_CHAPTER = 50` in `gen_audio.py`
2. **Use spot instances** on AWS for 70% savings
3. **Keep audio backups** before regenerating
4. **Monitor first hour** to catch issues early
5. **Verify cover dimensions** are even before starting
6. **Lower concurrency** if audio truncates
7. **Don't terminate AWS** until files are uploaded

---

## Support

For issues:
- Audio truncation → Reduce `AUDIO_CONCURRENCY` in `config.py`
- FFmpeg errors → Check cover image dimensions
- Missing chapters → Expected if not in EPUB
- Upload failures → Verify `rclone config`

---

## License

Open source - modify and distribute freely.
