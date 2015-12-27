from models import Base, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from flask import abort, Flask, jsonify, make_response, render_template, request
from oauth2client import client, crypt
from private_keys import GOOGLE_WEB_CLIENT_ID

import httplib2
import json


app = Flask(__name__)

engine = create_engine('sqlite:///meal_now.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def checkJson(request):
    if request.headers['Content-Type'] not in ['application/json', 'application/json; charset=utf-8']:
        abort(400)


@app.route('/')
def welcomePage():
    return render_template('index.html')

@app.route('/api/v1/<provider>/login', methods=['POST'])
def loginUser(provider):
    checkJson(request)
    data = request.json
    if not (data.get('client_type') and data.get('user_name') and data.get('user_email') and data.get('user_picture') and data.get('token_id')):
        abort(400)

    if provider == 'google':

        # Verify Google Sign in token
        google_token = data.get('token_id')
        try:
            idinfo = client.verify_id_token(google_token, GOOGLE_WEB_CLIENT_ID)
            # If multiple clients access the backend server:
            if idinfo['aud'] not in [GOOGLE_WEB_CLIENT_ID]:
                raise crypt.AppIdentityError("Unrecognized client.")
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise crypt.AppIdentityError("Wrong issuer.")
        except crypt.AppIdentityError:
            abort(401)

        userid = idinfo['sub']

        # Check if user exists, if it doesn't make a new one
        status = 200
        user = session.query(User).filter_by(provider_id=userid).first()
        if not user:
            userName = data.get('user_name')
            userEmail = data.get('user_email')
            userPicture = data.get('user_picture')
            user = User(name = userName, email = userEmail, picture = userPicture, provider = 'google', provider_id = userid, token = '')
            session.add(user)
            session.commit()
            status = 201
        print repr(session.query(User).filter_by(provider_id=userid).first()) # debug

        TOKEN_DURATION = 300
        # Make token for the user
        token = user.generate_auth_token(TOKEN_DURATION)
        user.token = token
        session.add(user)
        session.commit()

        # Send token back to the client
        body = jsonify({'message': 'Successful sign in', 'token': token.decode('ascii'), 'duration': TOKEN_DURATION})
        response = make_response(body, status)
        response.headers['Content-Type'] = 'application/json'
        return response

    else:
        body = jsonify({'error_message': 'Unrecognized provider.'})
        response = make_response(body, 404)
        response.headers['Content-Type'] = 'application/json'
        return response

@app.route('/api/v1/<provider>/logout', methods=['POST'])
def logoutUser(provider):
    checkJson(request)
    data = request.json
    if not (data.get('client_type') and data.get('user_id') and data.get('user_token')):
        abort(400)

    if provider == 'google':

        userid = data.get('user_id')
        token = data.get('user_token')

        # Check if user exists
        user = session.query(User).filter_by(provider_id=userid).first()
        if not user:
            abort(401)
        print repr(user) # debug

        # Verify token
        if (userid != user.verify_auth_token(token)):
            abort(401)

        # Degrade living token with immediately expiring token
        token = user.generate_auth_token(0)
        user.token = token
        session.add(user)
        session.commit()
        print repr(session.query(User).filter_by(provider_id=userid).first()) # debug

        body = jsonify({'message': 'Successful sign out'})
        response = make_response(body, 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    else:
        body = jsonify({'error_message': 'Unrecognized provider.'})
        response = make_response(body, 404)
        response.headers['Content-Type'] = 'application/json'
        return response




@app.errorhandler(400)
def bad_request(e):
    body = jsonify({'error_message': 'Bad request.'})
    response = make_response(body, 400)
    response.headers['Content-Type'] = 'application/json'
    return response

@app.errorhandler(401)
def unauthorized_user(e):
    body = jsonify({'error_message': 'Unauthorized user.'})
    response = make_response(body, 401)
    response.headers['Content-Type'] = 'application/json'
    return response

@app.errorhandler(404)
def page_not_found(e):
    body = jsonify({'error_message': 'Page not found.'})
    response = make_response(body, 404)
    response.headers['Content-Type'] = 'application/json'
    return response

@app.errorhandler(405)
def mwthod_not_allowed(e):
    body = jsonify({'error_message': 'Method not allowed.'})
    response = make_response(body, 405)
    response.headers['Content-Type'] = 'application/json'
    return response

# Doesn't work in debug mode!
@app.errorhandler(500)
def internal_server_error(e):
    body = jsonify({'error_message': 'Internal server error.'})
    response = make_response(body, 500)
    response.headers['Content-Type'] = 'application/json'
    return response



if __name__ == '__main__':
    #app.config['SECRET_KEY'] = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
