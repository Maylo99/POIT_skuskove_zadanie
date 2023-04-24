from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect
import math
import time
import json
import os
import MySQLdb
import time
import configparser as ConfigParser
import random

async_mode = None

app = Flask(__name__)

config = ConfigParser.ConfigParser()
config.read('config.cfg')
myhost = config.get('mysqlDB', 'host')
myuser = config.get('mysqlDB', 'user')
mypasswd = config.get('mysqlDB', 'passwd')
mydb = config.get('mysqlDB', 'db')
print(myhost)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()


def get_data_from_db(db, id):
    cursor = db.cursor()
    cursor.execute("SELECT hodnoty FROM graph WHERE id = %s", (id,))
    row_data = cursor.fetchone()
    return row_data


def write_to_json(new_record, str_id):
    filename = "data.json"
    if os.path.getsize(filename) > 0:
        with open(filename, 'r') as f:
            existing_data = json.load(f)
        init={
            "id": str_id,
            "result": {
                "data": new_record
            }
        }
        # Append new record to existing data
        existing_data.append(init)

        # Write combined data back to file as a JSON array
        with open(filename, 'w') as f:
            f.write(json.dumps(existing_data, indent=4))
    else:
        # Write new record as a JSON array to file
        init = [{
            "id": str_id,
            "result": {
                "data": new_record
            }
        }
        ]

        with open(filename, 'w') as f:
            f.write(json.dumps(init))


def background_thread(args):
    count = 0
    dataList = []
    btnV = ""
    db = MySQLdb.connect(host=myhost, user=myuser, passwd=mypasswd, db=mydb)
    while True:
        time.sleep(2)
        if args:
            A = dict(args).get('A')
            btnV = dict(args).get('btn_value')
            row_id_value = dict(args).get('row_id')
        else:
            A = 1
        # print A
        if btnV == "start":
            flag = 1
        elif btnV == "stop":
            flag = 0
        else:
            flag = 2
        if flag == 1:
            print(args)
            socketio.sleep(2)
            count += 1
            prem = math.sin(time.time())
            prem2 = math.cos(time.time())
            dataDict = {
                "t": time.time(),
                "x": count,
                "y": float(A) * prem,
                "y2": float(A) * prem2, }
            dataList.append(dataDict)
            socketio.emit('my_response',
                          {'data': float(A) * prem, 'data2': float(A) * prem2, 'count': count},
                          namespace='/test')
        elif flag == 0:
            if len(dataList) > 0:
                json_object = json.dumps(dataList, indent=4)

                print(str(dataList).replace("'", "\""))
                cursor = db.cursor()
                cursor.execute("SELECT MAX(id) FROM graph")
                maxid = cursor.fetchone()
                cursor.execute("INSERT INTO graph (id, hodnoty) VALUES (%s, %s)", (maxid[0] + 1, json_object))
                db.commit()
                write_to_json(dataList, str(maxid).replace("(", "").replace(")", ""))
                dataList = []

        if row_id_value is not None or row_id_value != "":
            row_data_values = get_data_from_db(db, row_id_value)
            row_id_value = ""
            # socketio.emit('my_response2',
            #           { 'row_data':row_data_values},namespace='/test')

    db.close()


@app.route('/')
def index():
    return render_template('tabs.html', async_mode=socketio.async_mode)

@socketio.on('row_id_event', namespace='/test')
def test_message(message):
    session['row_id'] = message['row_id']
    # emit('my_response',
    #      {'data': message['value'], 'count': session['receive_count']})
@socketio.on('my_event', namespace='/test')
def test_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    session['A'] = message['value']
    emit('my_response',
         {'data': message['value'], 'count': session['receive_count']})


@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()


@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())
    emit('my_response', {'data': 'Connected', 'count': 0})


@socketio.on('click_event', namespace='/test')
def db_message(message):
    session['btn_value'] = message['value']


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)
