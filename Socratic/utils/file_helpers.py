import tempfile
import os

def _save_temp_file(uploaded_file):
    """Save uploaded file to temporary location"""
    print(f"Saving temporary file for: {uploaded_file.name}")
    
    # Use system temp directory (cross-platform: Windows, Linux, Mac)
    temp_dir = tempfile.gettempdir()
    os.makedirs(temp_dir, exist_ok=True)
    
    fd, temp_path = tempfile.mkstemp(
        suffix=os.path.splitext(uploaded_file.name)[1],
        dir=temp_dir
    )
    
    try:
        # Close the file descriptor immediately and use normal file operations
        os.close(fd)
        
        # Write the uploaded file content
        with open(temp_path, 'wb') as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
        
        # Verify file was written
        file_size = os.path.getsize(temp_path)
        print(f"Temp file saved: {temp_path} ({file_size} bytes)")
        
        if file_size == 0:
            raise Exception("Temp file is empty")
        
        return temp_path
            
    except Exception as e:
        # Clean up on error
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise Exception(f"Failed to save temp file: {str(e)}")
    
def _cleanup_temp_file(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        print(f"Error cleaning up temp file {file_path}: {e}")