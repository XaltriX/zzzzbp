# Admin Panel with Inline Controls (NO REDEPLOY NEEDED)
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from config import ADMINS, FORCE_SUB_CHANNELS, LOGGER
from database.database import (
    get_channel_settings, update_channel_setting,
    add_channel, remove_channel, toggle_channel
)

logger = LOGGER(__name__)

# ==========================================
# ADMIN PANEL MAIN COMMAND
# ==========================================

@Client.on_message(filters.command("admin") & filters.user(ADMINS) & filters.private)
async def admin_panel(client: Client, message: Message):
    """Main admin panel with inline buttons"""
    
    settings = await get_channel_settings()
    
    panel_text = (
        "<b>🔧 Admin Control Panel</b>\n\n"
        "<b>⚙️ Current Settings:</b>\n"
        f"🟢 Max Active Users: <b>{settings.get('max_active_users', 1)}</b>\n"
        f"📢 Channels Per Request: <b>{settings.get('channels_per_request', 2)}</b>\n"
        f"⏱ Countdown Interval: <b>{settings.get('countdown_interval', 3)}s</b>\n"
        f"⏳ Soft Wait Time: <b>{settings.get('soft_wait_time', 20)}s</b>\n"
        f"🎯 Queue System: <b>{'✅ Enabled' if settings.get('queue_enabled', True) else '❌ Disabled'}</b>\n\n"
        "<b>📋 Available Channels:</b>\n"
    )
    
    # Add channel list
    for i, ch in enumerate(FORCE_SUB_CHANNELS, 1):
        status = "✅" if ch.get('enabled', True) else "❌"
        panel_text += f"{i}. {status} {ch['name']} (<code>{ch['channel_id']}</code>)\n"
    
    panel_text += "\n<b>Select an action below:</b>"
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👥 Set Max Active", callback_data="admin_max_active"),
            InlineKeyboardButton("📢 Channels/Request", callback_data="admin_channels_per")
        ],
        [
            InlineKeyboardButton("⏱ Countdown Speed", callback_data="admin_countdown"),
            InlineKeyboardButton("⏳ Soft Wait", callback_data="admin_soft_wait")
        ],
        [
            InlineKeyboardButton("🎯 Toggle Queue", callback_data="admin_toggle_queue"),
            InlineKeyboardButton("📋 Manage Channels", callback_data="admin_manage_channels")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh"),
            InlineKeyboardButton("❌ Close", callback_data="admin_close")
        ]
    ])
    
    await message.reply_text(
        panel_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

# ==========================================
# CALLBACK HANDLERS
# ==========================================

@Client.on_callback_query(filters.regex("^admin_refresh$") & filters.user(ADMINS))
async def admin_refresh(client: Client, callback_query: CallbackQuery):
    """Refresh admin panel"""
    settings = await get_channel_settings()
    
    panel_text = (
        "<b>🔧 Admin Control Panel</b>\n\n"
        "<b>⚙️ Current Settings:</b>\n"
        f"🟢 Max Active Users: <b>{settings.get('max_active_users', 1)}</b>\n"
        f"📢 Channels Per Request: <b>{settings.get('channels_per_request', 2)}</b>\n"
        f"⏱ Countdown Interval: <b>{settings.get('countdown_interval', 3)}s</b>\n"
        f"⏳ Soft Wait Time: <b>{settings.get('soft_wait_time', 20)}s</b>\n"
        f"🎯 Queue System: <b>{'✅ Enabled' if settings.get('queue_enabled', True) else '❌ Disabled'}</b>\n\n"
        "<b>📋 Available Channels:</b>\n"
    )
    
    for i, ch in enumerate(FORCE_SUB_CHANNELS, 1):
        status = "✅" if ch.get('enabled', True) else "❌"
        panel_text += f"{i}. {status} {ch['name']} (<code>{ch['channel_id']}</code>)\n"
    
    panel_text += "\n<b>Select an action below:</b>"
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👥 Set Max Active", callback_data="admin_max_active"),
            InlineKeyboardButton("📢 Channels/Request", callback_data="admin_channels_per")
        ],
        [
            InlineKeyboardButton("⏱ Countdown Speed", callback_data="admin_countdown"),
            InlineKeyboardButton("⏳ Soft Wait", callback_data="admin_soft_wait")
        ],
        [
            InlineKeyboardButton("🎯 Toggle Queue", callback_data="admin_toggle_queue"),
            InlineKeyboardButton("📋 Manage Channels", callback_data="admin_manage_channels")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh"),
            InlineKeyboardButton("❌ Close", callback_data="admin_close")
        ]
    ])
    
    await callback_query.message.edit_text(
        panel_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )
    await callback_query.answer("✅ Refreshed!")

