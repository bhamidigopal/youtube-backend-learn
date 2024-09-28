import os
import logging
from flask import Flask, request, jsonify, send_file, Response, make_response
from flask_cors import CORS
from functools import wraps
import yt_dlp
from openai import OpenAI
import requests
from io import BytesIO
import base64
import io
import json
import re
import time

from dotenv import load_dotenv
from anthropic import Anthropic
import anthropic

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

# Load environment variables from .env
load_dotenv()

# Get the API keys from environment variables
openai_api_key = os.getenv('OPENAI_API_KEY')
claude_api_key = os.getenv('CLAUDE_API_KEY')

if not openai_api_key:
    raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")
if not claude_api_key:
    raise ValueError("No Claude API key found. Please set the CLAUDE_API_KEY environment variable.")

openai_client = OpenAI(api_key=openai_api_key)
claude_client = anthropic.Anthropic(api_key=claude_api_key)

# Authentication decorator
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        username = request.headers.get('username')
        password = request.headers.get('password')
        if username == 'admin' and password == 'AlekhyaAnu':
            return f(*args, **kwargs)
        return jsonify({"error": "Authentication failed"}), 401
    return decorated

# Add a new function to extract YouTube video ID
def extract_youtube_video_id(url):
    # Regular expression pattern to match YouTube video IDs
    pattern = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

# Modify the download_youtube_audio function
def download_youtube_audio(url, output_dir="temp_audio"):
    video_id = extract_youtube_video_id(url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")
    
    output_path = os.path.join(output_dir, video_id)
    mp3_file = f"{output_path}.mp3"
    metadata_file = os.path.join(output_dir, "metadata.json")
    
    current_time = time.time()
    
    # Load or initialize metadata
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
    else:
        metadata = {}
    
    # Check if the file exists and is not older than 24 hours
    if os.path.exists(mp3_file) and video_id in metadata:
        file_age = current_time - metadata[video_id]['timestamp']
        logging.info(f"File: {mp3_file}")
        logging.info(f"Current time: {current_time}")
        logging.info(f"File timestamp: {metadata[video_id]['timestamp']}")
        logging.info(f"Calculated file age: {file_age:.2f} seconds")
        
        if file_age < 86400:  # 24 hours in seconds
            logging.info(f"Using cached audio file for video ID: {video_id} (age: {file_age:.2f} seconds)")
            return mp3_file
        else:
            logging.info(f"Cached file for video ID: {video_id} is too old (age: {file_age:.2f} seconds). Downloading again.")
            os.remove(mp3_file)
    else:
        logging.info(f"No cached file found for video ID: {video_id}. Downloading.")
    
    # Download logic remains the same
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        logging.info(f"Successfully downloaded and converted audio for video ID: {video_id}")
        
        # Update metadata
        metadata[video_id] = {'timestamp': current_time}
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)
        
        return mp3_file
    except Exception as e:
        logging.error(f"Error downloading audio for video ID {video_id}: {str(e)}")
        raise

def detect_language(text):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a language detection expert. Respond with only the ISO 639-1 two-letter language code."},
                {"role": "user", "content": f"Detect the language of this text:\n\n{text[:100]}"}
            ],
            max_tokens=2
        )
        return response.choices[0].message.content.strip().lower()
    except Exception as e:
        logging.error(f"Error detecting language: {str(e)}")
        raise

def translate_to_english(text):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a highly skilled translator. Translate the following text to English, maintaining the original meaning and tone as closely as possible."},
                {"role": "user", "content": f"Translate this to English:\n\n{text}"}
            ],
            max_tokens=1500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error translating text: {str(e)}")
        raise

def transcribe_audio(file_path):
    try:
        with open(file_path, "rb") as audio_file:
            transcription = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        # Detect the language of the transcription
        detected_language = detect_language(transcription)
        
        if detected_language != 'en':
            logging.info(f"Detected non-English language: {detected_language}. Translating to English.")
            translated_transcription = translate_to_english(transcription)
            return {
                "original_transcription": transcription,
                "detected_language": detected_language,
                "english_translation": translated_transcription
            }
        else:
            return {
                "transcription": transcription,
                "detected_language": "en"
            }
    except Exception as e:
        logging.error(f"Error transcribing audio: {str(e)}")
        raise

def summarize(text):
    try:
        response = claude_client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
             messages=[
        {
            "role": "user",
            "content": f"Summarize this text into 5-10 bullet points fit for an infographic with titles. Make each point clear and concise and capture the most important treasures of information:\n\n{text}"
        }
    ]
           
        )
        summary = response.content[0].text.strip().split('\n')
        # Clean up the bullet points
        summary = [point.strip().lstrip('•-* ') for point in summary if point.strip()]
        return summary
    except Exception as e:
        logging.error(f"Error summarizing text: {str(e)}")
        raise

def generate_infographic(bullet_points):
    prompt = "Create an infographic with the following bullet points:\n" + "\n".join(bullet_points)
    try:
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        
        # Download the image
        image_response = requests.get(image_url)
        image_data = BytesIO(image_response.content)
        
        return image_data
    except Exception as e:
        logging.error(f"Error generating infographic: {str(e)}")
        raise

