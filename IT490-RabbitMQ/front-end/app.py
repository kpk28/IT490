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

# Index Page, Load the index.html page (which is now the tft lookup HTML)
# $tag::index[]
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tft')
def tftIndex():
    return render_template('tftindex.html')

# This one will be for TFT, but is temporarily set to the index HTML
@app.route('/tft', methods=['GET', 'POST'])
def processTFTResults():
    if request.method == 'POST':
        playerTFTDataResponseCode = 200
        rankedTFTDataResponseCode = 200
        region = request.form['region']
        player = request.form['player']
        apikey = request.form['apikey']
        playerTFTDataArr = {}
        rankedTFTDataArr = {}
        procTFTMatchHistoryDict = {}
        inTFT = 'TFT' # Determines that we're sending from the TFT class
        matchId = ""
        
        #---Player Data---#
        
        # 1) Request TFT Player JSON Data
        playerTFTData = requestPlayerData(region, player, apikey)
        
        # 2) Check TFT Player JSON Data
        checkPlayerData(playerTFTData, playerTFTDataResponseCode)
        
        # 3) Process TFT Player Data
        playerTFTDataArr = processPlayerData(playerTFTData)
        
        #---Ranked Data---#
        
        # 4) Request TFT Ranked JSON Data
        rankedTFTData = requestRankedData(region, playerTFTDataArr['ID'], apikey, inTFT)
        
        # 5) Check TFT Ranked JSON Data
        rankedTFTDataResponseCode = checkRankedData(rankedTFTData, rankedTFTDataResponseCode)
        
        # 6) Process TFT Ranked Data
        if rankedTFTDataResponseCode == 200:
            rankedTFTDataArr = processRankedData(rankedTFTData)
        
        #---Match History--#
        
        # TFT 1) Get Most Recent Match ID
        matchId = requestMatchID(playerTFTDataArr['puuid'], apikey)
        
        # TFT 2) Get Most Recent Match History w/ Match ID
        matchHistory = requestMatchHistory(matchId, apikey)
        
        # TFT 3) Process Match History
        procTFTMatchHistoryDict = processMatchHistory(matchHistory, region, apikey)
        
        return render_template("playerTFTResults.html", 
            pid = "Player ID : " + playerTFTDataArr['ID'],
            acctID = "Account ID : " + playerTFTDataArr['accountId'],
            puid = "Player Universely Unique Identifier : " + playerTFTDataArr['puuid'],
            level = "Summoner Level : " + str(playerTFTDataArr['summonerLevel']),
            tr1 = "Tier Rank for TFT: " + str(rankedTFTDataArr['tier']), 
            rk1 = str(rankedTFTDataArr['rank']),  
            lp1 = "LP : " + str(rankedTFTDataArr['leaguePoints']),
            playerName = str(playerTFTDataArr['name']),
            TFTParticipantAndChampions = procTFTMatchHistoryDict)
            
# TFT 1) Get Most Recent Match ID
def requestMatchID(puuid, apikey):
    # Tailored URL using given input
    URL = "https://americas.api.riotgames.com/tft/match/v1/matches/by-puuid/" + puuid + "/ids?count=1&api_key=" + apikey
    print(URL)
    response = requests.get(URL)
    return response.json()
    
# TFT 2) Get Most Recent Match History w/ Match ID
def requestMatchHistory(matchId, apikey):
    # Tailored URL using given input
    URL = "https://americas.api.riotgames.com/tft/match/v1/matches/" + matchId[0] + "?api_key=" + apikey
    print(URL)
    response = requests.get(URL)
    return response.json()
    
# TFT 3) Process Match History
def processMatchHistory(matchHistory, region, apikey):
    participantAndChampions = {}
    
    for player in matchHistory['info']['participants']:
        championsArr = [] # Clear the array for the next round of champions
        TFTPlayerData = requestTFTPlayerData(region, str(player['puuid']), apikey)
        placement = processPlacement(player['placement'])
        Player = str(TFTPlayerData['name']) + " : Level " + str(player['level']) + " : " + str(placement)
        for unit in player['units']:
            string = str(unit['character_id'])
            if "TFT4_" in string:
                string = string[5:]
            elif "TFT4b_" in string:
                string = string[6:]
            Champion = "Tier " + str(unit['tier']) + " " +  string
            championsArr.append(Champion)
        participantAndChampions[Player] = championsArr # Each Player will have an array of strings detailing Champions and their tiers
        
    return participantAndChampions  

