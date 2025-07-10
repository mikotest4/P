import motor.motor_asyncio
from config import DB_URI, DB_NAME
from pytz import timezone
from datetime import datetime, timedelta
import logging

# Create an async client with Motor
dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
database = dbclient[DB_NAME]
collection = database['premium-users']

# Configure logging for premium operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if the user is a premium user
async def is_premium_user(user_id):
    user = await collection.find_one({"user_id": user_id})  # Async query
    return user is not None

# Remove premium user
async def remove_premium(user_id):
    result = await collection.delete_one({"user_id": user_id})  # Async removal
    if result.deleted_count > 0:
        logger.info(f"Premium removed for user: {user_id}")
    return result.deleted_count > 0

# Enhanced remove expired users with better logging
async def remove_expired_users():
    """Enhanced function to remove expired users with detailed logging"""
    try:
        ist = timezone("Asia/Kolkata")
        current_time = datetime.now(ist)
        removed_count = 0

        # Find all premium users
        async for user in collection.find({}):
            user_id = user.get("user_id")
            expiration = user.get("expiration_timestamp")
            
            if not expiration or not user_id:
                # Remove invalid entries
                await collection.delete_one({"user_id": user_id})
                logger.warning(f"Removed invalid premium entry for user: {user_id}")
                removed_count += 1
                continue

            try:
                expiration_time = datetime.fromisoformat(expiration).astimezone(ist)
                if expiration_time <= current_time:
                    # Remove expired user
                    await collection.delete_one({"user_id": user_id})
                    logger.info(f"Auto-removed expired premium user: {user_id} (expired: {expiration_time.strftime('%Y-%m-%d %H:%M:%S')})")
                    removed_count += 1
            except Exception as e:
                logger.error(f"Error processing user {user_id}: {e}")
                # Remove problematic entries
                await collection.delete_one({"user_id": user_id})
                removed_count += 1

        if removed_count > 0:
            logger.info(f"Premium cleanup completed: {removed_count} expired users removed")
        
        return removed_count
    except Exception as e:
        logger.error(f"Error in remove_expired_users: {e}")
        return 0

# Startup cleanup function
async def startup_premium_cleanup():
    """Clean expired premium users on bot startup"""
    try:
        logger.info("Starting premium cleanup on bot startup...")
        removed_count = await remove_expired_users()
        logger.info(f"Startup cleanup completed: {removed_count} expired users removed")
        return removed_count
    except Exception as e:
        logger.error(f"Error in startup cleanup: {e}")
        return 0

# Get users expiring in next 24 hours (for notifications)
async def get_users_expiring_in_24h():
    """Get list of users whose premium expires in next 24 hours"""
    try:
        ist = timezone("Asia/Kolkata")
        current_time = datetime.now(ist)
        tomorrow = current_time + timedelta(days=1)
        
        expiring_users = []
        async for user in collection.find({}):
            user_id = user.get("user_id")
            expiration = user.get("expiration_timestamp")
            
            if expiration and user_id:
                try:
                    expiration_time = datetime.fromisoformat(expiration).astimezone(ist)
                    if current_time < expiration_time <= tomorrow:
                        expiring_users.append({
                            'user_id': user_id,
                            'expires_at': expiration_time
                        })
                except Exception as e:
                    logger.error(f"Error processing expiring user {user_id}: {e}")
        
        return expiring_users
    except Exception as e:
        logger.error(f"Error getting expiring users: {e}")
        return []

