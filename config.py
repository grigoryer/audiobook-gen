# =============================================================================
# AUDIOBOOK PIPELINE CONFIGURATION
# =============================================================================
# Edit this file to switch between different book projects
# All scripts will read from this configuration

# =============================================================================
# CURRENT PROJECT - CHANGE THIS TO SWITCH BOOKS
# =============================================================================

BOOK_ID = "rtoc"  # Unique identifier for this book (used in paths)

# =============================================================================
# BOOK-SPECIFIC SETTINGS
# =============================================================================

BOOKS = {
    "rtoc": {
        "name": "Reverend Insanity",
        "epub_file": "rtoc.epub",
        "cover_image": "rtoc_cover.jpg",
        "gdrive_folder": "Audiobooks/RTOC",
        "target_video_duration": 120,  # minutes per video
        "voice": "en-US-AndrewNeural",
        "speech_rate": "+15%",
    },
    
    "lotm": {
        "name": "Lord of the Mysteries",
        "epub_file": "lotm.epub",
        "cover_image": "lotm_cover.jpg",
        "gdrive_folder": "Audiobooks/LOTM",
        "target_video_duration": 120,
        "voice": "en-US-AndrewNeural",
        "speech_rate": "+15%",
    },
    
    "example": {
        "name": "Example Book",
        "epub_file": "book.epub",
        "cover_image": "cover.jpg",
        "gdrive_folder": "Audiobooks/ExampleBook",
        "target_video_duration": 120,
        "voice": "en-US-AndrewNeural",
        "speech_rate": "+15%",
    },
}

# =============================================================================
# SYSTEM SETTINGS (SAME FOR ALL BOOKS)
# =============================================================================

# Audio generation
AUDIO_CONCURRENCY = 6  # 4-8 recommended, reduce to 4 if audio truncates
MAX_RETRIES = 3

# Video creation
VIDEO_MAX_WORKERS = None  # None = auto-detect CPU cores

# Google Drive
ENABLE_GDRIVE_UPLOAD = True

# =============================================================================
# GET CURRENT BOOK CONFIG
# =============================================================================

def get_config():
    """Get configuration for current book"""
    if BOOK_ID not in BOOKS:
        raise ValueError(f"Unknown BOOK_ID: {BOOK_ID}. Available: {list(BOOKS.keys())}")
    return BOOKS[BOOK_ID]

# =============================================================================
# USAGE IN OTHER SCRIPTS
# =============================================================================
# from config import get_config, AUDIO_CONCURRENCY
# 
# config = get_config()
# epub_file = config["epub_file"]
# voice = config["voice"]