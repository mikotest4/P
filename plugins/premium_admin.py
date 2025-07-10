import asyncio
import os
import random
import sys
import time
from datetime import datetime, timedelta
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, ChatInviteLink, ChatPrivileges
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant
from bot import Bot
from config import *
from helper_func import *
from database.database import *
from database.db_premium import *

# Premium Management Commands

@Bot.on_message(filters.private & filters.command('addpremium') & admin)
async def add_premium(client: Client, message: Message):
    """Add premium to a user manually"""
    pro = await message.reply("⏳ <i>Processing premium request...</i>", quote=True)
    
    try:
        args = message.text.split()
        if len(args) < 3:
            return await pro.edit(
                "<b>❗ Usage:</b>\n"
                "<code>/addpremium [user_id] [days]</code>\n\n"
                "<b>Example:</b>\n"
                "<code>/addpremium 123456789 30</code>"
            )
        
        user_id = int(args[1])
        days = int(args[2])
        
        if days <= 0:
            return await pro.edit("<b>❗ Days must be greater than 0</b>")
        
        # Add premium user
        success = await add_premium_user(user_id, days)
        
        if success:
            await pro.edit(
                f"<b>✅ Premium Added Successfully!</b>\n\n"
                f"<b>👤 User ID:</b> <code>{user_id}</code>\n"
                f"<b>📅 Duration:</b> {days} days\n"
                f"<b>⏰ Added on:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Notify user
            try:
                await client.send_message(
                    chat_id=user_id,
                    text=f"🎉 <b>Congratulations!</b>\n\n"
                         f"You have been granted <b>{days} days</b> of premium membership!\n\n"
                         f"Enjoy unlimited access! 🚀"
                )
            except:
                await pro.edit(pro.text + "\n\n<i>⚠️ Could not notify user</i>")
        else:
            await pro.edit("❌ Failed to add premium. User might already have premium.")
            
    except ValueError:
        await pro.edit("<b>❗ Invalid user ID or days format</b>")
    except Exception as e:
        await pro.edit(f"<b>❌ Error:</b> <code>{str(e)}</code>")

@Bot.on_message(filters.private & filters.command('remove_premium') & admin)
async def remove_premium_cmd(client: Client, message: Message):
    """Remove premium from a user"""
    pro = await message.reply("⏳ <i>Processing removal...</i>", quote=True)
    
    try:
        args = message.text.split()
        if len(args) < 2:
            return await pro.edit(
                "<b>❗ Usage:</b>\n"
                "<code>/remove_premium [user_id]</code>\n\n"
                "<b>Example:</b>\n"
                "<code>/remove_premium 123456789</code>"
            )
        
        user_id = int(args[1])
        
        # Check if user has premium
        if not await is_premium_user(user_id):
            return await pro.edit(f"<b>❌ User <code>{user_id}</code> is not a premium user</b>")
        
        # Remove premium
        success = await remove_premium(user_id)
        
        if success:
            await pro.edit(
                f"<b>✅ Premium Removed Successfully!</b>\n\n"
                f"<b>👤 User ID:</b> <code>{user_id}</code>\n"
                f"<b>⏰ Removed on:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Notify user
            try:
                await client.send_message(
                    chat_id=user_id,
                    text="⚠️ <b>Premium Expired</b>\n\n"
                         "Your premium membership has been removed.\n\n"
                         "Contact support if you believe this is an error."
                )
            except:
                await pro.edit(pro.text + "\n\n<i>⚠️ Could not notify user</i>")
        else:
            await pro.edit("❌ Failed to remove premium.")
            
    except ValueError:
        await pro.edit("<b>❗ Invalid user ID format</b>")
    except Exception as e:
        await pro.edit(f"<b>❌ Error:</b> <code>{str(e)}</code>")

@Bot.on_message(filters.private & filters.command('premium_users') & admin)
async def premium_users_list(client: Client, message: Message):
    """List all premium users"""
    pro = await message.reply("⏳ <i>Fetching premium users...</i>", quote=True)
    
    try:
        premium_users = await list_premium_users()
        
        if not premium_users:
            return await pro.edit("<b>📋 No premium users found</b>")
        
        text = "<b>👑 Premium Users List:</b>\n\n"
        count = 0
        
        for user in premium_users:
            count += 1
            user_id = user['user_id']
            expires_at = user['expires_at']
            days_left = user['days_left']
            
            status = "🟢 Active" if days_left > 0 else "🔴 Expired"
            
            text += f"<b>{count}.</b> <code>{user_id}</code>\n"
            text += f"   📅 Expires: {expires_at}\n"
            text += f"   ⏳ Days left: {days_left}\n"
            text += f"   {status}\n\n"
            
            # Split message if too long
            if len(text) > 3500:
                await pro.edit(text)
                pro = await message.reply("⏳ <i>Continuing...</i>")
                text = ""
        
        if text:
            await pro.edit(text + f"\n<b>📊 Total Premium Users: {count}</b>")
        else:
            await pro.edit(f"<b>📊 Total Premium Users: {count}</b>")
            
    except Exception as e:
        await pro.edit(f"<b>❌ Error:</b> <code>{str(e)}</code>")

@Bot.on_message(filters.private & filters.command('myplan'))
async def my_plan(client: Client, message: Message):
    """Check user's premium plan"""
    user_id = message.from_user.id
    
    try:
        if await is_premium_user(user_id):
            # Get premium details
            premium_users = await list_premium_users()
            user_data = None
            
            for user in premium_users:
                if user['user_id'] == user_id:
                    user_data = user
                    break
            
            if user_data:
                text = f"<b>👑 Your Premium Plan</b>\n\n"
                text += f"<b>📅 Expires on:</b> {user_data['expires_at']}\n"
                text += f"<b>⏳ Days remaining:</b> {user_data['days_left']} days\n"
                text += f"<b>📊 Status:</b> {'🟢 Active' if user_data['days_left'] > 0 else '🔴 Expired'}"
                
                if user_data['days_left'] <= 3:
                    text += f"\n\n⚠️ <b>Your premium is expiring soon!</b>\nRenew now to continue enjoying unlimited access."
                    
                await message.reply(text)
            else:
                await message.reply("❌ <b>Could not fetch your premium details</b>")
        else:
            await message.reply(
                "❌ <b>You don't have premium membership</b>\n\n"
                "Click the button below to buy premium!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 Buy Premium", callback_data="premium")]
                ])
            )
            
    except Exception as e:
        await message.reply(f"❌ <b>Error:</b> <code>{str(e)}</code>")