# TFT 3.5) Get Player JSON Data (based on puuid)
def requestTFTPlayerData(region, puuid, apikey):
    # Tailored URL using given input
    URL = "https://" + region + ".api.riotgames.com/tft/summoner/v1/summoners/by-puuid/" + puuid + "?api_key=" + apikey
    print(URL)
    response = requests.get(URL)
    return response.json()
    
# TFT 3.6) Shawn made me make this.
def processPlacement(placement):
    if placement == 1:
        placeNo = str(placement) + "st place"
        return placeNo
    elif placement == 2:
        placeNo = str(placement) + "nd place"
        return placeNo
    elif placement == 3:
        placeNo = str(placement) + "rd place"
        return placeNo
    else:
        placeNo = str(placement) + "th place"
        return placeNo
              
# $tag::processResults[]
@app.route('/league', methods=['GET'])
# This is where the magic happens #
# Use the POST method to process all data and render the results page
def leagueIndex():
    return render_template('leagueindex.html')

@app.route('/league', methods=['POST'])
def processResults():
    if request.method == 'POST':
        playerDataResponseCode = 200 # Error Code for Player Data, If Player exists (200), If Player doesn't exist (404)
        rankedDataResponseCode = 200 # Error Code for Ranked Data, If Ranked data exists (200), If Ranked data doesn't exist (0)
        spectatorDataResponseCode = 200 # Error Code for Spectator Data, If Player is CURRENTLY in a game (200), If Player is NOT in a game (404)
        region = request.form['region']
        player = request.form['player']
        apikey = request.form['apikey']
        playerDataArr = {} # Array for Player Data
        rankedDataArr = {} # Array for Ranked Data
        spectatorDataArr = {} # Array for Spectator Data
        redTeam = {}
        blueTeam = {}
        inWhere = 'League'
        
        #---Player Data---#
        
        # 1) Request Player JSON Data
        playerData = requestPlayerData(region, player, apikey)
        
        # 2) Check Player Data
        checkPlayerData(playerData, playerDataResponseCode)        
        
        # 3) Process Player Data
        playerDataArr = processPlayerData(playerData)
        
        #---Ranked Data---#
        
        # 4) Request Ranked JSON Data
        rankedData = requestRankedData(region, playerDataArr['ID'], apikey, inWhere)
        
        # 5) Check Ranked JSON Data
        rankedDataResponseCode = checkRankedData(rankedData, rankedDataResponseCode)
        
        # 6) Process Ranked Data
        if rankedDataResponseCode == 200:
            rankedDataArr = processRankedData(rankedData)
            
        #---Spectator Data---#
        
        # 7) Request Spectator JSON Data
        spectatorData = requestSpectatorData(region, playerDataArr['ID'], apikey, inWhere)
        
        # 8) Check Spectator JSON Data
        spectatorDataResponseCode = checkSpectatorData(spectatorData, spectatorDataResponseCode)
        
        # 9) Process Spectator Data
        if spectatorDataResponseCode == 200:
            spectatorDataArr = processSpectatorData(spectatorData, redTeam, blueTeam)

        # 10) Render and return results
        return renderResults(playerDataArr, rankedDataArr, spectatorDataArr, playerDataResponseCode, rankedDataResponseCode, spectatorDataResponseCode)                       
        
# 1) Get Player JSON Data (Summoner V4)
def requestPlayerData(region, player, apikey):
    # Tailored URL using given input
    URL = "https://" + region + ".api.riotgames.com/lol/summoner/v4/summoners/by-name/" + player + "?api_key=" + apikey
    print(URL)
    response = requests.get(URL)
    return response.json()
    
# 2) Check Player Data
#    Check if the player exists, if NOT, return render playerResult.html with error
def checkPlayerData(playerData, playerDataResponseCode):
    #   If the player doesn't exist, return error
        try:
            if playerData['status']['status_code'] == 404:
                return render_template('/playerResults.html',
                    playerDataError = playerData['status']['message'])    
        except:
            print("Error")
            