@app.route('/summarize-youtube', methods=['POST'])
@require_auth
def summarize_youtube():
    data = request.json
    youtube_url = data.get('url')
    
    if not youtube_url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        logging.info(f"Processing audio from {youtube_url}")
        mp3_file = download_youtube_audio(youtube_url)
        
        logging.info(f"Transcribing audio from {mp3_file}")
        transcription = transcribe_audio(mp3_file)
        
        logging.info("Summarizing transcription")
        summary = summarize(transcription)
        
        return jsonify({
            "transcription": transcription,
            "summary": summary
        })
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/infographic-youtube', methods=['POST'])
@require_auth
def infographic_youtube():
    data = request.json
    youtube_url = data.get('url')
    
    if not youtube_url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        logging.info(f"Processing audio from {youtube_url}")
        mp3_file = download_youtube_audio(youtube_url)
        
        logging.info(f"Transcribing audio from {mp3_file}")
        transcription = transcribe_audio(mp3_file)
        
        logging.info("Summarizing transcription")
        summary = summarize(transcription)
        
        logging.info(f"Generating infographic with {len(summary)} summary points")
        image_data = generate_infographic(summary)
        
        return send_file(image_data, mimetype='image/png')
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/create-infographic', methods=['POST'])
@require_auth
def create_infographic():
    data = request.json
    logging.info(f"Received data: {data}")
    
    bullet_points = data.get('summary')
    
    if not bullet_points:
        logging.error("No bullet points provided")
        return jsonify({"error": "No bullet points provided"}), 400
    
    if not isinstance(bullet_points, list):
        logging.error(f"Invalid bullet points format. Expected list, got {type(bullet_points)}")
        return jsonify({"error": "Invalid bullet points format. Expected a list."}), 400
    
    if len(bullet_points) == 0:
        logging.error("Empty list of bullet points provided")
        return jsonify({"error": "Empty list of bullet points provided"}), 400
    
    try:
        logging.info(f"Generating infographic with {len(bullet_points)} bullet points")
        image_data = generate_infographic(bullet_points)
        return send_file(image_data, mimetype='image/png')
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/download-mp3-youtube', methods=['POST'])
@require_auth
def download_mp3():
    data = request.json
    youtube_url = data.get('url')
    
    if not youtube_url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        logging.info(f"Downloading audio from {youtube_url}")
        mp3_file = download_youtube_audio(youtube_url)
        
        return send_file(mp3_file, mimetype="audio/mpeg", as_attachment=True, download_name="youtube_audio.mp3")
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/transcribe-youtube', methods=['POST'])
@require_auth
def transcribe_youtube():
    data = request.json
    youtube_url = data.get('url')
    
    if not youtube_url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        logging.info(f"Processing audio from {youtube_url}")
        mp3_file = download_youtube_audio(youtube_url)
        
        logging.info(f"Transcribing audio from {mp3_file}")
        transcription_result = transcribe_audio(mp3_file)
        
        return jsonify(transcription_result)
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/summarize-text', methods=['POST'])
@require_auth
def summarize_text():
    data = request.json
    text = data.get('text')
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    try:
        # Detect language and translate if necessary
        detected_language = detect_language(text)
        if detected_language != 'en':
            logging.info(f"Detected non-English language: {detected_language}. Translating to English.")
            text = translate_to_english(text)
        
        logging.info("Summarizing provided text")
        summary = summarize(text)
        
        return jsonify({
            "detected_language": detected_language,
            "summary": summary
        })
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/youtube-summary-infographic', methods=['POST'])
@require_auth
def youtube_summary_infographic():
    data = request.json
    youtube_url = data.get('url')
    
    if not youtube_url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        logging.info(f"Processing audio from {youtube_url}")
        mp3_file = download_youtube_audio(youtube_url)
        
        logging.info(f"Transcribing audio from {mp3_file}")
        transcription_result = transcribe_audio(mp3_file)
        
        # Use the English translation if available, otherwise use the original transcription
        text_to_summarize = transcription_result.get("english_translation") or transcription_result.get("transcription")
        
        logging.info("Summarizing transcription")
        summary = summarize(text_to_summarize)
        
        logging.info(f"Generating infographic with {len(summary)} summary points")
        image_data = generate_infographic(summary)
        
        # Prepare the multipart response
        response = make_response()
        response.status_code = 200

        # Add the image part
        response.data = image_data.getvalue()
        response.headers['Content-Type'] = 'image/png'
        
        # Prepare the text data
        text_data = {
            "transcription_result": transcription_result,
            "summary": summary
        }
        
        # Add the JSON data as a custom header
        response.headers['X-JSON-Data'] = json.dumps(text_data)

        return response
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Add a new route for cleaning up old cached files
@app.route('/cleanup-cache', methods=['POST'])
@require_auth
def cleanup_cache():
    try:
        cleanup_count = 0
        current_time = time.time()
        metadata_file = os.path.join("temp_audio", "metadata.json")
        
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            updated_metadata = {}
            for video_id, data in metadata.items():
                file_path = os.path.join("temp_audio", f"{video_id}.mp3")
                file_age = current_time - data['timestamp']
                if file_age > 86400 and os.path.exists(file_path):  # 24 hours in seconds
                    os.remove(file_path)
                    cleanup_count += 1
                    logging.info(f"Removed old cache file: {video_id}.mp3 (age: {file_age:.2f} seconds)")
                else:
                    updated_metadata[video_id] = data
            
            with open(metadata_file, 'w') as f:
                json.dump(updated_metadata, f)
        
        return jsonify({"message": f"Cleaned up {cleanup_count} old cache files"}), 200
    except Exception as e:
        logging.error(f"Error cleaning up cache: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/test-time', methods=['GET'])
def test_time():
    current_time = time.time()
    test_file = os.path.join("temp_audio", "test_file.txt")
    with open(test_file, "w") as f:
        f.write("Test")
    file_mtime = os.path.getmtime(test_file)
    os.remove(test_file)
    return jsonify({
        "current_time": current_time,
        "file_mtime": file_mtime,
        "difference": current_time - file_mtime
    })

if __name__ == "__main__":
    # Ensure the temp_audio directory exists
    os.makedirs("temp_audio", exist_ok=True)
    app.run(host='0.0.0.0', port=5000)