import os
import asyncio
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatMemberStatus
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ChatJoinRequest, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, RPCError
from config import (
    ADMINS, FORCE_MSG, START_MSG, CUSTOM_CAPTION, 
    DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT, FORCE_SUB_CHANNELS,
    LOGGER, SOFT_WAIT_TIME
)
from helper_func import encode, decode, get_messages
from database.database import (
    add_user, del_user, full_userbase, present_user,
    get_user_session, create_user_session, update_user_state,
    save_join_request, check_all_join_requests, get_file_request,
    set_file_request, clear_user_session, get_channel_settings,
    set_user_channel_set, get_unused_channel_set
)
from queue_manager import (
    add_user_to_queue, is_user_busy, start_queue_processor
)

logger = LOGGER(__name__)

# Extract channel IDs for filter
force_sub_channel_ids = [channel["channel_id"] for channel in FORCE_SUB_CHANNELS]

# ==========================================
# START COMMAND - MODIFIED FOR QUEUE SYSTEM
# ==========================================

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Add user to database if new (FIXED: Now actually adds to DB)
    if not await present_user(user_id):
        await add_user(user_id)
        logger.info(f"New user added: {user_id}")
    
    # Create session if doesn't exist
    session = await get_user_session(user_id)
    if not session:
        await create_user_session(user_id)
    
    # Check if user is already busy
    is_busy, busy_msg = await is_user_busy(user_id)
    if is_busy:
        await message.reply(busy_msg)
        return
    
    # ==========================================
    # FILE REQUEST HANDLING (WITH QUEUE SYSTEM)
    # ==========================================
    
    if len(message.text) > 7:
        try:
            base64_string = message.text.split(" ", 1)[1]
            string = await decode(base64_string)
            argument = string.split("-")
            
            # Parse message IDs
            if len(argument) == 3:
                ids = range(
                    int(argument[1]) // abs(client.db_channel.id),
                    (int(argument[2]) // abs(client.db_channel.id)) + 1
                )
            else:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            
        except (IndexError, ValueError) as e:
            logger.error(f"Invalid file link format: {e}")
            await message.reply("❌ Invalid file link!")
            return
        
        # Store file request data
        await set_file_request(user_id, {
            'message_ids': list(ids),
            'original_message': message.text
        })
        
        # Get settings
        settings = await get_channel_settings()
        queue_enabled = settings.get('queue_enabled', True)
        channels_per_request = settings.get('channels_per_request', 2)
        
        # Get unused channel set
        channel_set = await get_unused_channel_set(
            user_id, 
            FORCE_SUB_CHANNELS, 
            channels_per_request
        )
        
        if not channel_set:
            await message.reply(
                "❌ No available channel combinations left.\n"
                "Please contact admin or try again later."
            )
            return
        
        # Save channel set for this request
        await set_user_channel_set(user_id, channel_set)
        
        # Add to queue or directly activate
        if queue_enabled:
            position = await add_user_to_queue(client, user_id)
            logger.info(f"User {user_id} added to queue at position {position}")
        else:
            # Direct activation (no queue)
            from queue_manager import activate_user
            await activate_user(client, user_id)
        
        return
    
    # ==========================================
    # NORMAL START MESSAGE (NO FILE LINK)
    # ==========================================
    
    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("😊 About Me", callback_data="about"),
            InlineKeyboardButton("🔒 Close", callback_data="close")
        ]
    ])
    
    await message.reply_text(
        text=START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name or "",
            username=f'@{message.from_user.username}' if message.from_user.username else "None",
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=reply_markup,
        disable_web_page_preview=True,
        quote=True
    )

# ==========================================
# JOIN REQUEST HANDLER
# ==========================================

@Client.on_chat_join_request(filters.chat(force_sub_channel_ids))
async def handle_join_request(client: Client, chat_join_request: ChatJoinRequest):
    user_id = chat_join_request.from_user.id
    channel_id = chat_join_request.chat.id
    
    # Save join request
    await save_join_request(user_id, channel_id)
    logger.info(f"Join request saved: user {user_id} -> channel {channel_id}")
    
    # Check user session
    session = await get_user_session(user_id)
    if not session:
        await client.send_message(
            chat_id=user_id,
            text="✅ Join request received!\n\nPlease use /start command to access files."
        )
        return
    
    state = session.get('state')
    current_channels = session.get('current_channel_set', [])
    
    # Only proceed if user is in ACTIVE state and this channel is in their set
    if state == 'ACTIVE' and channel_id in current_channels:
        # Check if all channels joined
        all_joined = await check_all_join_requests(user_id, current_channels)
        
        if all_joined:
            # Update state to waiting verification
            await update_user_state(user_id, 'WAITING_VERIFICATION')
            
            await client.send_message(
                chat_id=user_id,
                text="⏳ <b>Verifying your join requests...</b>\n\nPlease wait a moment...",
                parse_mode=ParseMode.HTML
            )
            
            # Start verification process
            asyncio.create_task(verify_and_send_file(client, user_id))
        else:
            await client.send_message(
                chat_id=user_id,
                text=f"✅ Join request for <b>{chat_join_request.chat.title}</b> received!\n\n"
                     f"Please join the remaining channels.",
                parse_mode=ParseMode.HTML
            )
    else:
        # Generic confirmation
        await client.send_message(
            chat_id=user_id,
            text="✅ Join request received! Thank you for joining."
        )

