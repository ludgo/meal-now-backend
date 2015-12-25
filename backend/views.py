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
    print request.headers['Content-Type']
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
        token = data.get('token_id')
        try:
            idinfo = client.verify_id_token(token, GOOGLE_WEB_CLIENT_ID)
            # If multiple clients access the backend server:
            if idinfo['aud'] not in [GOOGLE_WEB_CLIENT_ID]:
                raise crypt.AppIdentityError("Unrecognized client.")
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise crypt.AppIdentityError("Wrong issuer.")
        except crypt.AppIdentityError:
            print 'Invalid token'
            response = make_response(json.dumps("Unauthorized user."), 401)
            response.headers['Content-Type'] = 'application/json'
            return response

        userid = idinfo['sub']

        # Check if user exists, if it doesn't make a new one
        status = 200
        user = session.query(User).filter_by(provider_id=userid).first()
        if not user:
            userName = data.get('user_name')
            userEmail = data.get('user_email')
            userPicture = data.get('user_picture')
            user = User(name = userName, email = userEmail, picture = userPicture, provider = 'google', provider_id = userid)
            session.add(user)
            session.commit()
            status = 201
        
        print repr(session.query(User).filter_by(provider_id=userid).first())

        TOKEN_DURATION = 300
        # Make token
        token = user.generate_auth_token(TOKEN_DURATION)

        # Send back token to the client
        body = jsonify({'token': token.decode('ascii'), 'duration': TOKEN_DURATION})

        response = make_response(body, status)
        response.headers['Content-Type'] = 'application/json'
        return response

    else:
        response = make_response(json.dumps('Unrecognized provider.'), 404)
        response.headers['Content-Type'] = 'application/json'
        return response




@app.errorhandler(400)
def page_not_found(e):
    response = make_response(json.dumps('Bad request.'), 400)
    response.headers['Content-Type'] = 'application/json'
    return response

@app.errorhandler(404)
def page_not_found(e):
    response = make_response(json.dumps('Page Not found.'), 404)
    response.headers['Content-Type'] = 'application/json'
    return response

@app.errorhandler(405)
def page_not_found(e):
    response = make_response(json.dumps('Method Not Allowed.'), 405)
    response.headers['Content-Type'] = 'application/json'
    return response

# Doesn't work in debug mode!
@app.errorhandler(500)
def internal_server_error(e):
    response = make_response(json.dumps('Internal Server Error.'), 500)
    response.headers['Content-Type'] = 'application/json'
    return response



if __name__ == '__main__':
    #app.config['SECRET_KEY'] = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
