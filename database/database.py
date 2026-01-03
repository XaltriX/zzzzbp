#(©)CodeXBotz - Extended for Queue & Force Join System
import pymongo
from datetime import datetime
from typing import Optional, List, Dict
from config import DB_URI, DB_NAME

dbclient = pymongo.MongoClient(DB_URI)
database = dbclient[DB_NAME]

# Collections
user_data = database['users']
user_sessions = database['user_sessions']
queue_collection = database['queue']
channel_settings = database['channel_settings']

# ==========================================
# USER MANAGEMENT (ORIGINAL + FIXED)
# ==========================================

async def present_user(user_id: int):
    """Check if user exists in database"""
    found = user_data.find_one({'_id': user_id})
    return bool(found)

async def add_user(user_id: int):
    """Add new user to database"""
    if not await present_user(user_id):
        user_data.insert_one({
            '_id': user_id,
            'joined_at': datetime.now()
        })
    return

async def full_userbase():
    """Get all user IDs - FIXED to return actual count"""
    user_docs = user_data.find()
    user_ids = []
    for doc in user_docs:
        user_ids.append(doc['_id'])
    return user_ids

async def del_user(user_id: int):
    """Delete user from database"""
    user_data.delete_one({'_id': user_id})
    return

# ==========================================
# USER SESSION MANAGEMENT (NEW)
# ==========================================

async def get_user_session(user_id: int) -> Optional[Dict]:
    """Get user's current session state"""
    return user_sessions.find_one({'user_id': user_id})

async def create_user_session(user_id: int):
    """Create new user session"""
    session = {
        'user_id': user_id,
        'state': 'IDLE',
        'used_channel_sets': [],
        'current_channel_set': None,
        'last_activity': datetime.now(),
        'queue_message_id': None,
        'file_request': None
    }
    user_sessions.update_one(
        {'user_id': user_id},
        {'$set': session},
        upsert=True
    )
    return session

async def update_user_state(user_id: int, state: str):
    """Update user's state"""
    user_sessions.update_one(
        {'user_id': user_id},
        {
            '$set': {
                'state': state,
                'last_activity': datetime.now()
            }
        },
        upsert=True
    )

async def set_user_channel_set(user_id: int, channel_set: List[int]):
    """Set current channel set for user and mark as used"""
    session = await get_user_session(user_id)
    if not session:
        await create_user_session(user_id)
        session = await get_user_session(user_id)
    
    # Convert to tuple for storage (hashable)
    channel_set_tuple = tuple(sorted(channel_set))
    
    user_sessions.update_one(
        {'user_id': user_id},
        {
            '$set': {
                'current_channel_set': list(channel_set_tuple),
                'last_activity': datetime.now()
            },
            '$addToSet': {
                'used_channel_sets': list(channel_set_tuple)
            }
        }
    )

async def get_unused_channel_set(user_id: int, available_channels: List[Dict], count: int) -> Optional[List[int]]:
    """Get a channel set that user hasn't used before"""
    from itertools import combinations
    
    session = await get_user_session(user_id)
    if not session:
        await create_user_session(user_id)
        session = await get_user_session(user_id)
    
    used_sets = [tuple(sorted(s)) for s in session.get('used_channel_sets', [])]
    
    # Get enabled channel IDs
    enabled_channels = [ch['channel_id'] for ch in available_channels if ch.get('enabled', True)]
    
    if len(enabled_channels) < count:
        return None
    
    # Generate all possible combinations
    all_combinations = list(combinations(enabled_channels, count))
    
    # Find first unused combination
    for combo in all_combinations:
        if combo not in used_sets:
            return list(combo)
    
    # If all combinations used, reset and return first one
    user_sessions.update_one(
        {'user_id': user_id},
        {'$set': {'used_channel_sets': []}}
    )
    return list(all_combinations[0]) if all_combinations else None

async def set_queue_message(user_id: int, message_id: int):
    """Store queue countdown message ID"""
    user_sessions.update_one(
        {'user_id': user_id},
        {'$set': {'queue_message_id': message_id}}
    )

async def get_queue_message(user_id: int) -> Optional[int]:
    """Get queue countdown message ID"""
    session = await get_user_session(user_id)
    return session.get('queue_message_id') if session else None

async def set_file_request(user_id: int, file_data: Dict):
    """Store file request data"""
    user_sessions.update_one(
        {'user_id': user_id},
        {'$set': {'file_request': file_data}}
    )

async def get_file_request(user_id: int) -> Optional[Dict]:
    """Get stored file request data"""
    session = await get_user_session(user_id)
    return session.get('file_request') if session else None

