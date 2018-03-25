import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, copy_current_request_context
from flask_socketio import SocketIO, emit
from threading import Thread
import zmq
from multiprocessing import Process

thread = None

app = Flask(__name__)
#app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode="eventlet")

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on("connect")
def say_hello():
    print("USER CONNECTED")
    global thread
    if not thread:
        @copy_current_request_context
        def f():
            print("Binding socket...")
            poller = zmq.Poller()
            context = zmq.Context()
            socket = context.socket(zmq.REP)
            socket.bind("{}://{}:{}".format("tcp", "*", 5560))
            poller.register(socket, zmq.POLLIN)
            print("socket is binded")
            while True:
                eventlet.sleep(2)
                try:
                    messages = dict(poller.poll())
                    print(messages)
                    if socket in messages:
                        msg = socket.recv()
                        print(msg)
                        socket.send(b"READY")
                        emit("message", msg.decode())
                except Exception as e:
                    print(e)
        socketio.start_background_task(target=f)
        thread = True


@socketio.on("message")
def blep(message):
    print(message)


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=8000, debug=True) 
