#!/bin/bash

# Audiobook Production Pipeline
# Converts EPUB → Chapters → Audio → Videos
# Usage: ./run_pipeline.sh
# 
# To switch books: Edit config.py and change BOOK_ID

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get configuration from config.py
BOOK_ID=$(python3 -c "from config import BOOK_ID; print(BOOK_ID)")
EPUB_FILE=$(python3 -c "from config import get_config; print(get_config()['epub_file'])")
COVER_IMAGE=$(python3 -c "from config import get_config; print(get_config()['cover_image'])")
GDRIVE_DEST=$(python3 -c "from config import get_config; print(get_config()['gdrive_folder'])")
ENABLE_UPLOAD=$(python3 -c "from config import ENABLE_GDRIVE_UPLOAD; print(str(ENABLE_GDRIVE_UPLOAD).lower())")

# Fixed directories
CHAPTERS_DIR="chapters"
AUDIO_DIR="audio"
VIDEOS_DIR="videos"
IMAGES_DIR="images"

GDRIVE_DESTINATION="$GDRIVE_DEST"
ENABLE_GDRIVE_UPLOAD=$([[ "$ENABLE_UPLOAD" == "true" ]] && echo "true" || echo "false")

# Function to print colored messages
print_step() {
    echo -e "${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if EPUB file exists
if [ ! -f "$EPUB_FILE" ]; then
    print_error "EPUB file not found: $EPUB_FILE"
    echo "Usage: ./run_pipeline.sh <epub_file>"
    exit 1
fi

# Check if cover image exists
if [ ! -f "$IMAGES_DIR/$COVER_IMAGE" ]; then
    print_warning "Cover image not found at $IMAGES_DIR/$COVER_IMAGE"
    print_warning "Videos will fail without a cover image"
fi

# Start pipeline
echo ""
print_step "Starting Audiobook Production Pipeline"
echo "Book ID: $BOOK_ID"
echo "EPUB File: $EPUB_FILE"
echo "Cover: $IMAGES_DIR/$COVER_IMAGE"
echo "Start Time: $(date)"
echo ""

# Step 1: Split EPUB into chapters
print_step "Step 1/5: Splitting EPUB into chapters"
if [ -d "$CHAPTERS_DIR" ]; then
    print_warning "Chapters directory already exists. Skipping split..."
    CHAPTER_COUNT=$(ls -1 "$CHAPTERS_DIR"/ch_*.txt 2>/dev/null | wc -l)
    echo "Total chapters: $CHAPTER_COUNT"
else
    python3 epub_chapter_splitter.py "$CHAPTERS_DIR"
    
    if [ $? -eq 0 ]; then
        print_success "Chapters created successfully"
        CHAPTER_COUNT=$(ls -1 "$CHAPTERS_DIR"/ch_*.txt 2>/dev/null | wc -l)
        echo "Total chapters: $CHAPTER_COUNT"
    else
        print_error "Failed to split chapters"
        exit 1
    fi
fi

echo ""

# Step 2: Generate audio files
print_step "Step 2/5: Generating audio files"
mkdir -p "$AUDIO_DIR"

EXISTING_AUDIO=$(ls -1 "$AUDIO_DIR"/ch_*.mp3 2>/dev/null | wc -l)
if [ $EXISTING_AUDIO -gt 0 ]; then
    print_warning "Found $EXISTING_AUDIO existing audio file(s). They will be preserved."
    print_warning "gen_audio.py will only generate missing chapters."
fi

python3 gen_audio.py

if [ $? -eq 0 ]; then
    print_success "Audio files generated successfully"
    AUDIO_COUNT=$(ls -1 "$AUDIO_DIR"/ch_*.mp3 2>/dev/null | wc -l)
    echo "Total audio files: $AUDIO_COUNT"
else
    print_error "Failed to generate audio files"
    exit 1
fi

echo ""

# Step 3: Check durations and create CSV
print_step "Step 3/5: Analyzing audio durations"
python3 get_durations.py

if [ $? -eq 0 ]; then
    print_success "Duration analysis complete"
    if [ -f "chapter_durations.csv" ]; then
        print_success "CSV file created: chapter_durations.csv"
    fi
else
    print_error "Failed to analyze durations"
    exit 1
fi

echo ""

# Step 4: Create videos
print_step "Step 4/5: Creating videos"
mkdir -p "$VIDEOS_DIR"

EXISTING_VIDEOS=$(ls -1 "$VIDEOS_DIR"/*.mp4 2>/dev/null | wc -l)
if [ $EXISTING_VIDEOS -gt 0 ]; then
    print_warning "Found $EXISTING_VIDEOS existing video file(s). They will be preserved."
    print_warning "create_videos.py will skip video groups that already exist."
fi

python3 create_videos.py

if [ $? -eq 0 ]; then
    print_success "Videos created successfully"
    VIDEO_COUNT=$(ls -1 "$VIDEOS_DIR"/*.mp4 2>/dev/null | wc -l)
    echo "Total videos: $VIDEO_COUNT"
else
    print_error "Failed to create videos"
    exit 1
fi

echo ""

# Step 5: Upload to Google Drive
print_step "Step 5/5: Uploading to Google Drive"

if [ "$ENABLE_GDRIVE_UPLOAD" = true ]; then
    if ! command -v rclone &> /dev/null; then
        print_error "rclone is not installed"
        echo "Install it with: sudo apt-get install rclone"
        print_warning "Skipping Google Drive upload"
    else
        if ! rclone listremotes | grep -q "gdrive:"; then
            print_error "Google Drive not configured in rclone"
            echo "Configure it with: rclone config"
            print_warning "Skipping Google Drive upload"
        else
            print_success "Uploading to gdrive:$GDRIVE_DESTINATION"
            rclone copy ./$VIDEOS_DIR gdrive:$GDRIVE_DESTINATION -P --transfers 4
            
            if [ $? -eq 0 ]; then
                print_success "Videos uploaded successfully to Google Drive"
            else
                print_error "Failed to upload videos to Google Drive"
            fi
        fi
    fi
else
    print_warning "Google Drive upload disabled (set ENABLE_GDRIVE_UPLOAD=true to enable)"
fi

echo ""

# Final summary
print_step "Pipeline Complete!"
echo "End Time: $(date)"
echo ""
echo "Summary:"
echo "  Chapters: $CHAPTER_COUNT"
echo "  Audio Files: $AUDIO_COUNT"
echo "  Videos: $VIDEO_COUNT"
echo ""
echo "Output locations:"
echo "  Chapters: ./$CHAPTERS_DIR/"
echo "  Audio: ./$AUDIO_DIR/"
echo "  Videos: ./$VIDEOS_DIR/"
echo "  CSV: ./chapter_durations.csv"
echo ""
print_success "All done!"