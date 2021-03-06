#!/usr/bin/env python
from flask import Flask, render_template, redirect, url_for, request, session
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
from hashlib import md5
import os
import logging
from sqlalchemy.orm import sessionmaker
import pandas as pd 

app = Flask(__name__)
app.secret_key = 'secret'
logging.basicConfig(filename='example.log',level=logging.DEBUG)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'movies'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


def recommend(user):
	cur = mysql.connection.cursor()

	cur.execute("SELECT actor_id from actors, favorites where actors.movie_id = favorites.movie_id and user_id=\'{}\';".format(user))
	actors = [ x['actor_id'] for x in cur.fetchall() ]

	cur.execute("SELECT genre from movies, favorites where movies.movie_id = favorites.movie_id and user_id=\'{}\';".format(user))
	genres = [ x['genre'] for x in cur.fetchall()]

	cur.execute("SELECT director from directors, favorites where directors.movie_id = favorites.movie_id and user_id=\'{}\';".format(user))
	directors = [ x['director'] for x in cur.fetchall()]

	cur.execute("SELECT movie_id from favorites where user_id=\'{}\';".format(user))
	favorites = [ x['movie_id'] for x in cur.fetchall()]


	format_strings = ','.join(['%s']*len(genres))
	cur.execute("SELECT movie_id from movies where genre IN (%s)" % format_strings, tuple(genres))
	temp_genres = [x['movie_id'] for x in cur.fetchall()]

	format_strings = ','.join(['%s']*len(actors))
	cur.execute("SELECT movie_id from actors where actor_id in (%s)" % format_strings, tuple(actors))
	temp_actors = [x['movie_id'] for x in cur.fetchall()]

	format_strings = ','.join(['%s']*len(directors))
	cur.execute("SELECT movie_id from directors where director in(%s)" % format_strings, tuple(directors))
	temp_directors = [x['movie_id'] for x in cur.fetchall()]
	
	cur.close()




	all_movies = temp_genres + temp_actors + temp_directors
	all_points = [20]*len(temp_genres) + [30] * len(temp_actors) + [50] * len(temp_directors)

	df1 = pd.DataFrame( {'movie_id': all_movies, 'points': all_points})
	df2 = df1.groupby('movie_id')['points'].sum()
	df3 = df2.reset_index()
	df4 = df3[~df3['movie_id'].isin(favorites)]


	recommendedMovies = df4.sort_values(by=['points'], ascending=False)['movie_id'][:5].tolist()

	return recommendedMovies
	#return []
 
@app.route('/')
def home():
    if 'username' not in session:
        return render_template('login.html')

    username_session = (session['username']).capitalize()
    #username_session = escape(session['username']).capitalize()
    return render_template('index2.html', session_user_name=username_session)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return render_template('index2.html')

    error = None
    try:
        if request.method == 'POST':
	    username_form  = request.form['username']
	    #password_form = sha256_crypt.hash(str(request.form['password']))
            password_form = request.form['password']
            cur = mysql.connection.cursor()
	    cur.execute('SELECT username FROM user WHERE username = "{}";'.format(username_form))
	    if not cur.fetchone():
	        raise Exception('Invalid username')
	    else:
	        cur.execute('SELECT password FROM user WHERE username = "{}" AND password = "{}";'.format(username_form, password_form))
	        if cur.fetchone():
		    cur.close()
	            session['username'] = username_form
	            return render_template('index2.html')
                cur.close()
                raise Exception(password_form)
	    #raise Exception('Invalid password')
    except Exception as e:
        error = str(e)

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return render_template('login.html')

@app.route('/register', methods = ['GET'])
def register():
    return render_template('register.html')

@app.route('/registration', methods = ['POST'])
def registration():
    POST_USERNAME = str(request.form['username'])
    POST_PASSWORD = str(request.form['password'])
    cur = mysql.connection.cursor()
    error = None
    cur.execute(('SELECT 1 FROM user WHERE username="{}";').format(POST_USERNAME))
    if cur.fetchone():
        error = "username already exists"
        cur.close()
        return render_template('register.html', error=error)
    else:
        try:
		cur.execute(("INSERT INTO user (username, password) VALUES ('{}', '{}');").format(POST_USERNAME, POST_PASSWORD))
	except Exception as e:
		error = "password is not at least 6 characters long"
		cur.close()
		return render_template('register.html', error=error)
	mysql.connection.commit()
	cur.close()
        return render_template('login.html')

