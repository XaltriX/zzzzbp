import os
import asyncio
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatMemberStatus
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ChatJoinRequest
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, RPCError
from pymongo import MongoClient
from config import ADMINS, FORCE_MSG, START_MSG, CUSTOM_CAPTION, DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT, DB_URI as MONGO_URL, DB_NAME
from helper_func import subscribed, encode, decode, get_messages
from database.database import add_user, del_user, full_userbase, present_user

START_COMMAND_LIMIT = 2 # set limit here 

# MongoDB setup
mongo_client = MongoClient(MONGO_URL)
db = mongo_client[DB_NAME]
users_collection = db['ushhhers']
join_requests_collection = db['join_requests']

FORCE_SUB_CHANNELS = [
    {"channel_id": -1002164052003, "join_link": 'https://t.me/+VVqMdLKfPxU1OGE1', "name": "Channel 1"},
    {"channel_id": -1002226784896, "join_link": 'https://t.me/+GmQLgQf7AlkyODc1', "name": "Channel 2"},
    {"channel_id": -1002172195934, "join_link": 'https://t.me/+FN4QvVUxXdk4ODU1', "name": "Channel 3"}
]

force_sub_channel_ids = [channel["channel_id"] for channel in FORCE_SUB_CHANNELS]

async def check_subscription_status(client: Client, user_id: int):
    for channel in FORCE_SUB_CHANNELS:
        channel_id = channel["channel_id"]
        try:
            member_status = await client.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member_status.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return False, channel
        except RPCError:
            pass

        existing_request = join_requests_collection.find_one({"user_id": user_id, "channel_id": channel_id})
        if not existing_request:
            return False, channel

    return True, None

async def check_join_request_status(user_id: int, channel_id: int):
    return join_requests_collection.find_one({"user_id": user_id, "channel_id": channel_id}) is not None

async def increment_start_count(user_id: int):
    user_data = users_collection.find_one({"user_id": user_id})
    if not user_data:
        users_collection.insert_one({"user_id": user_id, "start_count": 1})
    else:
        start_count = user_data.get("start_count", 0) + 1
        users_collection.update_one({"user_id": user_id}, {"$set": {"start_count": start_count}})
        return start_count

async def get_start_count(user_id: int):
    user_data = users_collection.find_one({"user_id": user_id})
    return user_data.get("start_count", 0) if user_data else 0

"""
async def get_current_channel(user_id: int):
    start_count = await get_start_count(user_id)
    required_count = START_COMMAND_LIMIT * len(FORCE_SUB_CHANNELS)
    if start_count < required_count:
        channel_index = start_count // START_COMMAND_LIMIT
        if channel_index < len(FORCE_SUB_CHANNELS):
            return FORCE_SUB_CHANNELS[channel_index]
    return None

"""

async def get_current_channel(user_id: int):
    user_data = users_collection.find_one({"user_id": user_id})
    current_channel_index = user_data.get("current_channel_index", 0) if user_data else 0
    
    if current_channel_index < len(FORCE_SUB_CHANNELS):
        return FORCE_SUB_CHANNELS[current_channel_index]
    
    return None

@Client.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    user_data = users_collection.find_one({"user_id": user_id})

    if not user_data:
        users_collection.insert_one({"user_id": user_id, "start_count": 0, "current_channel_index": 0})

    current_channel = await get_current_channel(user_id)
    start_count = await get_start_count(user_id)

    if current_channel:
        if not await check_join_request_status(user_id, current_channel["channel_id"]):
            await client.send_message(
                chat_id=user_id,
                text=f"To continue using the bot, please join the required channel: {current_channel['name']}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"Join {current_channel['name']}", url=current_channel["join_link"])]
                ])
            )
            return
        else:
            # Move to the next channel after user joins the current one
            users_collection.update_one(
                {"user_id": user_id},
                {"$inc": {"current_channel_index": 1}, "$set": {"start_count": 0}}
            )

   # await client.send_message(chat_id=user_id, text="Welcome! You have access to the bot.")
    await increment_start_count(user_id)

    if len(message.text) > 7:
        try:
            base64_string = message.text.split(" ", 1)[1]
            string = await decode(base64_string)
            argument = string.split("-")
            ids = range(int(argument[1]) // abs(client.db_channel.id), (int(argument[2]) // abs(client.db_channel.id)) + 1) if len(argument) == 3 else [int(int(argument[1]) / abs(client.db_channel.id))]
        except (IndexError, ValueError):
            return

        temp_msg = await message.reply("Please wait...")
        try:
            messages = await get_messages(client, ids)
        except Exception:
            await message.reply_text("Something went wrong!")
            return
        await temp_msg.delete()

        for msg in messages:
            caption = (CUSTOM_CAPTION.format(previouscaption="" if not msg.caption else msg.caption.html, filename=msg.document.file_name)
                       if CUSTOM_CAPTION and msg.document else (msg.caption.html if msg.caption else ""))

            try:
                await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=None if DISABLE_CHANNEL_BUTTON else msg.reply_markup, protect_content=PROTECT_CONTENT)
                await asyncio.sleep(0.5)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=None if DISABLE_CHANNEL_BUTTON else msg.reply_markup, protect_content=PROTECT_CONTENT)
            except Exception:
                pass
        return

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("😊 About Me", callback_data="about"), InlineKeyboardButton("🔒 Close", callback_data="close")]
    ])
    await message.reply_text(
        text=START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=f'@{message.from_user.username}' if message.from_user.username else None,
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=reply_markup,
        disable_web_page_preview=True,
        quote=True
    )

    
