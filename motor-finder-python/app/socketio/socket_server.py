import socketio
import datetime
from bson import ObjectId
from app.database.db import agent_collection, client_collection, chat_collection, messages_collection

# Create a Socket.IO server with ASGI compatibility
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
sio_app = socketio.ASGIApp(sio)

# When a socket client connects
@sio.event
async def connect(sid, environ):
    print(f"{sid} connected")

# When a socket client disconnects
@sio.event
async def disconnect(sid):
    print(f"{sid} disconnected")
    mark_user_offline(sid)

@sio.on("start_chat")
async def start_chat(sid, data):
    client_id = data["client_id"]
    company_id = data["company_id"]

    # Find an available agent in the same company
    agent = agent_collection.find_one({
        "company_id": company_id,
        
    })

    if agent:
        # Create a new chat session
        chat = chat_collection.insert_one({
            "client_id": client_id,
            "agent_id": str(agent["_id"]),
            "company_id": company_id,
            "started_at": datetime.datetime.utcnow(),
            "is_active": True
        })

        # Mark agent as unavailable
        agent_collection.update_one({"_id": agent["_id"]},
                                     {"$set": {"is_available": False}})
        # Save client’s socket ID
        client_collection.update_one({"_id": ObjectId(client_id)}, 
                                     {"$set": {"socket_id": sid}})

        # Inform agent and client that chat has started
        sio.emit("chat_assigned", {
            "chat_id": str(chat.inserted_id),
            "client_id": client_id
        }, to=agent["socket_id"])

        sio.emit("chat_started", {
            "chat_id": str(chat.inserted_id),
            "agent_id": str(agent["_id"])
        }, to=sid)
    else:
        sio.emit("no_agents_available", {}, to=sid)

@sio.on("send_message")
async def send_message(sid, data):
    chat_id = data["chat_id"]
    sender_id = data["sender_id"]
    receiver_id = data["receiver_id"]
    message = data["message"]

    # Save the message in MongoDB
    doc = {
        "chat_id": chat_id,
        "from_id": sender_id,
        "to_id": receiver_id,
        "message": message,
        "timestamp": datetime.datetime.utcnow(),
        "is_read": False
    }
    messages_collection.insert_one(doc)

    # Send the message to the receiver in real-time
    receiver = get_user_or_agent(receiver_id)
    if receiver and receiver.get("socket_id"):
        sio.emit("receive_message", {
            "chat_id": chat_id,
            "sender_id": sender_id,
            "message": message
        }, to=receiver["socket_id"])

# Helper: Find by client/agent ID
async def get_user_or_agent(user_id):
    user = client_collection.find_one({"_id": ObjectId(user_id)})
    if user:
        return user
    return  agent_collection.find_one({"_id": ObjectId(user_id)})

# Helper: Mark users offline
async def mark_user_offline(socket_id):
    client_collection.update_one({"socket_id": socket_id}, {"$set": {"is_online": False}})
    agent_collection.update_one({"socket_id": socket_id}, {"$set": {"is_online": False, "is_available": False}})