@Bot.on_message(filters.private & filters.command('pending_payments') & admin)
async def pending_payments(client: Client, message: Message):
    """Show pending payment requests"""
    pro = await message.reply("⏳ <i>Fetching pending payments...</i>", quote=True)
    
    try:
        pending = await db.database['payment_requests'].find({'status': 'pending'}).to_list(length=None)
        
        if not pending:
            return await pro.edit("📋 <b>No pending payments found</b>")
        
        text = "<b>💳 Pending Payments:</b>\n\n"
        count = 0
        
        for payment in pending:
            count += 1
            user_id = payment['_id']
            plan = payment['plan_name']
            amount = payment['amount']
            timestamp = datetime.fromtimestamp(payment['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            
            text += f"<b>{count}.</b> ID: <code>{user_id}</code>\n"
            text += f"   📅 Plan: {plan}\n"
            text += f"   💰 Amount: ₹{amount}\n"
            text += f"   ⏰ Time: {timestamp}\n\n"
        
        text += f"<b>📊 Total Pending: {count}</b>"
        await pro.edit(text)
        
    except Exception as e:
        await pro.edit(f"<b>❌ Error:</b> <code>{str(e)}</code>")

@Bot.on_message(filters.private & filters.command('approve_payment') & admin)
async def approve_payment_manual(client: Client, message: Message):
    """Manually approve a payment"""
    pro = await message.reply("⏳ <i>Processing approval...</i>", quote=True)
    
    try:
        args = message.text.split()
        if len(args) < 3:
            return await pro.edit(
                "<b>❗ Usage:</b>\n"
                "<code>/approve_payment [user_id] [days]</code>\n\n"
                "<b>Example:</b>\n"
                "<code>/approve_payment 123456789 30</code>"
            )
        
        user_id = int(args[1])
        days = int(args[2])
        
        # Add premium
        success = await add_premium_user(user_id, days)
        
        if success:
            # Remove from pending payments
            await db.delete_payment_request(user_id)
            
            await pro.edit(
                f"<b>✅ Payment Approved!</b>\n\n"
                f"<b>👤 User ID:</b> <code>{user_id}</code>\n"
                f"<b>📅 Premium Days:</b> {days}\n"
                f"<b>⏰ Approved on:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Notify user
            try:
                await client.send_message(
                    chat_id=user_id,
                    text=f"🎉 <b>Payment Approved!</b>\n\n"
                         f"Your {days} days premium membership has been activated!\n\n"
                         f"Thank you for your purchase! 🚀"
                )
            except:
                await pro.edit(pro.text + "\n\n<i>⚠️ Could not notify user</i>")
        else:
            await pro.edit("❌ Failed to approve payment")
            
    except ValueError:
        await pro.edit("<b>❗ Invalid format</b>")
    except Exception as e:
        await pro.edit(f"<b>❌ Error:</b> <code>{str(e)}</code>")

@Bot.on_message(filters.private & filters.command('reject_payment') & admin)
async def reject_payment_manual(client: Client, message: Message):
    """Manually reject a payment"""
    pro = await message.reply("⏳ <i>Processing rejection...</i>", quote=True)
    
    try:
        args = message.text.split()
        if len(args) < 2:
            return await pro.edit(
                "<b>❗ Usage:</b>\n"
                "<code>/reject_payment [user_id]</code>\n\n"
                "<b>Example:</b>\n"
                "<code>/reject_payment 123456789</code>"
            )
        
        user_id = int(args[1])
        
        # Remove from pending payments
        await db.delete_payment_request(user_id)
        
        await pro.edit(
            f"<b>❌ Payment Rejected</b>\n\n"
            f"<b>👤 User ID:</b> <code>{user_id}</code>\n"
            f"<b>⏰ Rejected on:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Notify user
        try:
            await client.send_message(
                chat_id=user_id,
                text="❌ <b>Payment Rejected</b>\n\n"
                     "Your payment could not be verified.\n"
                     "Please contact support if you believe this is an error.\n\n"
                     f"Support: {OWNER_TAG}"
            )
        except:
            await pro.edit(pro.text + "\n\n<i>⚠️ Could not notify user</i>")
            
    except ValueError:
        await pro.edit("<b>❗ Invalid user ID format</b>")
    except Exception as e:
        await pro.edit(f"<b>❌ Error:</b> <code>{str(e)}</code>")

@Bot.on_message(filters.private & filters.command('premium_stats') & admin)
async def premium_stats(client: Client, message: Message):
    """Show premium statistics"""
    pro = await message.reply("⏳ <i>Calculating stats...</i>", quote=True)
    
    try:
        # Get all premium users
        premium_users = await list_premium_users()
        
        # Get pending payments
        pending = await db.database['payment_requests'].find({'status': 'pending'}).to_list(length=None)
        
        # Calculate stats
        total_premium = len(premium_users)
        active_premium = len([u for u in premium_users if u['days_left'] > 0])
        expired_premium = total_premium - active_premium
        pending_payments = len(pending)
        
        # Calculate revenue (approximate)
        total_revenue = 0
        for payment in await db.database['payment_requests'].find({'status': 'completed'}).to_list(length=None):
            total_revenue += int(payment.get('amount', 0))
        
        text = f"<b>📊 Premium Statistics</b>\n\n"
        text += f"<b>👑 Total Premium Users:</b> {total_premium}\n"
        text += f"<b>🟢 Active Premium:</b> {active_premium}\n"
        text += f"<b>🔴 Expired Premium:</b> {expired_premium}\n"
        text += f"<b>💳 Pending Payments:</b> {pending_payments}\n"
        text += f"<b>💰 Total Revenue:</b> ₹{total_revenue}\n\n"
        text += f"<b>📈 Success Rate:</b> {((active_premium/total_premium)*100):.1f}%" if total_premium > 0 else "0%"
        
        await pro.edit(text)
        
    except Exception as e:
        await pro.edit(f"<b>❌ Error:</b> <code>{str(e)}</code>")

# Handle payment screenshot uploads
@Bot.on_message(filters.private & filters.photo)
async def handle_payment_screenshot(client: Client, message: Message):
    """Handle payment screenshot uploads"""
    user_id = message.from_user.id
    
    try:
        # Check if user has pending payment
        payment_request = await db.get_payment_request(user_id)
        
        if not payment_request or payment_request.get('status') != 'screenshot_pending':
            return  # Not a payment screenshot
        
        # Update status to screenshot received
        await db.update_payment_status(user_id, 'screenshot_received')
        
        # Forward screenshot to admin
        user_name = message.from_user.first_name or "Unknown"
        username = message.from_user.username or "No username"
        plan_name = payment_request['plan_name']
        amount = payment_request['amount']
        
        caption = f"💳 <b>Payment Screenshot Received!</b>\n\n"
        caption += f"👤 <b>User:</b> {user_name} (@{username})\n"
        caption += f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        caption += f"📅 <b>Plan:</b> {plan_name}\n"
        caption += f"💰 <b>Amount:</b> ₹{amount}\n"
        caption += f"⏰ <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Forward to admin with approval buttons
        await client.send_photo(
            chat_id=OWNER_ID,
            photo=message.photo.file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}_{payment_request['days']}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
                ]
            ])
        )
        
        # Confirm to user
        await message.reply(
            "✅ <b>Screenshot Received!</b>\n\n"
            "Your payment screenshot has been forwarded to admin for verification.\n\n"
            "⏳ You will receive confirmation within 5-10 minutes.\n\n"
            f"📞 Need help? Contact: {OWNER_TAG}"
        )
        
    except Exception as e:
        print(f"Error handling screenshot: {e}")
