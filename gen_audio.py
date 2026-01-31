import asyncio
import edge_tts
from pathlib import Path
from config import get_config, AUDIO_CONCURRENCY, MAX_RETRIES

# Get current book configuration
config = get_config()

# Configuration
output_dir = Path("./audio")
output_dir.mkdir(exist_ok=True)

START_CHAPTER = 1
END_CHAPTER = None

# CRITICAL: High concurrency (>10 workers) can cause Edge TTS API to truncate audio files
# Symptoms: Audio files are small (< 2 MB) despite containing full chapter text
# Safe values: 4-8 workers on most systems, 10-12 on high-end systems
# If you experience truncated audio, reduce AUDIO_CONCURRENCY in config.py to 4-6
CONCURRENCY_LIMIT = AUDIO_CONCURRENCY

VOICE = config["voice"]
SPEECH_RATE = config["speech_rate"]


async def generate_audio(text: str, chapter: str, retries: int = MAX_RETRIES) -> bool:
    """Generate audio with retry logic"""
    output_file = output_dir / f"ch_{chapter}.mp3"

    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=VOICE,
                rate=SPEECH_RATE,
            )
            await communicate.save(str(output_file))
            print(f"✓ Chapter {chapter} finished -> {output_file.name}")
            return True
                
        except Exception as e:
            print(f"✗ Chapter {chapter} error (attempt {attempt + 1}/{retries}): {e}")
        
        if attempt < retries - 1:
            backoff = 2 ** attempt
            await asyncio.sleep(backoff)
    
    print(f"✗✗ Chapter {chapter} FAILED after {retries} attempts")
    return False


async def worker(worker_id: int, queue: asyncio.Queue):
    """Worker that processes chapters from the queue"""
    while True:
        item = await queue.get()
        
        if item is None:
            queue.task_done()
            break
        
        chapter_file = item
        chapter_num = chapter_file.stem.replace("ch_", "")
        
        try:
            print(f"Starting Chapter {chapter_num}...")
            
            with open(chapter_file, 'r', encoding='utf-8') as file:
                text = file.read()
            
            await generate_audio(text, chapter_num)
            
        except Exception as e:
            print(f"✗ Error processing {chapter_file.name}: {e}")
        finally:
            queue.task_done()


async def main():
    chapters_dir = Path("./chapters")
    
    all_chapter_files = sorted(chapters_dir.glob("ch_*.txt"))
    
    if not all_chapter_files:
        print(f"No chapter files found in {chapters_dir}/")
        return
    
    chapter_files = []
    for chapter_file in all_chapter_files:
        chapter_num = int(chapter_file.stem.replace("ch_", ""))
        
        if chapter_num < START_CHAPTER:
            continue
        if END_CHAPTER is not None and chapter_num > END_CHAPTER:
            continue
        
        output_file = output_dir / f"ch_{chapter_num}.mp3"
        if output_file.exists():
            print(f"Skipping Chapter {chapter_num} (audio already exists)")
            continue
        
        chapter_files.append(chapter_file)
    
    if not chapter_files:
        print(f"No chapters to process in range {START_CHAPTER}-{END_CHAPTER or 'end'}")
        print(f"All chapters in this range already have audio files.")
        return
    
    print(f"Found {len(all_chapter_files)} total chapter(s)")
    print(f"Processing range: {START_CHAPTER} to {END_CHAPTER or 'end'}")
    print(f"Chapters to process: {len(chapter_files)}")
    print(f"Starting with {CONCURRENCY_LIMIT} workers...\n")
    
    queue = asyncio.Queue()
    
    workers = [
        asyncio.create_task(worker(i, queue))
        for i in range(CONCURRENCY_LIMIT)
    ]
    
    for chapter_file in chapter_files:
        await queue.put(chapter_file)
    
    await queue.join()
    
    for _ in workers:
        await queue.put(None)
    
    await asyncio.gather(*workers)
    
    print("\nAll chapters processed!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        raise