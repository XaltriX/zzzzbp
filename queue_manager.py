# Queue Management System for Force Join - FIXED VERSION
import asyncio
from datetime import datetime
from typing import Optional
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from database.database import (
    get_user_session, update_user_state, get_queue_position,
    remove_from_queue, get_queue_message, set_queue_message,
    get_active_users_count, get_next_in_queue, add_to_queue,
    get_channel_settings, clear_user_session
)
from config import COUNTDOWN_UPDATE_INTERVAL, LOGGER

logger = LOGGER(__name__)

# Global queue processor task
queue_processor_task = None

# ==========================================
# QUEUE COUNTDOWN FUNCTIONS
# ==========================================

async def start_countdown(client: Client, user_id: int, chat_id: int):
    """Start countdown for user in queue with live updates"""
    try:
        # Send initial countdown message
        msg = await client.send_message(
            chat_id=chat_id,
            text="⏳ <b>Preparing your access...</b>\n\n"
                 "Please wait while we process your request...",
            parse_mode=ParseMode.HTML
        )
        
        await set_queue_message(user_id, msg.id)
        
        # Update countdown every N seconds
        while True:
            session = await get_user_session(user_id)
            
            # Check if user is still in queue
            if not session or session['state'] != 'IN_QUEUE':
                break
            
            position = await get_queue_position(user_id)
            
            if position == 0:
                # User removed from queue
                break
            
            # Estimate wait time (position * 30 seconds average)
            estimated_time = max((position - 1) * 30, 0)
            minutes = estimated_time // 60
            seconds = estimated_time % 60
            
            # Create engaging progress bar
            if position == 1:
                progress_bar = "🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢"
                status_emoji = "🎯"
                status_text = "Almost your turn!"
            elif position <= 3:
                progress_bar = "🟢🟢🟢🟢🟢🟢🟢⚪⚪⚪"
                status_emoji = "⚡"
                status_text = "Get ready!"
            elif position <= 5:
                progress_bar = "🟢🟢🟢🟢🟢⚪⚪⚪⚪⚪"
                status_emoji = "⏳"
                status_text = "Moving forward..."
            else:
                progress_bar = "🟢🟢🟢⚪⚪⚪⚪⚪⚪⚪"
                status_emoji = "⏰"
                status_text = "Please wait..."
            
            time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
            
            countdown_text = (
                f"⏳ <b>Queue Status</b> {status_emoji}\n\n"
                f"{progress_bar}\n\n"
                f"📍 Your Position: <b>#{position}</b>\n"
                f"⏱ Estimated Wait: <b>{time_str}</b>\n"
                f"💬 Status: <i>{status_text}</i>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔔 <b>Stay connected!</b> You'll be notified when it's your turn.\n"
                f"⚡ <b>Tip:</b> Don't close this chat to avoid losing your spot!"
            )
            
            try:
                await msg.edit_text(countdown_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.warning(f"Failed to update countdown for {user_id}: {e}")
                break
            
            await asyncio.sleep(COUNTDOWN_UPDATE_INTERVAL)
    
    except Exception as e:
        logger.error(f"Countdown error for user {user_id}: {e}")

# ==========================================
# QUEUE PROCESSOR (BACKGROUND TASK)
# ==========================================

async def process_queue(client: Client):
    """Background task to process queue"""
    logger.info("Queue processor started")
    
    while True:
        try:
            settings = await get_channel_settings()
            max_active = settings.get('max_active_users', 1)
            
            # Count current active users
            active_count = await get_active_users_count()
            
            # If slots available, activate next user
            if active_count < max_active:
                next_user_id = await get_next_in_queue()
                
                if next_user_id:
                    await activate_user(client, next_user_id)
            
            await asyncio.sleep(2)  # Check every 2 seconds
        
        except Exception as e:
            logger.error(f"Queue processor error: {e}")
            await asyncio.sleep(5)

async def activate_user(client: Client, user_id: int):
    """Activate user's turn and show join buttons"""
    try:
        session = await get_user_session(user_id)
        if not session:
            return
        
        # Update state to ACTIVE
        await update_user_state(user_id, 'ACTIVE')
        await remove_from_queue(user_id)
        
        # Get queue message ID
        msg_id = await get_queue_message(user_id)
        
        if msg_id:
            # Edit countdown message to show it's user's turn
            try:
                await client.edit_message_text(
                    chat_id=user_id,
                    message_id=msg_id,
                    text="🟢 <b>Your turn has started!</b>\n\n"
                         "Please join the channels below by clicking the buttons.\n"
                         "After joining, verification will happen automatically.",
                    parse_mode=ParseMode.HTML
                )
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"Failed to edit queue message: {e}")
        
        # Now show join buttons
        from config import FORCE_SUB_CHANNELS
        from database.database import get_channel_settings
        
        settings = await get_channel_settings()
        channels_count = settings.get('channels_per_request', 2)
        
        # Get unused channel set
        from database.database import get_unused_channel_set, set_user_channel_set
        channel_set = await get_unused_channel_set(user_id, FORCE_SUB_CHANNELS, channels_count)
        
        if not channel_set:
            await client.send_message(
                chat_id=user_id,
                text="❌ No available channel combinations. Please contact admin."
            )
            await clear_user_session(user_id)
            return
        
        # Save channel set
        await set_user_channel_set(user_id, channel_set)
        
        # Create join buttons
        buttons = []
        for ch_id in channel_set:
            channel = next((c for c in FORCE_SUB_CHANNELS if c['channel_id'] == ch_id), None)
            if channel:
                buttons.append([
                    InlineKeyboardButton(
                        f"📢 Join {channel['name']}", 
                        url=channel['join_link']
                    )
                ])
        
        buttons.append([
            InlineKeyboardButton("✅ I Joined All", callback_data=f"verify_join_{user_id}")
        ])
        
        await client.send_message(
            chat_id=user_id,
            text="🔐 <b>Join Required Channels</b>\n\n"
                 "Click the buttons below to join all required channels.\n"
                 "After joining all, click 'I Joined All' button.\n\n"
                 "⚠️ You must actually REQUEST TO JOIN (not just click)!",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"Activated user {user_id} with channels: {channel_set}")
    
    except Exception as e:
        logger.error(f"Error activating user {user_id}: {e}")

