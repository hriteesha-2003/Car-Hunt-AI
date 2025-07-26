from datetime import datetime
from fastapi import HTTPException
from bson import ObjectId



# def convert_object_ids(obj):
#     if isinstance(obj, list):
#         return [convert_object_ids(item) for item in obj]
#     elif isinstance(obj, dict):
#         return {key: convert_object_ids(value) for key, value in obj.items()}
#     elif isinstance(obj, ObjectId):
#         return str(obj)
#     else:
#         return obj

def convert_object_ids(obj):
    if isinstance(obj, list):
        return [convert_object_ids(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_object_ids(value) for key, value in obj.items()}
    elif isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj



def objid(id):
    try:
        return ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId")

def convert_datetime(obj):
    if isinstance(obj, list):
        return [convert_datetime(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_datetime(v) for k, v in obj.items()}
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj
    
