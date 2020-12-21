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
KURIER_SESSION_ID = "kurier-session-id"
users = "users"


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
    return make_response(render_template("paczkomat-index.html"))

@app.route("/parcel_homepage_<string:p_id>", methods=[GET])
def homepage(p_id):

    return make_response(render_template("paczkomat-homepage.html", p_id = p_id))
    


@app.route("/login", methods=[GET])
def login():
    user = getUserFromCookie();
    isValidCookie = user is not None
    response = make_response(render_template("kurier-login.html", isValidCookie = isValidCookie))
    return refresh_token_session(response, request.cookies);


@app.route("/drop_<string:p_id>", methods=[POST])
def drop(p_id):

    form = request.form
    package_id = form.get("package-id")
    package_status = db.hget(package_id, "status")
    paczkomat_packages = 1
    if (package_status is None):
        return("Taka paczka nie istnieje", 400)
    if (package_status != "nowa"):
        return("Paczka została już nadana", 403)
    db.hset(p_id, package_id, "")
    db.hset(package_id, "status", "oczekujaca_w_paczkomacie")
    return make_response("Status changed", 201)


@app.route("/show_packages_<string:p_id>", methods=[GET])
def show_packages(p_id):
    user = getUserFromCookie()
    isValidCookie = user is not None
    if isValidCookie:
        userWaybillList = user + "-packages"
        my_files = db.hgetall(userWaybillList);
        response = make_response(render_template("kurier-packages.html", isValidCookie = isValidCookie, my_files = my_files))
        return refresh_token_session(response, request.cookies);
    else:
        return abort(401)

@app.route("/sp_<string:p_id>", methods=[GET])
def sp(p_id):
    my_packages = db.hgetall(p_id);
    return render_template("paczkomat-packages.html", my_packages = my_packages)


@app.route("/login_kurier", methods=[POST])
def login_kurier():
    login = request.form['login'] + "_kurier"
    password = request.form['password']
    
    if (db.hget(login, "password") == password):
        name_hash = hashlib.sha512(login.encode("utf-8")).hexdigest()
        db.set(name_hash, login);
        db.expire(name_hash, TOKEN_EXPIRES_IN_SECONDS);
        userWaybillList = login + "-packages"
        access_token = create_access_token(identity=login, user_claims=db.hgetall(userWaybillList));
        response = make_response(jsonify({"access_token": access_token}), 200)
        response.set_cookie(KURIER_SESSION_ID, name_hash, max_age=TOKEN_EXPIRES_IN_SECONDS, secure=True, httponly=True)
        return response
    else:
        return {"message": "Login or password incorrect."}, 400


def refresh_token_session(response, cookies):
    sessionId = cookies.get(KURIER_SESSION_ID);
    if (db.exists(str(sessionId))):
        db.expire(sessionId, TOKEN_EXPIRES_IN_SECONDS)
        response.set_cookie(KURIER_SESSION_ID, sessionId, max_age=TOKEN_EXPIRES_IN_SECONDS, secure=True, httponly=True)
    return response


@app.route("/client_drop_<string:p_id>")
def client_drop(p_id):
    return make_response(render_template("paczkomat-client-drop.html", p_id = p_id))



def getUserFromCookie():
    name_hash = request.cookies.get(KURIER_SESSION_ID)
    if name_hash is not None:
        login = db.get(name_hash);
        return login;
    return name_hash;

def removeCookies():
    sessionId = request.cookies.get(KURIER_SESSION_ID)
    if db.exists(sessionId):
        db.delete(sessionId);
        response = make_response(jsonify({"message": "OK"}), 200)
    else:
        response = make_response(jsonify({"message": "User is not logged"}), 204)
    response.set_cookie(KURIER_SESSION_ID, sessionId, max_age=0, secure=True, httponly=True)
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
