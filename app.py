import os
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from functools import wraps
import yt_dlp
from openai import OpenAI
import requests
from io import BytesIO

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

logging.basicConfig(level=logging.INFO)

# Get the API key from environment variable
api_key = 'CCC'
if not api_key:
    raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")

client = OpenAI(api_key=api_key)

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

def summarize(text):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes text into 5-10 concise bullet points suitable for an infographic."},
                {"role": "user", "content": f"Summarize the following text into 5-10 bullet points suitable for an infographic:\n\n{text}"}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content.strip().split('\n')
    except Exception as e:
        logging.error(f"Error summarizing text: {str(e)}")
        raise

def generate_infographic(bullet_points):
    prompt = "Create an infographic with the following bullet points:\n" + "\n".join(bullet_points)
    try:
        response = client.images.generate(
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
    
    base_output_file = "temp_audio"
    
    try:
        logging.info(f"Downloading audio from {youtube_url}")
        actual_output_file = download_youtube_audio(youtube_url, base_output_file)
        
        logging.info(f"Transcribing audio from {actual_output_file}")
        transcription = transcribe_audio(actual_output_file)
        
        logging.info("Summarizing transcription")
        summary = summarize(transcription)
        
        return jsonify({"summary": summary})
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up any potential leftover files
        for file in [f"{base_output_file}", f"{base_output_file}.mp3"]:
            if os.path.exists(file):
                os.remove(file)
                logging.info(f"Removed temporary file: {file}")

@app.route('/create-infographic', methods=['POST'])
@require_auth
def create_infographic():
    data = request.json
    logging.info(f"Received data: {data}")
    
    bullet_points = data.get('summary')
    
    if not bullet_points:
        logging.error("No summary bullet points provided")
        return jsonify({"error": "No summary bullet points provided"}), 400
    
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

@app.route('/download-mp3', methods=['POST'])
@require_auth
def download_mp3():
    data = request.json
    youtube_url = data.get('url')
    
    if not youtube_url:
        return jsonify({"error": "No URL provided"}), 400
    
    try:
        logging.info(f"Downloading audio from {youtube_url}")
        output_file = "temp_audio"
        mp3_file = download_youtube_audio(youtube_url, output_file)
        
        return send_file(mp3_file, mimetype="audio/mpeg", as_attachment=True, download_name="youtube_audio.mp3")
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(mp3_file):
            os.remove(mp3_file)
            logging.info(f"Removed temporary file: {mp3_file}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)