# List active premium users with enhanced info
async def list_premium_users():
    """List active premium users with detailed information"""
    try:
        # Define IST timezone
        ist = timezone("Asia/Kolkata")
        current_time = datetime.now(ist)
        
        # Fetch all premium users from the collection
        premium_users = collection.find({})
        premium_user_list = []
        expired_found = 0

        async for user in premium_users:
            user_id = user["user_id"]
            expiration_timestamp = user["expiration_timestamp"]

            try:
                # Convert expiration timestamp to a timezone-aware datetime object in IST
                expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(ist)

                # Calculate the remaining time (make sure both are timezone-aware)
                remaining_time = expiration_time - current_time

                if remaining_time.total_seconds() > 0:  # Only active users
                    # Calculate days, hours, minutes, and seconds left
                    days, hours, minutes, seconds = (
                        remaining_time.days,
                        remaining_time.seconds // 3600,
                        (remaining_time.seconds // 60) % 60,
                        remaining_time.seconds % 60,
                    )

                    # Format the expiration time in IST and remaining time
                    expiry_info = f"{days}d {hours}h {minutes}m {seconds}s left"

                    # Format the expiration time for clarity
                    formatted_expiry_time = expiration_time.strftime('%Y-%m-%d %H:%M:%S %p IST')

                    # Add user info to the list with both remaining and expiration times
                    premium_user_list.append(f"UserID: {user_id} - Expiry: {expiry_info} (Expires at {formatted_expiry_time})")
                else:
                    expired_found += 1
            except Exception as e:
                logger.error(f"Error processing user {user_id} in list: {e}")
                expired_found += 1

        if expired_found > 0:
            logger.info(f"Found {expired_found} expired users during listing (will be cleaned up automatically)")

        return premium_user_list
    except Exception as e:
        logger.error(f"Error listing premium users: {e}")
        return []

# Add premium user with enhanced logging
async def add_premium(user_id, time_value, time_unit):
    """
    Add a premium user for a specific duration with enhanced logging.
    
    Args:
        user_id (int): The ID of the user to add premium access for.
        time_value (int): The numeric value of the duration.
        time_unit (str): Time unit - 's'=seconds, 'm'=minutes, 'h'=hours, 'd'=days, 'y'=years.
    """
    try:
        # Normalize unit to lowercase
        time_unit = time_unit.lower()

        # Get IST timezone
        ist = timezone("Asia/Kolkata")

        # Calculate expiration time
        now = datetime.now(ist)
        if time_unit == 's':
            expiration_time = now + timedelta(seconds=time_value)
        elif time_unit == 'm':
            expiration_time = now + timedelta(minutes=time_value)
        elif time_unit == 'h':
            expiration_time = now + timedelta(hours=time_value)
        elif time_unit == 'd':
            expiration_time = now + timedelta(days=time_value)
        elif time_unit == 'y':
            expiration_time = now + timedelta(days=365 * time_value)
        else:
            raise ValueError("Invalid time unit. Use 's', 'm', 'h', 'd', or 'y'.")

        # Prepare premium data
        premium_data = {
            "user_id": user_id,
            "expiration_timestamp": expiration_time.isoformat(),
        }

        # Update database
        result = await collection.update_one(
            {"user_id": user_id},
            {"$set": premium_data},
            upsert=True
        )

        # Format and return
        formatted_expiration = expiration_time.strftime('%Y-%m-%d %H:%M:%S %p IST')
        
        if result.upserted_id:
            logger.info(f"Added new premium user: {user_id} (expires: {formatted_expiration})")
        else:
            logger.info(f"Updated premium user: {user_id} (expires: {formatted_expiration})")
        
        return formatted_expiration
    except Exception as e:
        logger.error(f"Error adding premium for user {user_id}: {e}")
        raise

# Check if a user has an active premium plan with auto-cleanup
async def check_user_plan(user_id):
    """Check user's premium plan with automatic cleanup of expired users"""
    try:
        user = await collection.find_one({"user_id": user_id})  # Async query for user
        if not user:
            return None
            
        expiration_timestamp = user["expiration_timestamp"]
        
        # Define IST timezone
        ist = timezone("Asia/Kolkata")
        
        # Convert expiration timestamp to a timezone-aware datetime object in IST
        expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(ist)
        
        # Get current time in IST
        current_time = datetime.now(ist)
        
        # Check if the premium is still active
        if expiration_time > current_time:
            # Calculate remaining time
            remaining_time = expiration_time - current_time
            
            # Calculate days, hours, minutes, and seconds left
            days, hours, minutes, seconds = (
                remaining_time.days,
                remaining_time.seconds // 3600,
                (remaining_time.seconds // 60) % 60,
                remaining_time.seconds % 60,
            )
            
            # Format the remaining time
            time_left = f"{days}d {hours}h {minutes}m {seconds}s"
            
            # Format the expiration time for clarity
            formatted_expiry_time = expiration_time.strftime('%Y-%m-%d %H:%M:%S %p IST')
            
            return {
                "active": True,
                "time_left": time_left,
                "expires_on": formatted_expiry_time
            }
        else:
            # Premium has expired, remove from database
            await remove_premium(user_id)
            logger.info(f"Auto-removed expired premium user during plan check: {user_id}")
            return {
                "active": False,
                "expired": True,
                "expired_on": expiration_time.strftime('%Y-%m-%d %H:%M:%S %p IST')
            }
    except Exception as e:
        logger.error(f"Error checking user plan for {user_id}: {e}")
        return None

# Get premium statistics
async def get_premium_stats():
    """Get premium user statistics"""
    try:
        total_users = await collection.count_documents({})
        active_users = 0
        expired_users = 0
        
        ist = timezone("Asia/Kolkata")
        current_time = datetime.now(ist)
        
        async for user in collection.find({}):
            expiration = user.get("expiration_timestamp")
            if expiration:
                try:
                    expiration_time = datetime.fromisoformat(expiration).astimezone(ist)
                    if expiration_time > current_time:
                        active_users += 1
                    else:
                        expired_users += 1
                except:
                    expired_users += 1
            else:
                expired_users += 1
        
        return {
            "total": total_users,
            "active": active_users,
            "expired": expired_users
        }
    except Exception as e:
        logger.error(f"Error getting premium stats: {e}")
        return {"total": 0, "active": 0, "expired": 0}
