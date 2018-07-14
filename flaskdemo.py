#!/usr/bin/env python
from flask import Flask, render_template, redirect, url_for, request
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
import os

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'movies'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


@app.route('/login', methods=['POST'])
def do_admin_login():
    if request.form['password'] == 'password' and request.form['username'] == 'admin':
        session['logged_in'] = True
    else:
        flash('wrong password!')
    return index()

@app.route("/logout")
def logout():
    session['logged_in'] = False
    return index()

@app.route("/")
def index():
    if not session.get('logged_in'):
	return render_template('login.html')
    else:
    	return render_template('index2.html')

@app.route('/showmovies', methods = ['GET'])
def showmovies():
	with app.app_context():
		moviesearch = request.args.get('movie')
		cur = mysql.connection.cursor()
		cur.execute(("select title, movies.movie_id, full_name as director, rating from movies, directors, ratings, names where movies.movie_id = directors.movie_id AND DIRECTOR = name_id AND movies.movie_id = ratings.movie_id AND title LIKE '%{}%';").format(moviesearch))
		rows = cur.fetchall()
		cur.close()
		return render_template('showmovies.html', data=rows)


@app.route('/addfavorites', methods = ['POST', 'GET'])
def addfavorites():
	with app.app_context():
		moviesearch = request.args.get('favmovie')
		cur2 = mysql.connection.cursor()
		cur2.execute(("INSERT INTO favorites (user_id, movie_id) VALUES ('aa1234', '{}');").format(moviesearch))
		mysql.connection.commit()
		cur2.close()
		cur = mysql.connection.cursor()
		cur.execute(("select DISTINCT title, movies.movie_id from movies, favorites where movies.movie_id = favorites.movie_id AND favorites.user_id = 'aa1234';"))
		rows = cur.fetchall()
		cur.close()
		return render_template('showfavorites.html', data=rows)

@app.route('/removefavorites', methods = ['POST', 'GET'])
def removefavorites():
	with app.app_context():
                moviesearch = request.args.get('favmovie')
                cur2 = mysql.connection.cursor()
                cur2.execute(("DELETE FROM favorites WHERE user_id = 'aa1234' AND movie_id = '{}';").format(moviesearch))
                mysql.connection.commit()
                cur2.close()
                cur = mysql.connection.cursor()
                cur.execute(("select DISTINCT title, movies.movie_id from movies, favorites where movies.movie_id = favorites.movie_id AND favorites.user_id = 'aa1234';"))
                rows = cur.fetchall()
                cur.close()
                return render_template('showfavorites.html', data=rows)



if __name__ == "__main__":
    app.secret_key = os.urandom(50)
    app.run(debug=True,host='0.0.0.0', port=4000)

