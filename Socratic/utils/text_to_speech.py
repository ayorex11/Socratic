from gtts import gTTS
import os
from django.conf import settings
import uuid
import re 

class TextToSpeech:
    """
    Handles conversion of text to speech using gTTS (free)
    Generates MP3 files for audio summaries
    """
    
    @staticmethod
    def generate_audio(text, filename_prefix="audio"):
        """
        Generate audio file from text using gTTS
        Returns the file path relative to MEDIA_ROOT
        """
        try:
            if not text or len(text.strip()) < 10:
                print("Text too short for audio generation")
                return None
            
            clean_text = TextToSpeech._prepare_text_for_tts(text)
            
            if len(clean_text) < 10:
                print("Text too short after cleaning")
                return None
            
            audio_dir = os.path.join(settings.MEDIA_ROOT, 'audio_summaries')
            os.makedirs(audio_dir, exist_ok=True)
            
            unique_id = uuid.uuid4().hex[:8]
            filename = f"{filename_prefix}_{unique_id}.mp3"
            file_path = os.path.join(audio_dir, filename)
            
            print(f"Generating audio for text length: {len(clean_text)} characters")
            
            tts = gTTS(
                text=clean_text, 
                lang='en', 
                slow=False, 
                lang_check=False
            )
            
            tts.save(file_path)
            
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                print(f"Audio file generated successfully: {filename}")
                return f"audio_summaries/{filename}"
            else:
                print("Audio file creation failed")
                return None
            
        except Exception as e:
            print(f"Audio generation failed: {str(e)}")
            return None
    
    @staticmethod
    def _prepare_text_for_tts(text):
        """
        Clean and prepare text for better TTS results by removing markdown/formatting noise.
        """
        if not text:
            return ""
        
        clean_text = text.strip()
        
        # 1. Remove Markdown Headings and Separators (e.g., #, ##, ---, list bullets like *)
        # This removes lines starting with one or more hashes, hyphens, or asterisks followed by a space
        clean_text = re.sub(r'^[#\-*]+\s*', '', clean_text, flags=re.MULTILINE)
        clean_text = re.sub(r'\s*---+\s*', ' ', clean_text)
        
        # 2. Remove Emphasis Markers (e.g., **bold**, *italic*)
        clean_text = re.sub(r'[\*\_]{1,2}', '', clean_text)
        
        # 3. Collapse excessive whitespace
        clean_text = re.sub(r'\s{2,}', ' ', clean_text).strip()
        
        # 4. Limit text length (5000 is safe)
        max_length = 5000 
        if len(clean_text) > max_length:
            # Cut text at a sentence break if possible for a smoother end
            clean_text = clean_text[:max_length].rsplit('.', 1)[0] + "." 
        
        # 5. Ensure the text ends with a proper sentence
        if not clean_text.endswith(('.', '!', '?')):
            clean_text += '.'
        
        return clean_text
    
    @staticmethod
    def generate_audio_chunked(text, filename_prefix="audio", max_chunk_length=1000):
        """
        Generate audio for long texts by chunking (if needed)
        """
        try:
            if len(text) <= max_chunk_length:
                return TextToSpeech.generate_audio(text, filename_prefix)
            
            sentences = TextToSpeech._split_into_sentences(text)
            chunks = []
            current_chunk = ""
            
            for sentence in sentences:
                if len(current_chunk) + len(sentence) <= max_chunk_length:
                    current_chunk += " " + sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            audio_files = []
            for i, chunk in enumerate(chunks):
                if chunk.strip():
                    audio_path = TextToSpeech.generate_audio(
                        chunk, 
                        f"{filename_prefix}_part{i+1}"
                    )
                    if audio_path:
                        audio_files.append(audio_path)
            
            return audio_files[0] if audio_files else None
            
        except Exception as e:
            print(f"Chunked audio generation failed: {str(e)}")
            return None
    
    @staticmethod
    def _split_into_sentences(text):
        """
        Simple sentence splitting for chunking
        """
        import re
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]