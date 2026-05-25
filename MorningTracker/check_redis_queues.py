
import redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    print(f"Priority Queue Length: {r.llen('priority')}")
    print(f"Celery Queue Length: {r.llen('celery')}")
except Exception as e:
    print(f"Error connecting to Redis: {e}")
