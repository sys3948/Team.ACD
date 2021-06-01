from app import create_app


app = create_app('default')
app.run(debug=True)
# app.run(host='0.0.0.0', debug=True)


