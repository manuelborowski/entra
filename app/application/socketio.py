from flask import request
from flask_socketio import emit, join_room, leave_room, close_room
from app import socketio

socketio_cbs = {}

# clients can subscribe to a room.  The server can broadcast an event into that room only.


@socketio.event
def subscribe_to_room(message):
    join_room(message['room'])


@socketio.event
def leave_room(message):
    leave_room(message['room'])


@socketio.on
def close_room(message):
    close_room(message['room'])


@socketio.event
def send_to_server(msg):
    if msg['type'] in socketio_cbs:
        if 'value' in msg['data'] and msg['data']['value'] == 'on': # bugfix socketio?  Sometimes, a True at the sender becomes 'on' at the receiver
            msg['data']['value'] = True
        for cb in socketio_cbs[msg['type']]:
            cb(msg, request.sid)


@socketio.on('disconnect')
def disconnect_socket():
    if 'disconnect' in socketio_cbs:
        for cb in socketio_cbs['disconnect']:
            cb(None, request.sid)


@socketio.event
def connect():
    pass


@socketio.event
def its_me(data):
    emit('send_to_client', {'type': 'its-me-received', 'data': True}, room=request.sid)


def subscribe_on_type(type, cb):
    if type in socketio_cbs:
        socketio_cbs[type].append(cb)
    else:
        socketio_cbs[type] = [cb]


def send_to_room(msg, room):
    emit('send_to_client', msg, room=room)


def broadcast_message(type, msg={}):
    data = {'type': type, 'data': msg}
    emit('send_to_client', data, broadcast=True, namespace='/')


def send_to_client(client_sid, type, msg):
    emit(type, msg, room=client_sid)