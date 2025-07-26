import os
from pymongo import MongoClient
from datetime import datetime
from config import (
    DATABASE_URL,
    DATABASE_NAME,
    USER_COLLECTION,
    CLIENT_COLLECTION,
    CATEGORY_COLLECTION,
    COMPANY_COLLECTION,
    AGENT_COLLECTION,
    CAR_BRAND_COLLECTION,
    CAR_COLLECTION,
    VEHICLE_TYPE_COLLECTION,
    REVIEW_COLLECTION,
    VIDEOS_COLLECTION,
    PHOTOS_COLLECTION,
    PRIVACY_COLLECTION_NAME,
    ABOUT_US_COLLECTION,
    BOTTOM_SLIDER_COLLECTION,
    SETTINGS_COLLECTION,
    FAQ_COLLECTION,
    MESSAGES_COLLECTION,
    CHAT_COLLECTION,
     
)


client = MongoClient(DATABASE_URL)
db = client[DATABASE_NAME]





user_collection = db[USER_COLLECTION]
category_collection = db[CATEGORY_COLLECTION]
company_collection = db[COMPANY_COLLECTION]
client_collection = db[CLIENT_COLLECTION]
agent_collection = db[AGENT_COLLECTION]
car_brand_collection = db[CAR_BRAND_COLLECTION]
car_collection = db[CAR_COLLECTION]
vehicle_type_collection = db[VEHICLE_TYPE_COLLECTION]
review_collection = db[REVIEW_COLLECTION]
videos_collection = db[VIDEOS_COLLECTION]
photos_collection = db[PHOTOS_COLLECTION]
email_templates = db["email_templates"]
ai_agent_collection = db["ai_agent_collection"]
home_featured_items = db["home_featured_items"]
privacy_collection = db["PRIVACY_COLLECTION_NAME"]
about_us_collection = db["about_us"]
bottom_slider_collection = db["bottom_slider"]
settings_collection = db["settings"]
faq_collection = db["faq"]
messages_collection = db["messages"]
chat_collection = db["chats_sessions"]
