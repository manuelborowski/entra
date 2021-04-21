function Message(arg) {
    this.text = arg.text;
    this.side = arg.side;
    this.initials = arg.initials;
    this.messages = arg.messages
    this.draw = function (_this) {
        return function () {
            var $message = $($('.message-template').clone().html());
            $message.addClass(_this.side).find('.text').html(_this.text);
            $message.find('.avatar').html(_this.initials);
            _this.messages.append($message);
            return setTimeout(function () {
                $message.addClass('appeared');
                return _this.messages.animate({scrollTop: _this.messages.prop('scrollHeight')}, 300);
            }, 0);
        };
    }(this);
    return this;
}


class Chat {
    rooms = {}
    add_chat_room_cb
    delete_chat_room_cb

    constructor() {
        socketio.subscribe_on_receive("chat-line", this.socketio_receive_chat_line_cb.bind(this));
        socketio.subscribe_on_receive("add-chat-room", this.socketio_add_chat_room_cb.bind(this));
    }

    on_connect_cb(opaque) {
        socketio.send_to_server('new-end-user', {user_code: opaque});
    }


    start(user_code, add_room_cb, delete_room_cb) {
        this.add_chat_room_cb = add_room_cb;
        this.delete_chat_room_cb = delete_room_cb;
        socketio.start(this.on_connect_cb, user_code);
    }

    subscribe_to_room(floor_level, room_code, sender_code, user_initials) {
        socketio.subscribe_to_room(room_code);
        this.rooms[room_code] = {
            floor_level: floor_level,
            sender_code: sender_code,
            initials: user_initials,
            jq_send_button: $("#" + room_code).children(".chat_window").children(".bottom_wrapper").children(".send_message"),
            jq_input_text: $("#" + room_code).children(".chat_window").children(".bottom_wrapper").children(".message_input_wrapper").children(".message_input"),
            jq_output_messages: $("#" + room_code).children(".chat_window").children(".messages")
        };

        this.rooms[room_code].jq_send_button.on("click", {value: room_code}, function (e) {
            var room_code = e.data.value;
            return this.send_chat_line(room_code, this.rooms[room_code].sender_code, this.rooms[room_code].initials, this.rooms[room_code].jq_input_text);
        }.bind(this));

        this.rooms[room_code].jq_input_text.on("keyup", {value: room_code}, function (e) {
            if (e.which === 13) {
                var room_code = e.data.value;
                return this.send_chat_line(room_code, this.rooms[room_code].sender_code, this.rooms[room_code].initials, this.rooms[room_code].jq_input_text);
            }
        }.bind(this));
    }

    send_chat_line(room_code, sender_code, initials, $jq_input_element = null, text = null) {
        if ($jq_input_element) {
            text = $jq_input_element.val();
            $jq_input_element.val("");
        }
        if (text.trim() === "") return;
        socketio.send_to_server('chat-line', {room: room_code, sender: sender_code, initials: initials, text: text});
        return false;
    }

    socketio_receive_chat_line_cb(type, data) {
        var message = new Message({
            text: data.text,
            side: data.room == data.sender ? 'left': 'right',
            initials: data.initials,
            messages: this.rooms[data.room].jq_output_messages
        });
        message.draw();
    }

    socketio_add_chat_room_cb(type, data) {
        this.add_chat_room_cb(data.floor, data.room_code, data.title);
    }
}

var chat;
$(function () { // same as $(document).ready()
    chat = new Chat();
});

