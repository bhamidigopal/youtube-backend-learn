# YouTube Audio Processing and Infographic Generation API

This project provides a Flask-based API that offers three main functionalities:
1. Summarizing YouTube videos into bullet points
2. Creating infographics from bullet points
3. Downloading audio from YouTube videos as MP3 files

## Setup

### Prerequisites
- Docker
- OpenAI API key

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/youtube-audio-infographic-api.git
   cd youtube-audio-infographic-api
   ```

2. Build the Docker image:
   ```
   docker build -t youtube-audio-infographic-api .
   ```

3. Run the Docker container:
   ```
   docker run -p 5000:5000 -e OPENAI_API_KEY=your_actual_api_key youtube-audio-infographic-api
   ```

The API will now be available at `http://localhost:5000`.

## Authentication

All API endpoints require authentication. You need to include the following headers with each request:

```
username: admin
password: KKK
```

## API Endpoints

### 1. Summarize YouTube Video

- **Endpoint**: `/summarize-youtube`
- **Method**: POST
- **Headers**:
  ```
  username: admin
  password: KKK
  Content-Type: application/json
  ```
- **Request Body**:
  ```json
  {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  }
  ```
- **Response**:
  ```json
  {
    "summary": [
      "Bullet point 1",
      "Bullet point 2",
      "Bullet point 3",
      ...
    ]
  }
  ```

### 2. Create Infographic

- **Endpoint**: `/create-infographic`
- **Method**: POST
- **Headers**:
  ```
  username: admin
  password: KKK
  Content-Type: application/json
  ```
- **Request Body**:
  ```json
  {
    "bullet_points": [
      "Point 1: Key information",
      "Point 2: Another important fact",
      "Point 3: Interesting statistic",
      "Point 4: Concluding thought"
    ]
  }
  ```
- **Response**: PNG image file

### 3. Download MP3

- **Endpoint**: `/download-mp3`
- **Method**: POST
- **Headers**:
  ```
  username: admin
  password: KKK
  Content-Type: application/json
  ```
- **Request Body**:
  ```json
  {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  }
  ```
- **Response**: MP3 audio file


### 4. Transcribe YouTube Video

- **Endpoint**: `/transcribe-youtube`
- **Method**: POST
- **Headers**:
  ```
  username: admin
  password: AlekhyaAnu
  Content-Type: application/json
  ```
- **Request Body**:
  ```json
  {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  }
  ```
- **Response**:
  ```json
  {
    "transcription": "Full transcribed text of the YouTube video..."
  }
  ```

## Sample Tests

Here are some curl commands to test each endpoint:

1. Summarize YouTube Video:
   ```bash
   curl -X POST http://localhost:5000/summarize-youtube \
     -H "username: admin" \
     -H "password: KKK" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
   ```

2. Create Infographic:
   ```bash
   curl -X POST http://localhost:5000/create-infographic \
     -H "username: admin" \
     -H "password: KKK" \
     -H "Content-Type: application/json" \
     -d '{
       "bullet_points": [
         "Point 1: Key information",
         "Point 2: Another important fact",
         "Point 3: Interesting statistic",
         "Point 4: Concluding thought"
       ]
     }' \
     --output infographic.png
   ```

3. Download MP3:
   ```bash
   curl -X POST http://localhost:5000/download-mp3 \
     -H "username: admin" \
     -H "password: KKK" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}' \
     --output audio.mp3
   ```

   4. Transcribe YouTube Video:
   ```bash
   curl -X POST http://localhost:5000/transcribe-youtube \
     -H "username: admin" \
     -H "password: XXX" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

## License

This project is licensed under the MIT License.

