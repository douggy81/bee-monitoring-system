#!/usr/bin/env python3
"""
Extract livestream URL from explore.org bee cam.
The site uses an embedded player, so we need to extract the actual video stream URL.
"""
import re
import requests
from bs4 import BeautifulSoup

def extract_stream_url(page_url="https://explore.org/livecams/player/honey-bees/honey-bee-landing-zone-cam"):
    """
    Extract the actual video stream URL from explore.org page.
    
    Returns:
        str: Direct stream URL (M3U8 or MP4)
    """
    print(f"Fetching page: {page_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    response = requests.get(page_url, headers=headers)
    response.raise_for_status()
    
    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Method 1: Look for iframe with player
    iframe = soup.find('iframe', {'id': 'player'}) or soup.find('iframe', class_=re.compile('player|video'))
    if iframe:
        iframe_src = iframe.get('src')
        print(f"Found iframe: {iframe_src}")
        
        # Fetch iframe content
        if iframe_src:
            if not iframe_src.startswith('http'):
                iframe_src = 'https://explore.org' + iframe_src
            
            iframe_response = requests.get(iframe_src, headers=headers)
            iframe_soup = BeautifulSoup(iframe_response.text, 'html.parser')
    
    # Method 2: Look for .m3u8 URLs in page source (HLS streams)
    m3u8_pattern = r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*'
    m3u8_matches = re.findall(m3u8_pattern, response.text)
    
    if m3u8_matches:
        print(f"\nFound {len(m3u8_matches)} HLS stream(s):")
        for i, url in enumerate(m3u8_matches, 1):
            print(f"  {i}. {url}")
        return m3u8_matches[0]
    
    # Method 3: Look for MP4 or other video URLs
    video_pattern = r'https?://[^\s"\'<>]+\.(?:mp4|flv|webm)[^\s"\'<>]*'
    video_matches = re.findall(video_pattern, response.text)
    
    if video_matches:
        print(f"\nFound {len(video_matches)} video URL(s):")
        for i, url in enumerate(video_matches, 1):
            print(f"  {i}. {url}")
        return video_matches[0]
    
    # Method 4: Look for source tags
    sources = soup.find_all('source')
    for source in sources:
        src = source.get('src')
        if src and ('m3u8' in src or 'mp4' in src):
            print(f"\nFound source tag: {src}")
            return src
    
    print("\n❌ Could not find stream URL automatically")
    print("Page may use dynamic loading or require authentication")
    
    # Save page for manual inspection
    with open('/tmp/explore_page.html', 'w') as f:
        f.write(response.text)
    print("Saved page to /tmp/explore_page.html for manual inspection")
    
    return None

if __name__ == '__main__':
    stream_url = extract_stream_url()
    
    if stream_url:
        print(f"\n✓ Stream URL: {stream_url}")
        print(f"\nTest with:")
        print(f"  ffplay '{stream_url}'")
        print(f"  vlc '{stream_url}'")
    else:
        print("\nManual alternatives:")
        print("1. Use youtube-dl/yt-dlp to extract stream")
        print("2. Use browser dev tools to capture network requests")
        print("3. Try alternative bee cam URLs:")
        print("   - https://youtu.be/your_fallback_stream")
