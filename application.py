from flask import Flask, render_template, url_for, request, redirect, jsonify, make_response, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Genres, Games, Users
from flask import session as login_session
import random, string, json, httplib2, requests
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError

app = Flask(__name__)

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine


'''Start a DB session'''
DBSession = sessionmaker(bind=engine)
session = DBSession()

'''Function to creat a new user'''
def createUser(login_session):

    newUser = Users(name=login_session['username'], email=login_session['email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(Users).filter_by(email=login_session['email']).one()
    return user.id

'''Function to get users ID used later in the code'''
def getUserInfo(user_id):

    user = session.query(Users).filter_by(id=user_id).one()
    return user

'''Function to get the users email and also used later in the code'''
def getUserID(email):
    try:
        user = session.query(Users).filter_by(email=email).one()
        return user.id
    except:
        return None

'''This will fetch Genres and Games to render and populate home.html'''
@app.route('/')
@app.route('/catalog')
def showGenres():

	genres = session.query(Genres).all()
	genreGames = session.query(Games).all()
	return render_template('home.html', genres = genres, games = genreGames)

'''This will let the user create a new genre'''
@app.route('/catalog/addgenre', methods=['GET', 'POST'])
def addGenre():

	if 'username' not in login_session:
		return redirect('/login')
	if request.method == "POST":
		'''If you don't input a name for the genre a flash is generated and shown'''
		if not request.form['genre']:
			flash('genre name is mandatory')
			return redirect(url_for('addGenre'))
		'''This will check if the genre being added is already in the database'''
		thisGenre = request.form['genre'].capitalize()
		genres = session.query(Genres).filter_by(name = thisGenre).first()
		'''If it's not already an existing genre, add it to the DB'''
		if not genres:
			newGenre = Genres(name = thisGenre, user_id = 1)
			session.add(newGenre)
			session.commit()	

		return redirect(url_for('addGame'))

	else:
		genres = session.query(Genres).all()
		return render_template('addGenre.html', genres = genres)

'''This will show all the games for a particular genre based off it's ID'''
@app.route('/catalog/<int:catalog_id>')
@app.route('/catalog/<int:catalog_id>/items')
def showGenre(catalog_id):
	'''Get all the Data needed and render it all in template'''
	genres = session.query(Genres).all()
	genre = session.query(Genres).filter_by(id = catalog_id).first()
	genreName = genre.name
	games = session.query(Games).filter_by(genre_id = catalog_id).all()
	gameCount = session.query(Games).filter_by(genre_id = catalog_id).count()
	return render_template('genre.html', genres = genres, games = games, genreName = genreName, gamesCount = gameCount)

'''This will let the user add a new game to the list'''
@app.route('/catalog/add', methods=['GET', 'POST'])
def addGame():
	'''Make sure user is logged in'''
	if 'username' not in login_session:
	    return redirect('/login')
	if request.method == 'POST':
		'''These will force the user to add name and description'''
		if not request.form['name']:
			flash('name is mandatory')
			return redirect(url_for('addGame'))
		if not request.form['description']:
			flash('description is mandatory')
			return redirect(url_for('addGame'))

		'''Create a new entry in Games table'''
		newGames = Games(name = request.form['name'], description = request.form['description'], genre_id = request.form['genre'], user_id = login_session['user_id'])
		session.add(newGames)
		session.commit()
		return redirect(url_for('showGenres'))
	else:
		'''This will just render the addGame html'''
		genres = session.query(Genres).all()
		return render_template('addGame.html', genres = genres)

'''This will show a particular game along with the description'''
@app.route('/catalog/<int:catalog_id>/items/<int:item_id>')
def showGame(catalog_id, item_id):
	'''Get all the Data needed and render it all in template. Creator is used to display edit/delete'''
	game = session.query(Games).filter_by(id = item_id).first()
	creator = getUserInfo(game.user_id)
	return render_template('game.html', game = game, creator = creator)

'''This will let an authorized user edit a game'''
@app.route('/catalog/<int:catalog_id>/items/<int:item_id>/edit', methods=['GET', 'POST'])
def editGame(catalog_id, item_id):
	'''Make sure user is logged in'''
	if 'username' not in login_session:
	    return redirect('/login')

	game = session.query(Games).filter_by(id = item_id).first()

	'''Make sure user is authorized to edit this game'''
	creator = getUserInfo(game.user_id)
	if creator.id != login_session['user_id']:
		return redirect('/login')

	genres = session.query(Genres).all()
	if request.method == 'POST':
		'''Again this will check for both name and description'''
		if not request.form['name']:
			flash('Name is mandatory')
			return redirect(url_for('editGame', catalog_id = catalog_id, item_id = item_id))
		if not request.form['description']:
			flash('description is mandatory')
			return redirect(url_for('editGame', catalog_id = catalog_id, item_id = item_id))
		'''This will update the data'''
		if request.form['name']:
			game.name = request.form['name']
		if request.form['description']:
			game.description = request.form['description']
		if request.form['genre']:
			game.genre_id = request.form['genre']
		return redirect(url_for('showGame', catalog_id = game.genre_id ,item_id = game.id))
	else:
		return render_template('editGame.html', genres = genres, game = game)

'''This will allow an authorized user delete a game'''
@app.route('/catalog/<int:catalog_id>/items/<int:item_id>/delete', methods=['GET', 'POST'])
def deleteGame(catalog_id, item_id):
	'''Make sure user is logged in'''
	if 'username' not in login_session:
	    return redirect('/login')

	game = session.query(Games).filter_by(id = item_id).first()

	'''Make sure user is authorized to delete game'''
	creator = getUserInfo(game.user_id)
	if creator.id != login_session['user_id']:
		return redirect('/login')

	'''Delete the game'''
	if request.method == 'POST':
		session.delete(game)
		session.commit()
		return redirect(url_for('showGenre', catalog_id = game.genre_id))
	else:
		return render_template('deleteGame.html', game = game)

'''This will log and logout the user using google API'''
@app.route('/login')
def login():
	state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
	login_session['state'] = state
	return render_template('login.html', STATE=state)

@app.route('/logout')
def logout():

	gdisconnect()
	del login_session['gplus_id']
	del login_session['access_token']
	del login_session['username']
	del login_session['email']
	del login_session['picture']
	del login_session['user_id']
	del login_session['provider']
	return redirect(url_for('showGenres'))

@app.route('/gconnect', methods=['POST'])
def gconnect():
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid state parameter.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	code = request.data

	try:
		oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
		oauth_flow.redirect_uri = 'postmessage'
		credentials = oauth_flow.step2_exchange(code)
	except FlowExchangeError:
		response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	access_token = credentials.access_token
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
	h = httplib2.Http()
	result = json.loads(h.request(url, 'GET')[1])

	if result.get('error') is not None:
		response = make_response(json.dumps(result.get('error')), 500)
		response.headers['Content-Type'] = 'application/json'
		return response

	gplus_id = credentials.id_token['sub']
	if result['user_id'] != gplus_id:
		response = make_response(json.dumps("Token's user ID doesn't match given user ID."), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	if result['issued_to'] != CLIENT_ID:
		response = make_response(json.dumps("Token's client ID does not match app's."), 401)
		print "Token's client ID does not match app's."
		response.headers['Content-Type'] = 'application/json'
		return response

	stored_access_token = login_session.get('access_token')
	stored_gplus_id = login_session.get('gplus_id')

	if stored_access_token is not None and gplus_id == stored_gplus_id:
		response = make_response(json.dumps('Current user is already connected.'), 200)
		response.headers['Content-Type'] = 'application/json'
		return response

	login_session['access_token'] = credentials.access_token
	login_session['gplus_id'] = gplus_id
	userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
	params = {'access_token': credentials.access_token, 'alt': 'json'}
	answer = requests.get(userinfo_url, params=params)
	data = answer.json()
	login_session['username'] = data['name']
	login_session['picture'] = data['picture']
	login_session['email'] = data['email']
	login_session['provider'] = 'google'
	user_id = getUserID(data["email"])
	if not user_id:
	    user_id = createUser(login_session)
	login_session['user_id'] = user_id

	return "Login Successful"

'''Logout user'''
@app.route('/gdisconnect')
def gdisconnect():
	access_token = login_session.get('access_token')
	if access_token is None:
		response = make_response(json.dumps('Current user not connected.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
	h = httplib2.Http()
	result = h.request(url, 'GET')[0]

	if result['status'] != '200':
	    response = make_response(json.dumps('Failed to revoke token for given user.'), 400)
	    response.headers['Content-Type'] = 'application/json'
	    return response

'''Return JSON of genres'''
@app.route('/catalog/JSON')
def showCategoriesJSON():
	genres = session.query(Genres).all()
	return jsonify(genres = [genre.serialize for genre in genres])

'''Return JSON of Games for given Genre'''
@app.route('/catalog/<int:catalog_id>/JSON')
@app.route('/catalog/<int:catalog_id>/items/JSON')
def showGenreJSON(catalog_id):
	games = session.query(Games).filter_by(genre_id = catalog_id).all()
	return jsonify(games = [games.serialize for games in games])

'''Return JSON of a certain Game data'''
@app.route('/catalog/<int:catalog_id>/items/<int:item_id>/JSON')
def showGameJSON(catalog_id, item_id):
	games = session.query(Games).filter_by(id = item_id).first()
	return jsonify(games = [games.serialize])

if __name__ == '__main__':
	app.debug = True 
	app.secret_key = 'i_can_count_to_potatoe'
	app.run(host = '0.0.0.0', port = 5000)