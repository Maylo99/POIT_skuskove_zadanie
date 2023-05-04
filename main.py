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
        init = {
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
            f.close()
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
            f.close()


def search_data_file(id):
    with open('data.json', 'r') as f:
        data = json.load(f)
    for item in data:
        if item['id'] == int(id):
            return item


def background_thread(args):
    count = 0
    dataList = []
    btnV = ""
    db = MySQLdb.connect(host=myhost, user=myuser, passwd=mypasswd, db=mydb)
    while True:
        arduino_data = str(ser.readline().decode('ISO-8859-1').rstrip())
        print(arduino_data)
        split_data = arduino_data.split(':')
        distance = int(split_data[1])
        ir = int(split_data[3])
        if args:
            A = dict(args).get('A')
            option = dict(args).get('option')
            row_id_value = dict(args).get('row_id')
            file_id_value = dict(args).get('file_id')
            args['file_id'] = ""
            args['row_id'] = ""

            if option == "ir":
                if int(ir) == 0:
                    btnV = "stop"
                if int(ir) == 1:
                    btnV = "start"
            elif option == "btns":
                btnV = dict(args).get('btn_value')
            else:
                btnV = "stop"
        else:
            A = 1
        if btnV == "start":
            socketio.sleep(2)
            count += 1
            prem = distance
            prem2 = ir
            dataDict = {
                "t": time.time(),
                "x": count,
                "y": float(A) * prem,
                "y2": prem2 }
            dataList.append(dataDict)
            socketio.emit('my_response',
                          {'data': float(A) * prem, 'data2': prem2, 'count': count},
                          namespace='/test')
        elif btnV == "stop":
            if len(dataList) > 0:
                json_object = json.dumps(dataList, indent=4)
                print(str(dataList).replace("'", "\""))
                cursor = db.cursor()
                cursor.execute("SELECT MAX(id) FROM graph")
                maxid = cursor.fetchone()
                cursor.execute("INSERT INTO graph (id, hodnoty) VALUES (%s, %s)", (maxid[0] + 1, json_object))
                db.commit()
                write_to_json(dataList, maxid[0])
                dataList = []

        if row_id_value is not None and row_id_value != "":
            row_data_values = get_data_from_db(db, row_id_value)
            socketio.emit('my_response2',
                          {'row_data': row_data_values}, namespace='/test')

        if file_id_value is not None and file_id_value != "":
            filename = "data.json"
            if os.path.getsize(filename) > 0:
                data_from_file = search_data_file(file_id_value)
                socketio.emit('file_response',
                              {'row_data': data_from_file}, namespace='/test')

    db.close()


@app.route('/')
def index():
    return render_template('tabs.html', async_mode=socketio.async_mode)


@socketio.on('file_id_event', namespace='/test')
def test_message(message):
    session['file_id'] = message['file_id']


@socketio.on('row_id_event', namespace='/test')
def test_message(message):
    session['row_id'] = message['row_id']


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


@socketio.on('click_event2', namespace='/test')
def db_message(message):
    print(message)
    session['option'] = message['ir']


@socketio.on('click_event3', namespace='/test')
def db_message(message):
    print(message)
    session['option'] = message['btns']


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)
