# intentionally empty; called on package initialization
from pymongo.objectid import ObjectId

def new_id():
    return str(ObjectId())
