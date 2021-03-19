from flask import Flask, render_template, request, session, redirect
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
import logging
import messaging
import os
import requests
import datetime
import json 
from urllib.request import urlopen

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

# Get Player Data
def requestPlayerData(region, player, apikey):
    # Tailored URL using given input
    URL = "https://" + region + ".api.riotgames.com/lol/summoner/v4/summoners/by-name/" + player + "?api_key=" + apikey
    print(URL)
    #requests.get is a function given to us my our import "requests". It basically goes to the URL we made and gives us back a JSON.
    response = requests.get(URL)
    #Here I return the JSON we just got.
    return response.json()
    
# Get Ranked Data
def requestRankedData(region, ID, APIKey):
    # Tailored URL using given input
    URL = "https://" + region + ".api.riotgames.com/lol/league/v4/entries/by-summoner/" + ID + "?api_key=" + APIKey
    print(URL)
    print('\n')
    response = requests.get(URL)
    return response.json()

# Get Spectator Data (Players that are currently in a game)    
def requestSpectatorData(region, ID, APIKey):
    # Tailored URL using given input
    URL = "https://" + region + ".api.riotgames.com/lol/spectator/v4/active-games/by-summoner/" + ID + "?api_key=" + APIKey
    print(URL)
    print('/n')
    response = requests.get(URL)
    return response.json()
    
# Requesting from Data Dragon
def champ_name(champ_id, dictionary):
        for item in list(dictionary["data"].keys()):
                if int(dictionary["data"][item]["key"]) == int(champ_id):
                        return item
        return "champion does not exist"    
    
# $tag::index1[]
@app.route('/', methods=['GET', 'POST'])
def index1():
    if request.method == 'POST':
        # Get Player Data
        playerDataResponseCode = 200
        region = request.form['region']
        player = request.form['player']
        apikey = request.form['apikey']
        playerDataURL = requestPlayerData(region, player, apikey)
        
        #  If the player doesn't exist, return error
        try:
            if playerDataURL['status']['status_code'] == 404:
                return render_template('/playerResults.html',
                    playerDataError = playerDataURL['status']['message'])    
        except:
            print("wub")
        
        ID = playerDataURL['id']
        accountId = playerDataURL['accountId']
        puuid = playerDataURL['puuid']
        summonerLevel = playerDataURL['summonerLevel']
        playerName = playerDataURL['name']
        #/End Player Data
        
        # Get Ranked Data (League V4)
        rankedDataResponseCode = 200
        rankedData = requestRankedData(region, ID, apikey)
        
        try:
            if rankedData == []:
                rankedDataResponseCode = 0
            else:
                tier = rankedData[0]['tier']
                rank = rankedData[0]['rank']
                leaguePoints = rankedData[0]['leaguePoints']
        except:
            print('There was an error requesting ranked data')
            
        #/End Get Ranked Data
        
        # Spectator Data (Spectator V4)
        spectatorDataResponseCode = 200
        redTeam = {}
        blueTeam = {}
        spectatorData = requestSpectatorData(region, ID, apikey)
        
        try:
            if spectatorData['status']['status_code'] == 404:
                spectatorDataResponseCode = spectatorData['status']['status_code']
        except:
            for i in range(10):
                summonerName = spectatorData['participants'][i]['summonerName']
                teamId = spectatorData['participants'][i]['teamId']
                championId = spectatorData['participants'][i]['championId']
                url = "https://ddragon.leagueoflegends.com/cdn/11.6.1/data/en_US/champion.json"
                json_url = urlopen(url)
                data = json.loads(json_url.read())
                championName = champ_name(championId, data)
                gameLength = str(datetime.timedelta(seconds=spectatorData['gameLength']+150))
                gameMode = spectatorData['gameMode']
                gameMap = ""

                if(teamId == 100):
                    blueTeam[summonerName] = championName
                else:
                    redTeam[summonerName] = championName

                if(gameMode == "CLASSIC"):
                    gameMap = "Game Map : " + "Summoner's Rift"
                else:
                    gameMap = "Game Map : " + "Howling Abyss"
        #/End Spectator Data
            
        # Send everything to playerResults.html
        
        #  If there is a player, they are Ranked, BUT they are not currently in a game
        if playerDataResponseCode == 200 and rankedDataResponseCode == 200 and spectatorDataResponseCode == 404:
            return render_template("playerResults.html", 
                pid = "Player ID : " + ID,
                acctID = "Account ID : " + accountId,
                puid = "Player Universely Unique Identifier : " + puuid,
                level = "Summoner Level : " + str(summonerLevel),
                tr = "Tier Rank : " + tier, 
                rk = rank, 
                lp = "LP : " + str(leaguePoints),
                pN = playerName,
                spectatorError = "Player is not currently in a game: Error " + str(spectatorDataResponseCode))
        #  If there is a player, they are Ranked, they are currently in a game
        elif playerDataResponseCode == 200 and rankedDataResponseCode == 200 and spectatorDataResponseCode == 200:
            return render_template("playerResults.html", 
                pid = "Player ID : " + ID,
                acctID = "Account ID : " + accountId,
                puid = "Player Universely Unique Identifier : " + puuid,
                level = "Summoner Level : " + str(summonerLevel),
                tr = "Tier Rank : " +  tier, 
                rk = rank, 
                lp = "LP : " + str(leaguePoints),
                sN = "Summoner Name : " + summonerName,
                gL = "Current Game Time : " + gameLength,
                gM = "Map : " + gameMap,
                rT = "Red Team : " + str(redTeam),
                bT = "Blue Team : " + str(blueTeam),
                pN = playerName)
        #  If there is a player, they are NOT Ranked, they are currently in a game
        elif playerDataResponseCode == 200 and rankedDataResponseCode == 0 and spectatorDataResponseCode == 200:
            return render_template("playerResults.html", 
                pid = "Player ID : " + ID,
                acctID = "Account ID : " + accountId,
                puid = "Player Universely Unique Identifier : " + puuid,
                level = "Summoner Level : " + str(summonerLevel),
                rankedError = "Player is not ranked : Error "+ str(rankedDataResponseCode),
                sN = "Summoner Name : " + summonerName,
                gL = "Current Game Time : " + gameLength,
                gM = "Map : " + gameMap,
                rT = "Red Team : " + str(redTeam),
                bT = "Blue Team : " + str(blueTeam),
                pN = playerName)
        #  If there is a player, they are NOT Ranked, they are NOT currently in a game
        elif playerDataResponseCode == 200 and rankedDataResponseCode == 0 and spectatorDataResponseCode == 404:
            return render_template("playerResults.html", 
                pid = "Player ID : " + ID,
                pN = playerName,
                acctID = "Account ID : " + accountId,
                puid = "Player Universely Unique Identifier : " + puuid,
                level = "Summoner Level : " + str(summonerLevel),
                rankedError = "Player is not ranked : Error " + str(rankedDataResponseCode),
                spectatorError = "Player is not currently in a game: Error " + str(spectatorDataResponseCode))               
# end::index1[]

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect('/')
