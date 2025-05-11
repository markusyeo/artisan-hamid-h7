def ab2ascii(data):
    return ''.join(chr(byte) for byte in data)

def ascii2ab(s):
    return s.encode('ascii')

class RateLimiter:
    
    def __init__(self):
        self.last_command_time = 0
        self.min_command_interval = 1.0
    
    async def wait_for_rate_limit(self):
        import time
        import asyncio
        
        current_time = time.time()
        time_since_last_command = current_time - self.last_command_time
        
        if time_since_last_command < self.min_command_interval:
            wait_time = self.min_command_interval - time_since_last_command
            await asyncio.sleep(wait_time)
        
        self.last_command_time = time.time()
        
def is_valid_response(data):
    if not data:
        return False
    
    try:
        decoded = ab2ascii(data)
        if (decoded.startswith('[') and decoded.endswith(']') and 
            ',' in decoded and 
            len(decoded.split(',')) >= 3):
            return True
    except:
        pass
    
    return False