# ==========================================
# VERIFICATION & FILE SENDING
# ==========================================

async def verify_and_send_file(client: Client, user_id: int):
    """Verify join requests and send file"""
    try:
        # Small delay for Telegram to register join requests
        await asyncio.sleep(3)
        
        session = await get_user_session(user_id)
        if not session:
            return
        
        current_channels = session.get('current_channel_set', [])
        
        # Verify all join requests
        all_verified = await check_all_join_requests(user_id, current_channels)
        
        if not all_verified:
            await client.send_message(
                chat_id=user_id,
                text="❌ <b>Verification failed!</b>\n\n"
                     "Please make sure you've sent join requests to all channels.\n"
                     "Click the buttons again and try once more.",
                parse_mode=ParseMode.HTML
            )
            await update_user_state(user_id, 'ACTIVE')
            return
        
        # Update state
        await update_user_state(user_id, 'VERIFIED')
        
        await client.send_message(
            chat_id=user_id,
            text="✅ <b>Verified successfully!</b>\n\nSending your file(s)...",
            parse_mode=ParseMode.HTML
        )
        
        # Get file request data
        file_data = await get_file_request(user_id)
        
        if not file_data:
            await client.send_message(
                chat_id=user_id,
                text="❌ File request data not found. Please try again."
            )
            await clear_user_session(user_id)
            return
        
        message_ids = file_data.get('message_ids', [])
        
        # Fetch and send files
        try:
            messages = await get_messages(client, message_ids)
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            await client.send_message(
                chat_id=user_id,
                text="❌ Failed to fetch file(s). Please contact admin."
            )
            await clear_user_session(user_id)
            return
        
        # Send each file
        for msg in messages:
            if not msg:
                continue
            
            caption = ""
            if CUSTOM_CAPTION and msg.document:
                caption = CUSTOM_CAPTION.format(
                    previouscaption="" if not msg.caption else msg.caption.html,
                    filename=msg.document.file_name
                )
            elif msg.caption:
                caption = msg.caption.html
            
            try:
                await msg.copy(
                    chat_id=user_id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=None if DISABLE_CHANNEL_BUTTON else msg.reply_markup,
                    protect_content=PROTECT_CONTENT
                )
                await asyncio.sleep(0.5)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await msg.copy(
                    chat_id=user_id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=None if DISABLE_CHANNEL_BUTTON else msg.reply_markup,
                    protect_content=PROTECT_CONTENT
                )
            except Exception as e:
                logger.error(f"Error sending file: {e}")
        
        # Update state to FILE_SENT
        await update_user_state(user_id, 'FILE_SENT')
        
        await client.send_message(
            chat_id=user_id,
            text="✅ <b>File(s) sent successfully!</b>\n\n"
                 "Thank you for using our service. 😊",
            parse_mode=ParseMode.HTML
        )
        
        # Start soft wait period
        await update_user_state(user_id, 'SOFT_WAIT')
        await asyncio.sleep(SOFT_WAIT_TIME)
        
        # Clear session after soft wait
        await clear_user_session(user_id)
        logger.info(f"Session cleared for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in verify_and_send_file: {e}")
        await clear_user_session(user_id)

# Part 2 of start.py - ADD THIS TO THE END OF PART 1

# ==========================================
# CALLBACK QUERY HANDLERS
# ==========================================

