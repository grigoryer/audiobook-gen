#!/usr/bin/env python3
"""
EPUB Chapter Splitter
Extracts chapters from an EPUB file and saves them as individual text files.
Each file is named ch_{number}.txt and contains "Chapter {number}, {title}" at the top.
Cleans promotional/footer text from chapters.

Usage:
  python3 epub_chapter_splitter.py [output_directory]
  
  EPUB file is read from config.py - no need to specify it
"""

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re
import os
import sys
from config import get_config


def extract_chapter_number(title):
    """
    Extract chapter number from title string.
    Handles formats like: "Chapter 5", "Chapter Five", "5. Title", etc.
    """
    match = re.search(r'chapter\s+(\d+)', title, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    match = re.search(r'^(\d+)', title.strip())
    if match:
        return int(match.group(1))
    
    return None


def clean_title(title):
    """
    Extract the chapter title, removing 'Chapter X' prefix if present.
    """
    cleaned = re.sub(r'^chapter\s+\d+\s*:?\s*', '', title, flags=re.IGNORECASE)
    return cleaned.strip()


def remove_promotional_text(text):
    """
    Remove promotional/footer text from chapters.
    """
    patterns_to_remove = [
        r'\*\*\*\s*Discord:.*?Remove Ads From \$\d+',
        r'Discord:\s*https://dsc\.gg/\w+',
        r'Link to donations in the discord!',
        r'Enhance your reading experience.*?Remove Ads From \$\d+',
        r'Remove Ads From \$\d+',
    ]
    
    cleaned_text = text
    for pattern in patterns_to_remove:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE | re.DOTALL)
    
    cleaned_text = re.sub(r'\n\s*\*\*\*\s*\n', '\n', cleaned_text)
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
    
    return cleaned_text.strip()


def html_to_text(html_content):
    """
    Convert HTML content to plain text.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for script in soup(["script", "style"]):
        script.decompose()
    
    text = soup.get_text()
    
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text


def split_epub_by_chapters(epub_path, output_dir="chapters"):
    """
    Main function to split EPUB into chapter text files.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading EPUB: {epub_path}")
    book = epub.read_epub(epub_path)
    
    toc = book.toc
    
    if not toc:
        print("Warning: No table of contents found. Attempting to use spine...")
        process_from_spine(book, output_dir)
        return
    
    print(f"Found {len(toc)} items in table of contents")
    
    chapter_count = 0
    for item in toc:
        items_to_process = [item] if not isinstance(item, tuple) else flatten_toc(item)
        
        for toc_item in items_to_process:
            if not hasattr(toc_item, 'title') or not hasattr(toc_item, 'href'):
                continue
                
            title = toc_item.title
            href = toc_item.href
            
            chapter_num = extract_chapter_number(title)
            
            if chapter_num is None:
                print(f"Skipping: {title} (no chapter number found)")
                continue
            
            chapter_title = clean_title(title)
            clean_href = href.split('#')[0]
            
            try:
                item_content = book.get_item_with_href(clean_href)
                if item_content is None:
                    print(f"Warning: Could not find content for {clean_href}")
                    continue
                
                html_content = item_content.get_content().decode('utf-8')
                text_content = html_to_text(html_content)
                text_content = remove_promotional_text(text_content)
                
                output_filename = f"ch_{chapter_num}.txt"
                output_path = os.path.join(output_dir, output_filename)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"Chapter {chapter_num}, {chapter_title}\n\n")
                    f.write(text_content)
                
                print(f"✓ Created: {output_filename} - Chapter {chapter_num}, {chapter_title}")
                chapter_count += 1
                
            except Exception as e:
                print(f"Error processing {title}: {e}")
                continue
    
    print(f"\nDone! Extracted {chapter_count} chapters to '{output_dir}' directory")


def flatten_toc(toc_item):
    """
    Flatten nested TOC structure.
    """
    items = []
    if isinstance(toc_item, tuple):
        items.append(toc_item[0])
        for sub_item in toc_item[1]:
            items.extend(flatten_toc(sub_item))
    else:
        items.append(toc_item)
    return items


def process_from_spine(book, output_dir):
    """
    Fallback: process chapters from spine when TOC is not available.
    """
    print("Processing from spine...")
    chapter_num = 1
    
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        html_content = item.get_content().decode('utf-8')
        text_content = html_to_text(html_content)
        text_content = remove_promotional_text(text_content)
        
        if len(text_content.strip()) < 100:
            continue
        
        output_filename = f"ch_{chapter_num}.txt"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Chapter {chapter_num}\n\n")
            f.write(text_content)
        
        print(f"✓ Created: {output_filename}")
        chapter_num += 1


if __name__ == "__main__":
    # Get EPUB file from config
    config = get_config()
    epub_file = config["epub_file"]
    
    # Output directory can be specified or defaults to "chapters"
    output_directory = sys.argv[1] if len(sys.argv) > 1 else "chapters"
    
    if not os.path.exists(epub_file):
        print(f"Error: EPUB file '{epub_file}' not found")
        print(f"Make sure the file specified in config.py exists")
        sys.exit(1)
    
    split_epub_by_chapters(epub_file, output_directory)
