import datetime
import logging

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

def send_welcome_message(username:str, email:str):
    logger.info(f"Sending welcome message to {email}")
    logger.info(f"Welcome to AI vacation planner {username}")

def log_trip_creation(username:str, destination:str):
    logger.info(f"User {username} created a trip to {destination}")

def log_itinerary_creation(destination:str):
    logger.info(f"destination {destination} itinerary was created.")

def track_login_activity(username:str):
    timestamp = datetime.datetime.now()
    logger.info(f"User {username} logged in at {timestamp}")