@Client.on_callback_query(filters.regex("^verify_join_"))
async def verify_join_callback(client: Client, callback_query: CallbackQuery):
    """Handle 'I Joined All' button click"""
    user_id = callback_query.from_user.id
    
    session = await get_user_session(user_id)
    if not session or session.get('state') != 'ACTIVE':
        await callback_query.answer(
            "⚠️ This verification is expired or invalid.",
            show_alert=True
        )
        return
    
    current_channels = session.get('current_channel_set', [])
    
    # Import here to avoid circular import
    from database.database import check_join_request
    
    # Check if all join requests submitted
    all_joined = await check_all_join_requests(user_id, current_channels)
    
    if not all_joined:
        # Find which channels are missing
        missing = []
        for ch_id in current_channels:
            if not await check_join_request(user_id, ch_id):
                channel = next((c for c in FORCE_SUB_CHANNELS if c['channel_id'] == ch_id), None)
                if channel:
                    missing.append(channel['name'])
        
        await callback_query.answer(
            f"⚠️ Please send join requests to: {', '.join(missing)}",
            show_alert=True
        )
        return
    
    # All joined - start verification
    await callback_query.answer("✅ Verifying...", show_alert=False)
    
    await callback_query.message.edit_text(
        "⏳ <b>Verifying your join requests...</b>\n\nPlease wait...",
        parse_mode=ParseMode.HTML
    )
    
    await update_user_state(user_id, 'WAITING_VERIFICATION')
    asyncio.create_task(verify_and_send_file(client, user_id))

@Client.on_callback_query(filters.regex("^about$"))
async def about_callback(client: Client, callback_query: CallbackQuery):
    """About button handler"""
    about_text = (
        "<b>📚 About This Bot</b>\n\n"
        f"<b>📦 Bot Name:</b> File Sharing Bot\n"
        f"<b>🔖 Version:</b> 2.0 (Queue System)\n"
        f"<b>🐍 Pyrogram:</b> v{__version__}\n"
        f"<b>💾 Database:</b> MongoDB\n\n"
        "<b>⚡️ Features:</b>\n"
        "• Smart Queue System\n"
        "• Rotating Channel Sets\n"
        "• Anti-Flood Protection\n"
        "• Secure File Sharing\n\n"
        "<b>👨‍💻 Owner:</b> @NeonGhost_Network"
    )
    
    await callback_query.message.edit_text(
        text=about_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="start_back")]
        ])
    )