@app.route('/genrecs', methods = ['GET'])
def genrecs():
	rows = []
	movierecs = []
	with app.app_context():
		if 'username' not in session:
			return render_template('login.html')
		current_user = session['username']
		movierecs = recommend(current_user)
		cur = mysql.connection.cursor()
        	cur.execute("start transaction;")
		cur.execute(("delete from recommended where user_id = '{}';").format(current_user))
		for movie in movierecs:
			cur.execute(("INSERT INTO recommended (user_id, movie_id) VALUES ('{}', '{}');").format(current_user, movie))
		#cur.execute("commit;")
		mysql.connection.commit()
		cur.execute(("SELECT title, year_released, movies.movie_id, full_name as director, rating FROM movies, directors, ratings, names, recommended WHERE recommended.user_id = '{}' AND movies.movie_id = recommended.movie_id and movies.movie_id = directors.movie_id AND DIRECTOR = name_id AND movies.movie_id = ratings.movie_id;").format(session['username']))
		#cur.execute(("SELECT title FROM movies, recommended where user_id = '{}' AND movies.movie_id = recommended.movie_id;").format(current_user))
	        rows = cur.fetchall()
	
		cur.close()	
		return render_template('showmovies.html', data=rows)
@app.route('/showrecs', methods = ['GET'])
def showrecs():
	rows = []
	
        if 'username' not in session:
                return render_template('login.html')
        cur = mysql.connection.cursor()
        cur.execute(("SELECT title, year_released, movies.movie_id, full_name as director, rating FROM movies, directors, ratings, names, recommended WHERE recommended.user_id = '{}' AND movies.movie_id = recommended.movie_id and movies.movie_id = directors.movie_id AND DIRECTOR = name_id AND movies.movie_id = ratings.movie_id;").format(session['username']))
        rows = cur.fetchall()
        cur.close()
	return render_template('showmovies.html', data=rows)


@app.route('/showmovies', methods = ['GET'])
def showmovies():
	with app.app_context():
		if 'username' not in session:
			return render_template('login.html')
		moviesearch = request.args.get('movie')
		cur = mysql.connection.cursor()
		cur.execute(("select title, year_released, movies.movie_id, full_name as director, rating from movies, directors, ratings, names where movies.movie_id = directors.movie_id AND DIRECTOR = name_id AND movies.movie_id = ratings.movie_id AND title LIKE '%{}%';").format(moviesearch))
		rows = cur.fetchall()
		cur.close()
		return render_template('showmovies.html', data=rows)

@app.route('/showfavorites', methods = ['GET'])
def showfavorites():
	with app.app_context():
                cur = mysql.connection.cursor()
                #cur.execute(("select DISTINCT title, movies.movie_id, rating from movies, favorites where movies.movie_id = favorites.movie_id AND favorites.user_id = '{}';").format(session['username']))
		cur.execute(("call getfaves('{}');").format(session['username']))

                rows = cur.fetchall()
                cur.close()
                return render_template('showfavorites.html', data=rows)

@app.route('/addfavorites', methods = ['POST', 'GET'])
def addfavorites():
	with app.app_context():
		moviesearch = request.args.get('favmovie')
		cur2 = mysql.connection.cursor()
		cur2.execute(('SELECT 1 FROM favorites WHERE movie_id="{}" AND user_id = "{}";').format(moviesearch, session['username']))
		if not cur2.fetchone():
			cur2.execute(("INSERT INTO favorites (user_id, movie_id) VALUES ('{}', '{}');").format(session['username'], moviesearch))
		mysql.connection.commit()
		cur2.close()
		cur = mysql.connection.cursor()
		cur.execute(("select DISTINCT title, movies.movie_id, rating from movies, favorites where movies.movie_id = favorites.movie_id AND favorites.user_id = '{}';").format(session['username']))
		rows = cur.fetchall()
		cur.close()
		return render_template('showfavorites.html', data=rows)

