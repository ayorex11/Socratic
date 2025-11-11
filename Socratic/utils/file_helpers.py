import tempfile
import os

def _save_temp_file(uploaded_file):
    """Save uploaded file to temporary location"""
    print(f"Saving temporary file for: {uploaded_file.name}")
    
    # Use /tmp explicitly (more reliable on ephemeral systems)
    temp_dir = '/tmp'
    os.makedirs(temp_dir, exist_ok=True)
    
    fd, temp_path = tempfile.mkstemp(
        suffix=os.path.splitext(uploaded_file.name)[1],
        dir=temp_dir
    )
    print(f"Temporary file path: {temp_path}")
    
    try:
        with open(temp_path, 'wb') as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
        
        # Verify file was written
        file_size = os.path.getsize(temp_path)
        print(f"Temp file size: {file_size} bytes")
        
        if file_size == 0:
            raise Exception("Temp file is empty")
            
    except Exception as e:
        os.close(fd)
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise Exception(f"Failed to save temp file: {str(e)}")
    finally:
        os.close(fd)
    
    return temp_path
    
def _cleanup_temp_file(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        print(f"Error cleaning up temp file {file_path}: {e}")