# 3) Set Player Data
def processPlayerData(playerData):
    #   Set all the player data in the 'playerData' Array
    procPlayerData = { 
        'ID' : playerData['id'],
        'accountId' : playerData['accountId'], 
        'puuid' : playerData['puuid'], 
        'summonerLevel' : playerData['summonerLevel'], 
        'name' : playerData['name'] }
    return procPlayerData
    
# 4) Get Ranked Data (League V4)
def requestRankedData(region, ID, APIKey, inWhere):
    # Tailored URL using given input
    if inWhere == 'TFT':
        URL = "https://" + region + ".api.riotgames.com/tft/league/v1/entries/by-summoner/" + ID + "?api_key=" + APIKey
        print(URL)
        print('\n')
        response = requests.get(URL)
        return response.json()
    elif inWhere == 'League':
        URL = "https://" + region + ".api.riotgames.com/lol/league/v4/entries/by-summoner/" + ID + "?api_key=" + APIKey
        print(URL)
        print('\n')
        response = requests.get(URL)
        return response.json()

# 5) Check Ranked Data
def checkRankedData(rankedData, rankedDataResponseCode):
    # Check if Ranked Data JSON Data is empty
    try:
        if rankedData == []:
            rankedDataResponseCode = 0
    except:
        print("Player is Ranked")
    return rankedDataResponseCode

# 6) Process Ranked Data
def processRankedData(rankedData):
    # Return array of details from the JSON Data
    if rankedData[0]['queueType'] == "RANKED_FLEX_SR":
        procRankedData = {
            'tier1' : rankedData[0]['tier'],
            'rank1' : rankedData[0]['rank'],
            'tier2' : rankedData[1]['tier'],
            'rank2' : rankedData[1]['rank'],
            'leaguePoints1' : rankedData[0]['leaguePoints'],
            'leaguePoints2' : rankedData[1]['leaguePoints'] }
    elif rankedData[0]['queueType'] == "RANKED_TFT":
        procRankedData = {
            'tier' : rankedData[0]['tier'],
            'rank' : rankedData[0]['rank'],
            'leaguePoints' : rankedData[0]['leaguePoints'] }
    else:
        procRankedData = {
            'tier1' : 'Not Ranked',
            'rank1' : '',
            'tier2' : rankedData[0]['tier'],
            'rank2' : rankedData[0]['rank'],
            'leaguePoints1' : 'Not Ranked',
            'leaguePoints2' : rankedData[0]['leaguePoints'] }
    #procRankedData = [tier1, rank1, tier2, rank2, leaguePoints1, leaguePoints2]
    return procRankedData
        
# 7) Get Spectator JSON Data (Spectator V4) 
def requestSpectatorData(region, ID, APIKey, inWhere):
    # Tailored URL using given input
    URL = "https://" + region + ".api.riotgames.com/lol/spectator/v4/active-games/by-summoner/" + ID + "?api_key=" + APIKey
    print(URL)
    print('/n')
    response = requests.get(URL)
    return response.json()
    
# 8) Check Spectator Data
def checkSpectatorData(spectatorData, spectatorDataResponseCode):
    try:
        if spectatorData['status']['status_code'] == 404:
            spectatorDataResponseCode = spectatorData['status']['status_code']
    except:
        print('Player is currently in a game')
    return spectatorDataResponseCode
        
# 9) Process Spectator Data
def processSpectatorData(spectatorData, redTeam, blueTeam):
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
    procSpectatorData = { 
        'gameLength' : str(datetime.timedelta(seconds=spectatorData['gameLength']+150)),
        'gameMode' : spectatorData['gameMode'],
        'gameMap' : gameMap,
        'redTeam' : redTeam,
        'blueTeam' : blueTeam }
    return procSpectatorData

# 9.5) Requesting from Data Dragon
def champ_name(champ_id, dictionary):
    for item in list(dictionary["data"].keys()):
        if int(dictionary["data"][item]["key"]) == int(champ_id):
            return item
    return "champion does not exist"  
        
