from os import environ, urandom
from hmac import HMAC as hmac, compare_digest 
import bcrypt
from hashlib import sha256
from base64 import b64encode, b64decode
from flask import Flask, request, render_template, session, redirect, flash

import sqlite3
conn = sqlite3.connect('app.db', check_same_thread=False)

c = conn.cursor()
c.execute("""DROP TABLE IF EXISTS User""")
c.execute("""
   CREATE TABLE IF NOT EXISTS User (
      id integer primary key autoincrement,
      username text unique,
      password text,
      gender text defaul null,
      image blob default null,
      age integer default null,
      phone text defaul null,
      fav_color text default null,
      permissions integer default 222
   )""")
c.execute("""INSERT INTO User(username) VALUES ("Alice")""")
c.execute("""INSERT INTO User(username) VALUES ("Eve")""")
c.execute("""INSERT INTO User(username) VALUES ("Bob")""")
conn.commit()

app = Flask(__name__)
app.secret_key = b64decode(environ['SECRET_KEY'])
debug = True

FRIENDS = set([(0,1), (0,2), (1,2), (3, 1)]) # TODO move to database

def selectValue(value, user):
    if value not in ["id", "username", "password", "gender", "image", "age", "phone", "fav_color"]:
        return None
    c = conn.cursor()
    return c.execute("""SELECT {v} FROM User WHERE username=? LIMIT 1""".format(v=value),
            (user,)).fetchone()

@app.route('/')
def home():
   return render_template('home.html', authed="username" in session)

@app.route('/d3/')
def graph():
    if "username" not in session:
        return redirect('/')
    c = conn.cursor()
    users = c.execute("""SELECT username,id,gender,image,phone,fav_color,age FROM User""").fetchall()
    users.sort(key=lambda u: u[1]) # sort by SQL id
    username = session['username']
    try:
        me = list(filter(lambda u: u[0].capitalize() == username.capitalize(), users))[0]
    except:
        session.pop("username")
        return '', 400
    id = me[1]
    gender = me[2]
    color = me[5]
    age = me[6]
    # print(color)
    print(id, list(FRIENDS))
    return render_template('demo.html', users=users, friends=list(FRIENDS), name=username, id=id, color=color, age=age, gender=gender)

@app.route('/login/', methods=["POST"])
def login():
    if "username" in session:
        session.pop("username")
    username = request.form['name'].capitalize()
    password = request.form['password']
    user_pw = selectValue("password", username)
    if user_pw and bcrypt.checkpw(password.encode('utf-8'), user_pw[0]):
        session['username'] = username
    else:
        flash("Incorrect username/password")
    return redirect('/')

@app.route('/accountsetup/', methods=["GET", "POST"])
def accountsetup():
    if not "username" in session:
        return redirect('/')
    if request.method == "POST":
        gender = request.form['gender']
        favcolor = request.form['color']
        age = request.form['age']
        phone = request.form['phone']
        c = conn.cursor()
        c.execute("""UPDATE User SET gender=?,phone=?,fav_color=? WHERE username=?""", (gender,phone,favcolor,session['username']))
        conn.commit()
        return redirect("/")
    return render_template("createaccount.html")

@app.route('/addfriend/', methods=["GET", "POST"])
def addfriend():
    if not "username" in session:
        return redirect("/")
    id = selectValue("id", session["username"])[0]
    targ_id = selectValue("id", "Alice")[0]
    FRIENDS.add((id-1, targ_id-1))
    return redirect('/')
    if request.method == 'POST':
        if not "username" in session:
           return redirect("/")
        try:
            targ_id = int(request.values['target'])
        except:
            return '', 400
        FRIENDS.add((id, targ_id))
    return redirect('/')

@app.route('/register/', methods=["POST"])
def register():
   if "username" in session:
      return redirect('/')
   username = request.form['name'].capitalize()
   password = request.form['password']
   c = conn.cursor()
   user = selectValue("username", username)
   if user:
      flash("That username is already taken.")
      return redirect("/")
   c.execute("""INSERT INTO User(username, password) VALUES (?, ?)""", (username, bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())))
   conn.commit()
   session['username'] = username
   return redirect("/accountsetup/")

@app.route('/logout/')
def logout():
    if "username" in session:
        session.pop("username")
    return redirect("/")

@app.route('/user/<name>/')
def user_info(name):
    c = conn.cursor()
    user = selectValue("*", name.capitalize())
    #user = c.execute("""SELECT * from User where username=? LIMIT 1""",
                        #(name.capitalize(),)).fetchone()
    if user is None:
        return redirect('/')
    return render_template("user.html", user=user)

def controlStringToInt(string):
    if string == "everyone":
        return 2
    if string == "fof":
        return 1
    if string == "friends":
        return 0

@app.route("/control_change", methods=["POST"])
def control_change():
    #values as color;age;gender
    values = request.form.getlist("control")

    value_list = values[0].split(';')
    print(value_list)
    permissions = 0
    for v in value_list:
        permissions = permissions + controlStringToInt(v)
        permissions = permissions * 10
    permissions = permissions/10

    user = session['username']

#TODO insert permissions into user

    return "", 200

if __name__ == '__main__':
    app.run(debug=debug, port=8080)    