@app.route('/removefavorites', methods = ['POST', 'GET'])
def removefavorites():
	with app.app_context():
                moviesearch = request.args.get('favmovie')
                cur2 = mysql.connection.cursor()
                cur2.execute(("DELETE FROM favorites WHERE user_id = '{}' AND movie_id = '{}';").format(session['username'], moviesearch))
                mysql.connection.commit()
                cur2.close()
                cur = mysql.connection.cursor()
                cur.execute(("select DISTINCT title, movies.movie_id, rating from movies, favorites where movies.movie_id = favorites.movie_id AND favorites.user_id = '{}';").format(session['username']))
                rows = cur.fetchall()
                cur.close()
                return render_template('showfavorites.html', data=rows)

@app.route('/ratefavorites', methods = ['POST', 'GET'])
def ratefavorites():
	with app.app_context():
                moviesearch = request.args.get('favmovie')
                movierating = request.args.get('movierating')
                cur2 = mysql.connection.cursor()
                cur2.execute(("UPDATE favorites set rating = {} WHERE user_id = '{}' AND movie_id = '{}';").format(movierating, session['username'], moviesearch))
                mysql.connection.commit()
                cur2.close()
                cur = mysql.connection.cursor()
                cur.execute(("select DISTINCT title, movies.movie_id, rating from movies, favorites where movies.movie_id = favorites.movie_id AND favorites.user_id = '{}';").format(session['username']))
                rows = cur.fetchall()
                cur.close()
                return render_template('showfavorites.html', data=rows)

@app.route('/conversations', methods = ['GET'])
def getConversations():
        with app.app_context():
                user = session['username']
                cur = mysql.connection.cursor()
                cur.execute(("SELECT * FROM (SELECT DISTINCT to_userid FROM messages WHERE (from_userid = '{}' OR to_userid = '{}') UNION SELECT DISTINCT from_userid FROM messages WHERE (from_userid = '{}' OR to_userid = '{}')) AS t WHERE t.to_userid <> '{}';").format(user, user, user, user, user))
                rows = cur.fetchall()
                cur.close()
		
		return render_template("getconversations.html", data=rows)

@app.route('/messageform', methods = ['GET'])
def messageform():
	return render_template('messageform.html')

@app.route('/sendMessage', methods = ['POST'])
def sendMessage():
        with app.app_context():
		#arguments
                sender = session['username']
		user = sender
		recipient = request.form['recipient']
		#validate the recipient username?
		body = request.form['messageBody']
		
		#post new message
                cur = mysql.connection.cursor()
		query = ("INSERT INTO messages (from_userid, to_userid, message_body) VALUES ('{}', '{}', '{}');").format(user, recipient, body)
                with open("logfile.txt", "w") as f:
                	f.write(str(query))

                cur.execute(("INSERT INTO messages (from_userid, to_userid, message_body) VALUES ('{}', '{}', '{}');").format(user, recipient, body))
		mysql.connection.commit()
                cur.close()

		#query latest messages
		cur2 = mysql.connection.cursor()
		cur2.execute(("SELECT * FROM (SELECT * FROM messages WHERE (from_userid = '{}' OR from_userid = '{}') AND (to_userid = '{}' OR to_userid = '{}') ORDER BY message_time DESC LIMIT 20) AS t  ORDER BY t.message_time;").format(user, recipient, user, recipient))
		rows = cur2.fetchall()
		cur2.close()

		return render_template('showconversation.html', data=rows, otheruser=recipient)
		
@app.route('/messages', methods = ['GET'])
def getMessages():
	with app.app_context():
		user = session['username']
		recipient = request.args.get('recipient')
		#validate the recipient username?

		#query latest messages
		cur = mysql.connection.cursor()
		cur.execute(("SELECT * FROM (SELECT * FROM messages WHERE (from_userid = '{}' OR from_userid = '{}') AND (to_userid = '{}' OR to_userid = '{}') ORDER BY message_time DESC LIMIT 20) AS t  ORDER BY t.message_time;").format(user, recipient, user, recipient))
		rows = cur.fetchall()
		cur.close()

		#return render_template('index2.html')
		return render_template('showconversation.html', data=rows, otheruser=recipient)
	


if __name__ == "__main__":
    app.secret_key = os.urandom(50)
    app.run(debug=True,host='0.0.0.0', port=4000)