@Client.on_message(filters.command("limit"))
async def check_limit(client, message):
    user_id = message.from_user.id
    start_count = await get_start_count(user_id)
    current_channel = await get_current_channel(user_id)
    remaining_uses = START_COMMAND_LIMIT - (start_count % START_COMMAND_LIMIT)
    channel_link = current_channel["join_link"] if current_channel else "No channel"
    await client.send_message(
        chat_id=user_id,
        text=f"You have {remaining_uses} /start command uses remaining for the current channel: {channel_link}."
    )

@Client.on_chat_join_request(filters.chat(force_sub_channel_ids))
async def handle_join_request(client: Client, chat_join_request: ChatJoinRequest):
    user_id = chat_join_request.from_user.id
    channel_id = chat_join_request.chat.id

    try:
        member_status = await client.get_chat_member(chat_id=channel_id, user_id=user_id)
        if member_status.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            await client.send_message(chat_id=user_id, text="You are already a member of the channel.")
            return
    except RPCError as e:
        print(f"Error checking member status: {e}")
        pass
        
    existing_request = join_requests_collection.find_one({"user_id": user_id, "channel_id": channel_id})
    if not existing_request:
        join_requests_collection.insert_one({
            "user_id": user_id,
            "channel_id": channel_id,
            "timestamp": chat_join_request.date
        })

    await client.send_message(chat_id=user_id, text="Your join request is received. You can now use the bot.")

@Client.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Client, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text="Please wait...")
    users = await full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")

@Client.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: Client, message: Message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total, successful, blocked, deleted, unsuccessful = 0, 0, 0, 0, 0
        
        pls_wait = await message.reply("<i>Broadcasting Message.. This will Take Some Time</i>")
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
                del_user(chat_id)
            except InputUserDeactivated:
                deleted += 1
                del_user(chat_id)
            except Exception:
                unsuccessful += 1
            total += 1
        
        status = f"<b>Broadcast Completed:</b>\n\nTotal: {total} users\nSuccessful: {successful} users\nBlocked: {blocked} users\nDeleted: {deleted} users\nUnsuccessful: {unsuccessful} users"
        await pls_wait.delete()
        await message.reply_text(status, quote=True, parse_mode=ParseMode.HTML)
    else:
        await message.reply_text("Reply to a message to broadcast to all users.")

@Client.on_message(filters.private & filters.command(['status']) & filters.user(ADMINS))
async def bot_stats(client: Client, message: Message):
    total_users = len(await full_userbase())
    await message.reply_text(f"Bot Status:\n\nPython-Pyrogram: v{__version__}\nTotal Users: {total_users}")

@Client.on_message(filters.private & filters.command("info"))
async def get_userinfo(client: Client, message: Message):
    try:
        if len(message.command) > 1:
            # If a user ID or username is provided as an argument
            user_id = message.command[1]
            user = await client.get_users(user_id)
        else:
            # If no argument is provided, get the info of the user who sent the command
            user = await client.get_users(message.from_user.id)

        await message.reply_text(f"User Info:\n\nID: <code>{user.id}</code>\nName: {user.first_name}\nUsername: {user.username}\nDC ID: {user.dc_id}\nProfile Link: {user.mention}")
    except Exception:
        await message.reply_text("No user found.")
        
