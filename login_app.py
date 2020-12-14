from flask import Flask, render_template, send_file, request, jsonify, redirect, url_for, make_response, abort
import logging
from flask_jwt_extended import (JWTManager, create_access_token, jwt_required, get_jwt_identity)
from const import *
import redis
import os
from flask_cors import CORS, cross_origin
import uuid
import hashlib
from datetime import datetime

GET = "GET"
POST = "POST"
SESSION_ID = "session-id"
users = "users"

FILES_PATH = "waybill_files/"
IMAGES_PATH = "waybill_files/images"
ACCEPTED_IMAGE_EXTENSIONS = ["png", "jpeg", "jpg"]

app = Flask(__name__, static_url_path="")
db = redis.Redis(host="redis", port=6379, decode_responses=True)

app.config["JWT_SECRET_KEY"] = os.environ.get(SECRET_KEY)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = TOKEN_EXPIRES_IN_SECONDS
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = True


jwt = JWTManager(app)
cors = CORS(app)


@app.route("/", methods=[GET])
def index():
    user = getUserFromCookie();
    isValidCookie = user is not None
    response = make_response(render_template("index.html", isValidCookie = isValidCookie))
    return refresh_token_session(response, request.cookies);
    

@app.route("/register", methods=[GET])
def register():
    user = getUserFromCookie();
    isValidCookie = user is not None
    response = make_response(render_template("register.html", isValidCookie = isValidCookie))
    return refresh_token_session(response, request.cookies);

@app.route("/login", methods=[GET])
def login():
    user = getUserFromCookie();
    isValidCookie = user is not None
    response = make_response(render_template("login.html", isValidCookie = isValidCookie))
    return refresh_token_session(response, request.cookies);

@app.route("/add_waybill", methods=[GET])
def add_waybill():
    user = getUserFromCookie();
    isValidCookie = user is not None
    if isValidCookie:
        response = make_response(render_template("add-waybill.html", isValidCookie = isValidCookie))
        return refresh_token_session(response, request.cookies);
    else:
        return abort(401)

@app.route("/add_waybill/new", methods=[POST])
def add_waybill_new():
    login = getUserFromCookie();
    isValidCookie = login is not None
    if isValidCookie:
        form = request.form
        userWaybillList = login + "-waybills"
        addTime = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        package_id = uuid.uuid4().hex.encode("utf-8")

        db.hset(userWaybillList, package_id, addTime)

        db.hset(package_id, "sender_name", form.get("sender_name"));
        db.hset(package_id, "sender_surname", form.get("sender_name"));
        db.hset(package_id, "sender_street", form.get("sender_name"));
        db.hset(package_id, "sender_city", form.get("sender_name"));
        db.hset(package_id, "sender_postal", form.get("sender_name"));
        db.hset(package_id, "sender_country", form.get("sender_name"));
        db.hset(package_id, "sender_phone", form.get("sender_name"));

        db.hset(package_id, "recipient_name", form.get("recipient_name"));
        db.hset(package_id, "recipient_surname", form.get("recipient_name"));
        db.hset(package_id, "recipient_street", form.get("recipient_name"));
        db.hset(package_id, "recipient_city", form.get("recipient_name"));
        db.hset(package_id, "recipient_postal", form.get("recipient_name"));
        db.hset(package_id, "recipient_country", form.get("recipient_name"));
        db.hset(package_id, "recipient_phone", form.get("recipient_name"));

        db.hset(package_id, "creation_time", addTime)

        pathToImage = save_file(package_id, request.files["waybill_image"])
        db.hset(package_id, "waybill_image", pathToImage)

        response = make_response(redirect("/show_waybills"))
        return refresh_token_session(response, request.cookies);
    else:
        return render_template("errors/401.html")



@app.route("/show_waybills", methods=[GET])
def show_waybills():
    user = getUserFromCookie();
    isValidCookie = user is not None
    if isValidCookie:
        userWaybillList = user + "-waybills"
        my_files = db.hgetall(userWaybillList);
        response = make_response(render_template("show-waybills.html", isValidCookie = isValidCookie, my_files = my_files))
        return refresh_token_session(response, request.cookies);
    else:
        return render_template("errors/401.html")


@app.route("/logout")
def logout():
    user = getUserFromCookie();
    isValidCookie = user is not None
    if isValidCookie:
        response = removeCookies()
    return redirect("/")