# ==========================================
# QUEUE MANAGEMENT FUNCTIONS
# ==========================================

async def add_user_to_queue(client: Client, user_id: int):
    """Add user to queue and start countdown"""
    position = await add_to_queue(user_id)
    await update_user_state(user_id, 'IN_QUEUE')
    
    # Start countdown in background
    asyncio.create_task(start_countdown(client, user_id, user_id))
    
    return position

async def start_queue_processor(client: Client):
    """Start the queue processor background task"""
    global queue_processor_task
    
    if queue_processor_task is None or queue_processor_task.done():
        queue_processor_task = asyncio.create_task(process_queue(client))
        logger.info("Queue processor task started")

# ==========================================
# USER STATE CHECKS
# ==========================================

async def is_user_busy(user_id: int) -> tuple[bool, Optional[str]]:
    """Check if user is already in process"""
    session = await get_user_session(user_id)
    
    if not session:
        return False, None
    
    state = session.get('state', 'IDLE')
    
    if state in ['IN_QUEUE', 'ACTIVE', 'WAITING_VERIFICATION', 'SOFT_WAIT']:
        messages = {
            'IN_QUEUE': '⚠️ You are already in queue. Please wait for your turn.',
            'ACTIVE': '⚠️ Your verification is already in progress. Please complete it first.',
            'WAITING_VERIFICATION': '⚠️ Please wait, we are verifying your join requests...',
            'SOFT_WAIT': '⏳ Please wait a moment before requesting another file.'
        }
        return True, messages.get(state, '⚠️ You are already in process.')
    
    return False, None

# Import needed for queue_size
async def get_queue_size():
    """Get current queue size"""
    from database.database import get_queue_size as db_get_queue_size
    return await db_get_queue_size()
