from flask import Blueprint, request
from Models.Image import Image, GetImage
from Models.User import User, GetUser
from Models.Classification_Model import  Classification_Score_Model
import json
from Shared.Database.DatabaseFactory import DatabaseFactory, engine
from Shared.S3Service import S3Service
from Shared.SaltService import SaltService
from Shared.ClassificationService import ClassificationService
import os
from flask import render_template, session, redirect, url_for, jsonify
from flask_api import status




imageAccess = Blueprint('imageAccess', __name__)

@imageAccess.route('/api/')
def index():
    return "This is an example app"

@imageAccess.route('/api/image', methods = ['POST'])
def insert_image():
    if 'username' not in session:
        return render_template('login.html')
    data = json.loads(request.get_data())
    image = GetImage(data['ImageUrl'])
    images = []
    images.append(image)
    engine.insert(images)
    S3Service().UploadImageFromUrl(image.Image_Id, image.Image_Url)
    return json.dumps({'success':True}), 201, {'ContentType':'application/json'} 

@imageAccess.route('/api/unclassifiedimage', methods = ['GET'])
def get_image():
    if 'username' not in session:
        return redirect(url_for('imageAccess.login_screen'))
    url = GetImageFromAws()
    return render_template('image.html', url =url[0], key=url[1] )

@imageAccess.route('/api/unclassifiedimage', methods = ['POST']) ##
def post_image():

    if 'username' not in session:
        return redirect(url_for('imageAccess.login_screen'))

    post_score_to_db(
        request.form['classification'],
        request.form['hatefullClassification'],
        request.form['IsText'],
        request.form['IsHateText'],
        request.form['IsHateSymbol'],
        #request.form['Symbol'],
        'test',
        request.form['id'], 
        session['username'])

    url = GetImageFromAws()
    return redirect(url_for('imageAccess.get_image'))

def post_score_to_db(IsSwastika, IsHateful, IsText, IsHateText, IsHateSymbol, Symbol, id, username):
    engine.InsertClassificationScore(IsSwastika, IsHateful, IsText, IsHateText, IsHateSymbol, Symbol, id, username)



@imageAccess.route('/api/register', methods = ['Post'])
def register_user():
    data = json.loads(request.get_data())
    user = GetUser(data['UserName'], data['Password'])
    users = []
    users.append(user)
    engine.insert(users)
    return json.dumps({'success':True}), 201, {'ContentType':'application/json'} 

@imageAccess.route('/api/logout', methods = ['Post'])
def logout():
    if 'username' not in session:
        return json.dumps({'status': 'User is not logged in.'}),status.HTTP_403_FORBIDDEN
    else:
        session.pop('username')
    return json.dumps({'success':True}), 201, {'ContentType':'application/json'} 

@imageAccess.route('/api/login', methods = ['Post'])
def login():
    # data = json.loads(request.get_data())
    user = GetUserFromDb(request.form['UserName'], request.form['Password'])
    if(user):
        session['username'] = user.UserName
        return redirect(url_for('imageAccess.get_image')) 
    else:
        return render_template('login.html', error = "credentials not found")


@imageAccess.route('/api/login', methods = ['Get'])
def login_screen():
    return render_template('login.html')

@imageAccess.route('/api/allImages', methods = ['Get'])
def GetAllImages():
    images = engine.GetAllImages()
    dicts = list(map(lambda x: x.as_dict(), images))
    return (jsonify(dicts)), 200, {'ContentType':'application/json'}

@imageAccess.route('/home', methods = ['Get'])
def home():
    return render_template("home.html")


    
def GetImageFromAws():
    key = engine.ExecuteQuery('CALL GetImage_prc')
    url = S3Service().create_presigned_url(key[0]['Image_Id'])
    return url, key[0]['Image_Id']


ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@imageAccess.route('/api/classify')
def classify():
	return render_template('upload.html')

@imageAccess.route('/api/getClassScore', methods=['POST'])
def getClassScore():
    if 'file' not in request.files:
            return json.dumps({'error':'No file provided'}), 405, {'ContentType':'application/json'} 
    file = request.files['file']
    if file.filename == '':
        return json.dumps({'error':'No file provided'}), 405, {'ContentType':'application/json'} 
    if file and allowed_file(file.filename):
        scores =  ClassificationService().Classify(file)
        return json.dumps(scores.scoreObjects), 200
    else:
        return redirect(request.url, error = "File type not allowed")

        

def GetUserFromDb(username, password):
    user = engine.GetUser(username)
    if(user):
        if(SaltService().ValidatePassword(password, user.Password)):
            return user
    return 
