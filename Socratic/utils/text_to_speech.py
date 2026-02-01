from gtts import gTTS
from django.conf import settings
import uuid
import re 
from django.core.files.storage import default_storage
from io import BytesIO
from pydub import AudioSegment
import tempfile
import os

class TextToSpeech:
    """
    Handles conversion of text to speech using gTTS (free)
    Generates MP3 files for audio summaries directly to R2
    IMPROVED: Better chunking and concatenation for long content
    """
    
    @staticmethod
    def generate_audio(text, filename_prefix="audio"):
        """
        Generate audio file from text using gTTS
        Returns the file path in R2 storage
        IMPROVED: Increased character limit from 5000 to 15000
        """
        try:
            if not text or len(text.strip()) < 10:
                print("Text too short for audio generation")
                return None
            
            clean_text = TextToSpeech._prepare_text_for_tts(text)
            
            if len(clean_text) < 10:
                print("Text too short after cleaning")
                return None
            
            unique_id = uuid.uuid4().hex[:8]
            filename = f"audio/{filename_prefix}_{unique_id}.mp3"  # Goes to 'media/audio/' in R2
            
            print(f"Generating audio for text length: {len(clean_text)} characters")
            
            tts = gTTS(
                text=clean_text, 
                lang='en', 
                slow=False, 
                lang_check=False
            )
            
            # Save to in-memory buffer
            buffer = BytesIO()
            tts.write_to_fp(buffer)
            buffer.seek(0)
            
            # Save directly to R2 using Django's storage
            file_path = default_storage.save(filename, buffer)
            
            print(f"Audio file generated successfully: {file_path}")
            return file_path  # Returns path in R2
            
        except Exception as e:
            print(f"Audio generation failed: {str(e)}")
            return None
    
    @staticmethod
    def _prepare_text_for_tts(text):
        """
        Clean and prepare text for better TTS results by removing markdown/formatting noise.
        IMPROVED: Increased limit from 5000 to 15000 characters
        """
        if not text:
            return ""
        
        clean_text = text.strip()
        
        # 1. Remove Markdown Headings and Separators
        clean_text = re.sub(r'^[#\-*]+\s*', '', clean_text, flags=re.MULTILINE)
        clean_text = re.sub(r'\s*---+\s*', ' ', clean_text)
        
        # 2. Remove Emphasis Markers
        clean_text = re.sub(r'[\*\_]{1,2}', '', clean_text)
        
        # 3. Collapse excessive whitespace
        clean_text = re.sub(r'\s{2,}', ' ', clean_text).strip()
        
        # 4. IMPROVED: Increased limit from 5000 to 15000
        max_length = 15000 
        if len(clean_text) > max_length:
            clean_text = clean_text[:max_length].rsplit('.', 1)[0] + "." 
        
        # 5. Ensure the text ends with a proper sentence
        if not clean_text.endswith(('.', '!', '?')):
            clean_text += '.'
        
        return clean_text
    
    @staticmethod
    def generate_audio_chunked(text, filename_prefix="audio", max_chunk_length=4000):
        """
        Generate audio for long texts by chunking and concatenating
        IMPROVED: Now properly concatenates all chunks into a single audio file
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
            
            print(f"Generating {len(chunks)} audio chunks for concatenation")
            
            # Generate audio for each chunk and concatenate
            temp_files = []
            combined_audio = None
            
            try:
                for i, chunk in enumerate(chunks):
                    if chunk.strip():
                        # Generate TTS for chunk
                        tts = gTTS(
                            text=TextToSpeech._prepare_text_for_tts(chunk), 
                            lang='en', 
                            slow=False, 
                            lang_check=False
                        )
                        
                        # Save to temporary file
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                        tts.write_to_fp(temp_file)
                        temp_file.close()
                        temp_files.append(temp_file.name)
                        
                        # Load and concatenate
                        audio_segment = AudioSegment.from_mp3(temp_file.name)
                        if combined_audio is None:
                            combined_audio = audio_segment
                        else:
                            # Add small pause between chunks (500ms)
                            silence = AudioSegment.silent(duration=500)
                            combined_audio = combined_audio + silence + audio_segment
                
                if combined_audio:
                    # Export combined audio to buffer
                    buffer = BytesIO()
                    combined_audio.export(buffer, format='mp3')
                    buffer.seek(0)
                    
                    # Save to R2
                    unique_id = uuid.uuid4().hex[:8]
                    filename = f"audio/{filename_prefix}_{unique_id}_full.mp3"
                    file_path = default_storage.save(filename, buffer)
                    
                    print(f"Combined audio file generated successfully: {file_path}")
                    return file_path
                else:
                    return None
                    
            finally:
                # Clean up temporary files
                for temp_file in temp_files:
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
            
        except Exception as e:
            print(f"Chunked audio generation failed: {str(e)}")
            # Fallback to single chunk
            return TextToSpeech.generate_audio(text[:15000], filename_prefix)
    
    @staticmethod
    def _split_into_sentences(text):
        """
        Simple sentence splitting for chunking
        """
        import re
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    @staticmethod
    def generate_audio_smart(text, filename_prefix="audio"):
        """
        Smart audio generation that automatically chooses between single and chunked
        based on text length
        """
        # Clean text first
        clean_text = TextToSpeech._prepare_text_for_tts(text)
        
        # If text is short enough, use single generation
        if len(clean_text) <= 15000:
            return TextToSpeech.generate_audio(text, filename_prefix)
        else:
            # Use chunked generation with concatenation
            return TextToSpeech.generate_audio_chunked(text, filename_prefix)