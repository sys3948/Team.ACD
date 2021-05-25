from app import create_app


app = create_app('default')
app.run(host='0.0.0.0')


<<<<<<< HEAD
=======
if __name__ == '__main__':
    socketio.run(app, debug=True)
    # socketio.run(app,host='0.0.0.0',debug=True)
>>>>>>> df109f475eb84a54df252af106130519bad54bd9
