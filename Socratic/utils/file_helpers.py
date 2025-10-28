import tempfile
import os
def _save_temp_file(uploaded_file):
    """Save uploaded file to temporary location"""
    print(f"Saving temporary file for: {uploaded_file.name}")
    # mkstemp returns (fd, path) - we need the path
    fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(uploaded_file.name)[1])
    print(f"Temporary file path: {temp_path}")
    
    try:
        # Write the uploaded file content to the temp file
        with open(temp_path, 'wb') as temp_file:
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
    finally:
        # Close the file descriptor to avoid resource leaks
        os.close(fd)
    
    return temp_path
    
def _cleanup_temp_file(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        print(f"Error cleaning up temp file {file_path}: {e}")