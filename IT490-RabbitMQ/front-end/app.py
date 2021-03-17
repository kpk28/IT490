from flask import Flask, render_template, request, session, redirect
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
import logging
import messaging
import os
import requests

app = Flask(__name__)
app.secret_key = os.environ['FLASK_SECRET_KEY'] 

logging.basicConfig(level=logging.INFO)

# tag::login_required[]
def login_required(f):
    """
    Decorator that returns a redirect if session['email'] is not set
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function
# end::login_required[]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/secret')
@login_required
def secret():
    return render_template('secret.html')
    
# tag::register[] 
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        msg = messaging.Messaging()
        msg.send(
            'REGISTER',
            {
                'email': email,
                'hash': generate_password_hash(password)
            }
        )
        response = msg.receive()
        if response['success']:
            session['email'] = email
            return redirect('/')
        else:
            return f"{response['message']}"
    return render_template('register.html')
# end::register[] 

# tag::login[] 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        msg = messaging.Messaging()
        msg.send('GETHASH', { 'email': email })
        response = msg.receive()
        if response['success'] != True:
            return "Login failed."
        if check_password_hash(response['hash'], password):
            session['email'] = email
            return redirect('/')
        else:
            return "Login failed."
    return render_template('login.html')
# end::login[] 

# Experimenting =3
def requestPlayerData(region, player, apikey):
    # This is my code; Nobody elses ;3
    URL = "https://" + region + ".api.riotgames.com/lol/summoner/v4/summoners/by-name/" + player + "?api_key=" + apikey
    print(URL)
    #requests.get is a function given to us my our import "requests". It basically goes to the URL we made and gives us back a JSON.
    response = requests.get(URL)
    #Here I return the JSON we just got.
    return response.json()
    
# This is my code ;3
def requestRankedData(region, ID, APIKey):
    URL = "https://" + region + ".api.riotgames.com/lol/league/v4/entries/by-summoner/" + ID + "?api_key=" + APIKey
    print(URL)
    print('\n')
    response = requests.get(URL)
    return response.json()
    
# Experimenting =3
# $tag::index[]
@app.route('/', methods=['GET', 'POST'])
def index1():
    if request.method == 'POST':
        # Get Player Data
        region = request.form['region']
        player = request.form['player']
        apikey = request.form['apikey']
        playerDataURL = requestPlayerData(region, player, apikey)
        ID = playerDataURL['id']
        accountId = playerDataURL['accountId']
        puuid = playerDataURL['puuid']
        summonerLevel = playerDataURL['summonerLevel']
        
        # Get Ranked Data
        rankedData = requestRankedData(region, ID, apikey)
        tier = rankedData[0]['tier']
        rank = rankedData[0]['rank']
        leaguePoints = rankedData[0]['leaguePoints']
        
        # Send everything to playerResults.html
        return render_template("playerResults.html", 
            pid = ID,
            acctID = accountId,
            puid = puuid,
            level = summonerLevel,
            tr = tier, 
            rk = rank, 
            lp = leaguePoints)
        
# end::index[]

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect('/')