@app.route("/register/<string:new_user>")
def is_login_taken(new_user):
    empty = {}
    dbResponse = db.hgetall(new_user)
    if dbResponse == empty:
        return {"message": "User don't exist"}, 404
    else:
        return {"message": "Username already taken"}, 200



@app.route("/register/create_new_user/<string:new_user>", methods=[POST])
def create_new_user(new_user):
    name = request.form['name']
    surname = request.form['surname']
    birthDate = request.form['birthDate']
    street = request.form['street']
    adressNumber = request.form['adressNumber']
    postalCode = request.form['postalCode']
    country = request.form['country']
    login = request.form['login']
    pesel = request.form['pesel']
    password = request.form['password']
    if(
        db.hset(login, "name", name) != 1 or
        db.hset(login, "surname", surname) != 1 or
        db.hset(login, "birthDate", birthDate) != 1 or
        db.hset(login, "street", street) != 1 or
        db.hset(login, "adressNumber", adressNumber) != 1 or
        db.hset(login, "postalCode", postalCode) != 1 or
        db.hset(login, "country", country) != 1 or
        db.hset(login, "pesel", pesel) != 1 or
        db.hset(login, "password", password) != 1 
    ):
        db.hdel(login, "name", "surname", "birthDate", "street", "adressNumber", "postalCode", "country", "pesel", "password");
        return {"message": "Something went wrong while adding new user"}, 400
    else:
        return {"message": "User created succesfully"}, 201


@app.route("/login_user", methods=[POST])
def log_user():
    login = request.form['login']
    password = request.form['password']
    
    if (db.hget(login, "password") == password):
        name_hash = hashlib.sha512(login.encode("utf-8")).hexdigest()
        db.set(name_hash, login);
        db.expire(name_hash, TOKEN_EXPIRES_IN_SECONDS);
        userWaybillList = login + "-waybills"
        access_token = create_access_token(identity=login, user_claims=db.hgetall(userWaybillList));
        response = make_response(jsonify({"access_token": access_token}), 200)
        response.set_cookie(SESSION_ID, name_hash, max_age=TOKEN_EXPIRES_IN_SECONDS, secure=True, httponly=True)
        return response
    else:
        return {"message": "Login or password incorrect."}, 400


def refresh_token_session(response, cookies):
    sessionId = cookies.get(SESSION_ID);
    if (db.exists(str(sessionId))):
        db.expire(sessionId, TOKEN_EXPIRES_IN_SECONDS)
        response.set_cookie(SESSION_ID, sessionId, max_age=TOKEN_EXPIRES_IN_SECONDS, secure=True, httponly=True)
    return response

@app.route('/<string:user>')
def getUser(user):
    return db.hgetall(user)


def getUserFromCookie():
    name_hash = request.cookies.get(SESSION_ID)
    if name_hash is not None:
        login = db.get(name_hash);
        return login;
    return name_hash;

def removeCookies():
    sessionId = request.cookies.get(SESSION_ID)
    if db.exists(sessionId):
        db.delete(sessionId);
        response = make_response(jsonify({"message": "OK"}), 200)
    else:
        response = make_response(jsonify({"message": "User is not logged"}), 204)
    response.set_cookie(SESSION_ID, sessionId, max_age=0, secure=True, httponly=True)
    return response


def save_file(id, image):
    if image is not None:
        fileExtension = image.filename.split('.')[-1]
        if fileExtension not in ACCEPTED_IMAGE_EXTENSIONS:
            return ""
        else:
            image_name = "{}.{}".format(id, fileExtension)
            image_path = os.path.join(IMAGES_PATH, image_name)
            image.save(image_path)
            return image_path
    else:
        return ""


@app.errorhandler(400)
def bad_request(error):
    response = make_response(render_template("errors/400.html", error=error))
    return response

@app.errorhandler(401)
def unauthorized(error):
    response = make_response(render_template("errors/401.html", error=error))
    return response

@app.errorhandler(403)
def forbidden(error):
    response = make_response(render_template("errors/403.html", error=error))
    return response

@app.errorhandler(404)
def page_not_found(error):
    response = make_response(render_template("errors/404.html", error=error))
    return response

@app.errorhandler(500)
def internal_server_error(error):
    response = make_response(render_template("errors/500.html", error=error))
    return response