async def clear_user_session(user_id: int):
    """Clear user session (keep used_channel_sets)"""
    session = await get_user_session(user_id)
    if session:
        user_sessions.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'state': 'IDLE',
                    'current_channel_set': None,
                    'queue_message_id': None,
                    'file_request': None,
                    'last_activity': datetime.now()
                }
            }
        )

# ==========================================
# QUEUE MANAGEMENT (NEW)
# ==========================================

async def add_to_queue(user_id: int):
    """Add user to queue"""
    # Check if already in queue
    existing = queue_collection.find_one({'user_id': user_id})
    if existing:
        return existing['position']
    
    # Get current max position
    max_position = 0
    last_user = queue_collection.find_one(sort=[('position', pymongo.DESCENDING)])
    if last_user:
        max_position = last_user['position']
    
    position = max_position + 1
    queue_collection.insert_one({
        'user_id': user_id,
        'position': position,
        'entered_at': datetime.now()
    })
    
    return position

async def remove_from_queue(user_id: int):
    """Remove user from queue"""
    queue_collection.delete_one({'user_id': user_id})

async def get_queue_position(user_id: int) -> int:
    """Get user's position in queue (1-indexed)"""
    queue_entry = queue_collection.find_one({'user_id': user_id})
    if not queue_entry:
        return 0
    
    # Count users with lower position (earlier in queue)
    position = queue_collection.count_documents({
        'position': {'$lt': queue_entry['position']}
    }) + 1
    
    return position

async def get_active_users_count() -> int:
    """Count users currently in ACTIVE or WAITING_VERIFICATION state"""
    return user_sessions.count_documents({
        'state': {'$in': ['ACTIVE', 'WAITING_VERIFICATION']}
    })

async def get_next_in_queue() -> Optional[int]:
    """Get next user ID from queue"""
    next_user = queue_collection.find_one(sort=[('position', pymongo.ASCENDING)])
    return next_user['user_id'] if next_user else None

async def get_queue_size() -> int:
    """Get total queue size"""
    return queue_collection.count_documents({})

# ==========================================
# CHANNEL SETTINGS MANAGEMENT (NEW)
# ==========================================

async def get_channel_settings() -> Dict:
    """Get current channel settings"""
    settings = channel_settings.find_one({'_id': 'settings'})
    if not settings:
        # Create default settings
        default = {
            '_id': 'settings',
            'max_active_users': 1,
            'channels_per_request': 2,
            'countdown_interval': 3,
            'soft_wait_time': 20,
            'queue_enabled': True
        }
        channel_settings.insert_one(default)
        return default
    return settings

async def update_channel_setting(key: str, value):
    """Update a specific channel setting"""
    channel_settings.update_one(
        {'_id': 'settings'},
        {'$set': {key: value}},
        upsert=True
    )

async def get_all_channels() -> List[Dict]:
    """Get all channels from settings (for admin management)"""
    channels = channel_settings.find({'type': 'channel'})
    return list(channels)

async def add_channel(channel_id: int, join_link: str, name: str):
    """Add new channel to database"""
    channel_settings.insert_one({
        'type': 'channel',
        'channel_id': channel_id,
        'join_link': join_link,
        'name': name,
        'enabled': True,
        'added_at': datetime.now()
    })

async def remove_channel(channel_id: int):
    """Remove channel from database"""
    channel_settings.delete_one({
        'type': 'channel',
        'channel_id': channel_id
    })

async def toggle_channel(channel_id: int, enabled: bool):
    """Enable/disable a channel"""
    channel_settings.update_one(
        {'type': 'channel', 'channel_id': channel_id},
        {'$set': {'enabled': enabled}}
    )

# ==========================================
# JOIN REQUEST TRACKING (EXISTING - KEPT)
# ==========================================

async def save_join_request(user_id: int, channel_id: int):
    """Save join request to database"""
    join_requests = database['join_requests']
    existing = join_requests.find_one({
        'user_id': user_id,
        'channel_id': channel_id
    })
    
    if not existing:
        join_requests.insert_one({
            'user_id': user_id,
            'channel_id': channel_id,
            'timestamp': datetime.now()
        })

async def check_join_request(user_id: int, channel_id: int) -> bool:
    """Check if user has submitted join request"""
    join_requests = database['join_requests']
    return join_requests.find_one({
        'user_id': user_id,
        'channel_id': channel_id
    }) is not None

async def check_all_join_requests(user_id: int, channel_ids: List[int]) -> bool:
    """Check if user has submitted join requests for all channels"""
    for channel_id in channel_ids:
        if not await check_join_request(user_id, channel_id):
            return False
    return True
