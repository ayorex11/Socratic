import os
import sys

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Config.settings')
import django
django.setup()

try:
    from Account.utils import is_student_email, check_fingerprint_limit
    print("Import Successful")
    
    # Test is_student_email
    assert is_student_email("test@university.edu") == True
    assert is_student_email("test@gmail.com") == False
    print("is_student_email logic: PASS")

    # Test fingerprint import (make sure both coexist)
    assert check_fingerprint_limit(None) == True
    print("check_fingerprint_limit import: PASS")

except ImportError as e:
    print(f"Import Failed: {e}")
except Exception as e:
    print(f"Test Failed: {e}")