@Client.on_callback_query(filters.regex("^admin_max_active$") & filters.user(ADMINS))
async def set_max_active(client: Client, callback_query: CallbackQuery):
    """Set max active users"""
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1 User", callback_data="setmax_1"),
            InlineKeyboardButton("2 Users", callback_data="setmax_2"),
            InlineKeyboardButton("3 Users", callback_data="setmax_3")
        ],
        [
            InlineKeyboardButton("5 Users", callback_data="setmax_5"),
            InlineKeyboardButton("10 Users", callback_data="setmax_10")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_refresh")]
    ])
    
    await callback_query.message.edit_text(
        "<b>👥 Set Maximum Active Users</b>\n\n"
        "Select how many users can verify simultaneously:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.regex("^setmax_") & filters.user(ADMINS))
async def apply_max_active(client: Client, callback_query: CallbackQuery):
    """Apply max active setting"""
    value = int(callback_query.data.split("_")[1])
    await update_channel_setting('max_active_users', value)
    
    await callback_query.answer(f"✅ Max active users set to {value}!", show_alert=True)
    
    # Refresh panel
    await admin_refresh(client, callback_query)

@Client.on_callback_query(filters.regex("^admin_channels_per$") & filters.user(ADMINS))
async def set_channels_per(client: Client, callback_query: CallbackQuery):
    """Set channels per request"""
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("2 Channels", callback_data="setchan_2"),
            InlineKeyboardButton("3 Channels", callback_data="setchan_3")
        ],
        [
            InlineKeyboardButton("4 Channels", callback_data="setchan_4"),
            InlineKeyboardButton("5 Channels", callback_data="setchan_5")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_refresh")]
    ])
    
    await callback_query.message.edit_text(
        "<b>📢 Set Channels Per Request</b>\n\n"
        "Select how many channels user must join per file:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.regex("^setchan_") & filters.user(ADMINS))
async def apply_channels_per(client: Client, callback_query: CallbackQuery):
    """Apply channels per request setting"""
    value = int(callback_query.data.split("_")[1])
    await update_channel_setting('channels_per_request', value)
    
    await callback_query.answer(f"✅ Channels per request set to {value}!", show_alert=True)
    await admin_refresh(client, callback_query)

@Client.on_callback_query(filters.regex("^admin_countdown$") & filters.user(ADMINS))
async def set_countdown(client: Client, callback_query: CallbackQuery):
    """Set countdown interval"""
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("2 seconds", callback_data="setcount_2"),
            InlineKeyboardButton("3 seconds", callback_data="setcount_3")
        ],
        [
            InlineKeyboardButton("5 seconds", callback_data="setcount_5"),
            InlineKeyboardButton("10 seconds", callback_data="setcount_10")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_refresh")]
    ])
    
    await callback_query.message.edit_text(
        "<b>⏱ Set Countdown Update Interval</b>\n\n"
        "How often should queue countdown update?\n"
        "(Lower = more updates but more API calls)",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.regex("^setcount_") & filters.user(ADMINS))
async def apply_countdown(client: Client, callback_query: CallbackQuery):
    """Apply countdown setting"""
    value = int(callback_query.data.split("_")[1])
    await update_channel_setting('countdown_interval', value)
    
    await callback_query.answer(f"✅ Countdown interval set to {value}s!", show_alert=True)
    await admin_refresh(client, callback_query)