# 10) Render the page based on the conditions method
def renderResults(playerDataArr, rankedDataArr, spectatorDataArr, playerDataResponseCode, rankedDataResponseCode, spectatorDataResponseCode):
#  If there is a player, they are Ranked, BUT they are not currently in a game
    if playerDataResponseCode == 200 and rankedDataResponseCode == 200 and spectatorDataResponseCode == 404:
        return render_template("playerResults.html", 
            pid = "Player ID : " + playerDataArr['ID'],
            acctID = "Account ID : " + playerDataArr['accountId'],
            puid = "Player Universely Unique Identifier : " + playerDataArr['puuid'],
            level = "Summoner Level : " + str(playerDataArr['summonerLevel']),
            tr1 = "Tier Rank for Flex: " + rankedDataArr['tier1'], 
            rk1 = rankedDataArr['rank1'], 
            tr2 = "Tier Rank for Solo/Duo: " + rankedDataArr['tier2'], 
            rk2 = rankedDataArr['rank2'], 
            lp1 = "LP : " + str(rankedDataArr['leaguePoints1']),
            lp2 = "LP : " + str(rankedDataArr['leaguePoints2']),
            playerName = playerDataArr['name'],
            spectatorError = "Player is not currently in a game: Error " + str(spectatorDataResponseCode))
    #  If there is a player, they are Ranked, they are currently in a game
    elif playerDataResponseCode == 200 and rankedDataResponseCode == 200 and spectatorDataResponseCode == 200:
        return render_template("playerResults.html", 
            pid = "Player ID : " + playerDataArr['ID'],
            acctID = "Account ID : " + playerDataArr['accountId'],
            puid = "Player Universely Unique Identifier : " + playerDataArr['puuid'],
            level = "Summoner Level : " + str(playerDataArr['summonerLevel']),
            tr1 = "Tier Rank for Flex: " + rankedDataArr['tier1'], 
            rk1 = rankedDataArr['rank1'], 
            tr2 = "Tier Rank for Solo/Duo: " + rankedDataArr['tier2'], 
            rk2 = rankedDataArr['rank2'],  
            lp1 = "LP : " + str(rankedDataArr['leaguePoints1']),
            lp2 = "LP : " + str(rankedDataArr['leaguePoints2']),
            gL = "Current Game Time : " + spectatorDataArr['gameLength'],
            gM = "Map : " + spectatorDataArr['gameMap'],
            rT = "Red Team : " + str(spectatorDataArr['redTeam']),
            bT = "Blue Team : " + str(spectatorDataArr['blueTeam']),
            playerName = playerDataArr['name'])
    #  If there is a player, they are NOT Ranked, they are currently in a game
    elif playerDataResponseCode == 200 and rankedDataResponseCode == 0 and spectatorDataResponseCode == 200:
        return render_template("playerResults.html", 
            pid = "Player ID : " + playerDataArr['ID'],
            acctID = "Account ID : " + playerDataArr['accountId'],
            puid = "Player Universely Unique Identifier : " + playerDataArr['puuid'],
            level = "Summoner Level : " + str(playerDataArr['summonerLevel']),
            rankedError = "Player is not ranked : Error "+ str(rankedDataResponseCode),
            gL = "Current Game Time : " + spectatorDataArr['gameLength'],
            gM = "Map : " + spectatorDataArr['gameMap'],
            rT = "Red Team : " + str(spectatorDataArr['redTeam']),
            bT = "Blue Team : " + str(spectatorDataArr['blueTeam']),
            playerName = playerDataArr['name'])
    #  If there is a player, they are NOT Ranked, they are NOT currently in a game
    elif playerDataResponseCode == 200 and rankedDataResponseCode == 0 and spectatorDataResponseCode == 404:
        return render_template("playerResults.html", 
            pid = "Player ID : " + playerDataArr['ID'],
            playerName = playerDataArr['name'],
            acctID = "Account ID : " + playerDataArr['accountId'],
            puid = "Player Universely Unique Identifier : " + playerDataArr['puuid'],
            level = "Summoner Level : " + str(playerDataArr['summonerLevel']),
            rankedError = "Player is not ranked : Error " + str(rankedDataResponseCode),
            spectatorError = "Player is not currently in a game: Error " + str(spectatorDataResponseCode))

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

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect('/')
