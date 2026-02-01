import tempfile
import os
from django.core.files.storage import default_storage
import uuid

def _save_uploaded_file_to_storage(uploaded_file):
    """
    Save uploaded file to R2 storage instead of temp directory.
    This ensures Celery workers in separate containers can access the file.
    Returns the file path in R2 storage.
    """
    print(f"Saving uploaded file to R2: {uploaded_file.name}")
    
    try:
        # Generate unique filename
        file_extension = os.path.splitext(uploaded_file.name)[1]
        unique_filename = f"uploads/{uuid.uuid4().hex}{file_extension}"
        
        # Save to R2 storage
        file_path = default_storage.save(unique_filename, uploaded_file)
        
        # Verify file was saved
        if not default_storage.exists(file_path):
            raise Exception("File was not saved to storage")
        
        file_size = default_storage.size(file_path)
        print(f"File saved to R2: {file_path} ({file_size} bytes)")
        
        if file_size == 0:
            default_storage.delete(file_path)
            raise Exception("Uploaded file is empty")
        
        return file_path
        
    except Exception as e:
        print(f"Failed to save file to R2: {str(e)}")
        raise Exception(f"Failed to save uploaded file: {str(e)}")

def _cleanup_uploaded_file(file_path):
    """
    Delete uploaded file from R2 storage after processing.
    """
    try:
        if file_path and default_storage.exists(file_path):
            default_storage.delete(file_path)
            print(f"Cleaned up uploaded file: {file_path}")
    except Exception as e:
        print(f"Error cleaning up uploaded file {file_path}: {e}")