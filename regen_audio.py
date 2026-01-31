import asyncio
import edge_tts
from pathlib import Path
from config import get_config, MAX_RETRIES

# Get current book configuration
config = get_config()

# Configuration
output_dir = Path("./audio")
output_dir.mkdir(exist_ok=True)

CHAPTER_LIST_FILE = "chapters_to_regenerate.txt"

# CRITICAL: High concurrency (>10 workers) can cause Edge TTS API to truncate audio files
# When regenerating failed chapters, use LOWER concurrency to prevent re-truncation
# Recommended: 4 workers for regeneration to ensure full audio completion
CONCURRENCY_LIMIT = 4

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
    
    if not Path(CHAPTER_LIST_FILE).exists():
        print(f"✗ {CHAPTER_LIST_FILE} not found!")
        print(f"Create a text file with one chapter number per line:")
        print(f"Example content:")
        print(f"126")
        print(f"127")
        print(f"120")
        return
    
    with open(CHAPTER_LIST_FILE, 'r') as f:
        chapter_numbers = [line.strip() for line in f if line.strip()]
    
    if not chapter_numbers:
        print(f"✗ No chapter numbers found in {CHAPTER_LIST_FILE}")
        return
    
    print(f"Found {len(chapter_numbers)} chapter(s) to regenerate")
    print(f"Chapters: {', '.join(chapter_numbers)}")
    print(f"Starting with {CONCURRENCY_LIMIT} workers...\n")
    
    chapter_files = []
    for ch_num in chapter_numbers:
        chapter_file = chapters_dir / f"ch_{ch_num}.txt"
        if chapter_file.exists():
            chapter_files.append(chapter_file)
        else:
            print(f"Warning: {chapter_file.name} not found in chapters/")
    
    if not chapter_files:
        print("✗ No valid chapter files found!")
        return
    
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
    
    print("\n✓ All chapters processed!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        raise