@Client.on_callback_query(filters.regex("^start_back$"))
async def start_back_callback(client: Client, callback_query: CallbackQuery):
    """Back to start message"""
    user = callback_query.from_user
    
    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("😊 About Me", callback_data="about"),
            InlineKeyboardButton("🔒 Close", callback_data="close")
        ]
    ])
    
    await callback_query.message.edit_text(
        text=START_MSG.format(
            first=user.first_name,
            last=user.last_name or "",
            username=f'@{user.username}' if user.username else "None",
            mention=user.mention,
            id=user.id
        ),
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

@Client.on_callback_query(filters.regex("^close$"))
async def close_callback(client: Client, callback_query: CallbackQuery):
    """Close button handler"""
    await callback_query.message.delete()

# ==========================================
# ADMIN COMMANDS - USER MANAGEMENT
# ==========================================

@Client.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Client, message: Message):
    """Show total users - FIXED"""
    msg = await client.send_message(chat_id=message.chat.id, text="📊 Fetching user data...")
    
    try:
        users = await full_userbase()
        await msg.edit(
            f"<b>📊 Bot Statistics</b>\n\n"
            f"👥 Total Users: <b>{len(users)}</b>\n"
            f"📅 Checked at: {message.date}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await msg.edit(f"❌ Error fetching users: {str(e)}")

@Client.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: Client, message: Message):
    """Broadcast message to all users - FIXED"""
    if not message.reply_to_message:
        await message.reply_text(
            "❌ Please reply to a message to broadcast it to all users.\n\n"
            "<b>Usage:</b> Reply to any message with /broadcast",
            parse_mode=ParseMode.HTML
        )
        return
    
    query = await full_userbase()
    broadcast_msg = message.reply_to_message
    total, successful, blocked, deleted, unsuccessful = 0, 0, 0, 0, 0
    
    pls_wait = await message.reply(
        "<b>📢 Broadcasting Message...</b>\n\n"
        "This will take some time. Please wait...",
        parse_mode=ParseMode.HTML
    )
    
    for chat_id in query:
        try:
            await broadcast_msg.copy(chat_id)
            successful += 1
        except FloodWait as e:
            await asyncio.sleep(e.x)
            await broadcast_msg.copy(chat_id)
            successful += 1
        except UserIsBlocked:
            blocked += 1
            await del_user(chat_id)
        except InputUserDeactivated:
            deleted += 1
            await del_user(chat_id)
        except Exception as e:
            unsuccessful += 1
            logger.error(f"Broadcast error for {chat_id}: {e}")
        
        total += 1
        
        # Update progress every 50 users
        if total % 50 == 0:
            try:
                await pls_wait.edit_text(
                    f"<b>📢 Broadcasting...</b>\n\n"
                    f"Progress: {total}/{len(query)} users\n"
                    f"✅ Successful: {successful}\n"
                    f"❌ Failed: {unsuccessful}",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
    
    status = (
        f"<b>📢 Broadcast Completed!</b>\n\n"
        f"<b>📊 Statistics:</b>\n"
        f"👥 Total: <b>{total}</b> users\n"
        f"✅ Successful: <b>{successful}</b>\n"
        f"🚫 Blocked: <b>{blocked}</b>\n"
        f"❌ Deleted: <b>{deleted}</b>\n"
        f"⚠️ Failed: <b>{unsuccessful}</b>"
    )
    
    await pls_wait.delete()
    await message.reply_text(status, quote=True, parse_mode=ParseMode.HTML)

@Client.on_message(filters.private & filters.command(['status']) & filters.user(ADMINS))
async def bot_stats(client: Client, message: Message):
    """Bot status and statistics"""
    total_users = len(await full_userbase())
    
    from queue_manager import get_queue_size, get_active_users_count
    queue_size = await get_queue_size()
    active_users = await get_active_users_count()
    
    # Calculate uptime
    from datetime import datetime
    if hasattr(client, 'uptime'):
        uptime = datetime.now() - client.uptime
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
    else:
        uptime_str = "Unknown"
    
    status_text = (
        f"<b>🤖 Bot Status</b>\n\n"
        f"<b>📊 Statistics:</b>\n"
        f"👥 Total Users: <b>{total_users}</b>\n"
        f"⏳ In Queue: <b>{queue_size}</b>\n"
        f"🟢 Active: <b>{active_users}</b>\n\n"
        f"<b>⚙️ System:</b>\n"
        f"🐍 Pyrogram: v{__version__}\n"
        f"⏰ Uptime: <b>{uptime_str}</b>\n"
        f"💾 Database: MongoDB\n\n"
        f"<b>✅ Status:</b> Running smoothly!"
    )
    
    await message.reply_text(status_text, parse_mode=ParseMode.HTML)

@Client.on_message(filters.private & filters.command("info"))
async def get_userinfo(client: Client, message: Message):
    """Get user information"""
    try:
        if len(message.command) > 1:
            user_id = message.command[1]
            user = await client.get_users(user_id)
        else:
            user = await client.get_users(message.from_user.id)
        
        # Get user session info
        session = await get_user_session(user.id)
        state = session.get('state', 'Unknown') if session else 'No session'
        
        info_text = (
            f"<b>👤 User Information</b>\n\n"
            f"<b>ID:</b> <code>{user.id}</code>\n"
            f"<b>Name:</b> {user.first_name} {user.last_name or ''}\n"
            f"<b>Username:</b> @{user.username or 'None'}\n"
            f"<b>DC ID:</b> {user.dc_id or 'Unknown'}\n"
            f"<b>State:</b> {state}\n"
            f"<b>Profile:</b> {user.mention}"
        )
        
        await message.reply_text(info_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        await message.reply_text(f"❌ User not found or error: {str(e)}")

# ==========================================
# QUEUE STATUS COMMAND (USER)
# ==========================================

@Client.on_message(filters.command("queue") & filters.private)
async def queue_status(client: Client, message: Message):
    """Check queue position and status"""
    user_id = message.from_user.id
    
    session = await get_user_session(user_id)
    if not session:
        await message.reply("You don't have any active session.")
        return
    
    state = session.get('state', 'IDLE')
    
    from queue_manager import get_queue_position, get_queue_size
    
    if state == 'IN_QUEUE':
        position = await get_queue_position(user_id)
        total = await get_queue_size()
        
        await message.reply(
            f"⏳ <b>Queue Status</b>\n\n"
            f"📍 Your Position: <b>#{position}</b>\n"
            f"👥 Total in Queue: <b>{total}</b>\n"
            f"⏱ Estimated wait: <b>{(position-1)*30}s</b>\n\n"
            f"Please wait for your turn! 🔔",
            parse_mode=ParseMode.HTML
        )
    elif state == 'ACTIVE':
        await message.reply(
            "🟢 <b>Your turn is active!</b>\n\n"
            "Please complete the join verification.",
            parse_mode=ParseMode.HTML
        )
    elif state == 'IDLE':
        await message.reply("You are not in queue. Use /start with a file link to begin.")
    else:
        await message.reply(f"Current state: {state}")

# Continue in next part for admin panel...
