import uuid
from datetime import datetime

def generate_session_id():
    return str(uuid.uuid4())

def get_current_timestamp():
    return datetime.now().isoformat()