@Client.on_callback_query(filters.regex("^admin_soft_wait$") & filters.user(ADMINS))
async def set_soft_wait(client: Client, callback_query: CallbackQuery):
    """Set soft wait time"""
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("10s", callback_data="setwait_10"),
            InlineKeyboardButton("20s", callback_data="setwait_20")
        ],
        [
            InlineKeyboardButton("30s", callback_data="setwait_30"),
            InlineKeyboardButton("60s", callback_data="setwait_60")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_refresh")]
    ])
    
    await callback_query.message.edit_text(
        "<b>⏳ Set Soft Wait Time</b>\n\n"
        "Time to wait after sending file before allowing next request:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.regex("^setwait_") & filters.user(ADMINS))
async def apply_soft_wait(client: Client, callback_query: CallbackQuery):
    """Apply soft wait setting"""
    value = int(callback_query.data.split("_")[1])
    await update_channel_setting('soft_wait_time', value)
    
    await callback_query.answer(f"✅ Soft wait time set to {value}s!", show_alert=True)
    await admin_refresh(client, callback_query)

@Client.on_callback_query(filters.regex("^admin_toggle_queue$") & filters.user(ADMINS))
async def toggle_queue_system(client: Client, callback_query: CallbackQuery):
    """Toggle queue system on/off"""
    settings = await get_channel_settings()
    current = settings.get('queue_enabled', True)
    new_value = not current
    
    await update_channel_setting('queue_enabled', new_value)
    
    status = "✅ Enabled" if new_value else "❌ Disabled"
    await callback_query.answer(f"Queue system {status}!", show_alert=True)
    await admin_refresh(client, callback_query)

@Client.on_callback_query(filters.regex("^admin_manage_channels$") & filters.user(ADMINS))
async def manage_channels(client: Client, callback_query: CallbackQuery):
    """Channel management menu"""
    channel_list = ""
    for i, ch in enumerate(FORCE_SUB_CHANNELS, 1):
        status = "✅" if ch.get('enabled', True) else "❌"
        channel_list += f"{i}. {status} {ch['name']}\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Channel", callback_data="channel_add")],
        [InlineKeyboardButton("🔄 Toggle Channel", callback_data="channel_toggle")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_refresh")]
    ])
    
    await callback_query.message.edit_text(
        f"<b>📋 Channel Management</b>\n\n"
        f"<b>Current Channels:</b>\n{channel_list}\n"
        f"Select an action:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.regex("^channel_toggle$") & filters.user(ADMINS))
async def toggle_channel_menu(client: Client, callback_query: CallbackQuery):
    """Show channel toggle buttons"""
    buttons = []
    for ch in FORCE_SUB_CHANNELS:
        status = "✅" if ch.get('enabled', True) else "❌"
        buttons.append([
            InlineKeyboardButton(
                f"{status} {ch['name']}", 
                callback_data=f"togglech_{ch['channel_id']}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_manage_channels")])
    
    await callback_query.message.edit_text(
        "<b>🔄 Toggle Channel Status</b>\n\n"
        "Click a channel to enable/disable it:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex("^togglech_") & filters.user(ADMINS))
async def apply_toggle_channel(client: Client, callback_query: CallbackQuery):
    """Toggle specific channel"""
    channel_id = int(callback_query.data.split("_")[1])
    
    # Find and toggle channel in config
    for ch in FORCE_SUB_CHANNELS:
        if ch['channel_id'] == channel_id:
            ch['enabled'] = not ch.get('enabled', True)
            status = "✅ Enabled" if ch['enabled'] else "❌ Disabled"
            await callback_query.answer(f"{ch['name']} {status}!", show_alert=True)
            break
    
    await toggle_channel_menu(client, callback_query)

@Client.on_callback_query(filters.regex("^admin_close$") & filters.user(ADMINS))
async def close_admin_panel(client: Client, callback_query: CallbackQuery):
    """Close admin panel"""
    await callback_query.message.delete()
    await callback_query.answer("Panel closed!")
