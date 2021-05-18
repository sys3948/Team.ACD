from app import create_app,socketio


app = create_app('default')
#app.run(host='0.0.0.0')

if __name__ == '__main__':
    socketio.run(app,host='0.0.0.0')
