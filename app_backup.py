import os
import logging
from flask import Flask, request, jsonify
import yt_dlp
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Get the API key from environment variable
api_key = 'AAA'
if not api_key:
    raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")

client = OpenAI(api_key=api_key)

def download_youtube_audio(url, output_path):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_path,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        # Return the actual filename (which might have changed due to extraction)
        return f"{output_path}.mp3"
    except Exception as e:
        logging.error(f"Error downloading audio: {str(e)}")
        raise

def transcribe_audio(file_path):
    try:
        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcription
    except Exception as e:
        logging.error(f"Error transcribing audio: {str(e)}")
        raise

@app.route('/transcribe', methods=['POST'])
def transcribe_youtube():
    data = request.json
    youtube_url = data.get('url')
    
    if not youtube_url:
        return jsonify({"error": "No URL provided"}), 400
    
    base_output_file = "temp_audio"
    
    try:
        logging.info(f"Downloading audio from {youtube_url}")
        actual_output_file = download_youtube_audio(youtube_url, base_output_file)
        
        logging.info(f"Transcribing audio from {actual_output_file}")
        transcription = transcribe_audio(actual_output_file)
        
        return jsonify({"transcription": transcription})
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up any potential leftover files
        for file in [f"{base_output_file}", f"{base_output_file}.mp3"]:
            if os.path.exists(file):
                os.remove(file)
                logging.info(f"Removed temporary file: {file}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)