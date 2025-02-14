import os
from dotenv import load_dotenv
import redis

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_REDIS = redis.from_url(os.environ.get("REDIS_URL"))
    MY_DATABASE_URL = os.environ.get("MY_DATABASE_URL")