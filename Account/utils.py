"""
Utility functions for Account app
"""


def is_student_email(email):

    if not email or '@' not in email:
        return False
    
    email_lower = email.lower()
    domain = email_lower.split('@')[-1]
    
    # Keywords that indicate educational institutions
    student_keywords = [
        'university',
        'college', 
        'school',
        'edu',      # Common in US (.edu domains)
        'ac',       # Academic institutions (.ac.uk, .ac.za, etc.)
        'student',
    ]
    
    # Check if domain contains any student keywords
    return any(keyword in domain for keyword in student_keywords)


def get_email_domain(email):

    if not email or '@' not in email:
        return ''
    
    return email.split('@')[-1].lower()
