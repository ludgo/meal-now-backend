from models import Base, User, Offer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from flask import abort, Flask, jsonify, make_response, render_template, request
from oauth2client import client, crypt

import utilities
from private_keys import GOOGLE_WEB_CLIENT_ID

import httplib2
import json
from time import strftime


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

# Users
@app.route('/api/v1/<provider>/login', methods=['POST'])
def loginUser(provider):
    checkJson(request)
    data = request.json
    if not (data.get('client_type') and data.get('user_name') and data.get('user_email') and data.get('user_picture')):
            abort(400)

    if provider == 'google':

        if not data.get('token_id'):
            abort(400)

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
        userName = data.get('user_name')
        userEmail = data.get('user_email')
        userPicture = data.get('user_picture')
            
        # Check if user exists
        status = 200
        user = session.query(User).filter_by(provider_id=userid).first()
        if not user:
            # User doesn't exist, make a new one
            user = User(name = userName, email = userEmail, picture = userPicture, provider = 'google', provider_id = userid, token = '')
            session.add(user)
            session.commit()
            print "User created."
            status = 201
        else:
            # User exists, check profile changes at Google account
            if user.name != userName:
                user.name = userName
            if user.email != userEmail:
                user.email = userEmail
            if user.picture != userPicture:
                user.picture = userPicture

        TOKEN_DURATION = 300000
        # Make token for the user
        token = user.generate_auth_token(TOKEN_DURATION)
        user.token = token
        session.add(user)
        session.commit()
        print repr(user) # debug

        # Send token back to the client
        obj = {'message': 'User signed in.', 'token': token.decode('ascii')}
        obj.update(user.serialize)
        body = jsonify(obj)
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
        print repr(user) # debug

        body = jsonify({'message': 'User signed out.'})
        response = make_response(body, 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    else:
        body = jsonify({'error_message': 'Unrecognized provider.'})
        response = make_response(body, 404)
        response.headers['Content-Type'] = 'application/json'
        return response

# Offers
@app.route('/api/v1/offers', methods=['GET', 'POST'])
def offers():
    checkJson(request)

    if request.method == 'GET':

        page = int(request.args.get('page', '1'))

        # Provide not yet filled offers only
        OFFERS_PER_PAGE = 10
        offers = session.query(Offer).filter_by(filled=0).limit(OFFERS_PER_PAGE).offset((page-1)*OFFERS_PER_PAGE).all()
        offers_array = []
        for offer in offers:
            user = session.query(User).filter_by(id=offer.user_id).first()
            if user:
                # Provide info about both the offer and its creator
                item = (offer.serialize).copy()
                item.update(user.serialize)
                offers_array.append(item)
                print repr(offer) # debug

        body = json.dumps({"message": "%d active offers." % len(offers_array), "offers": offers_array})
        response = make_response(body, 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    elif request.method == 'POST':

        data = request.json
        if not (data.get('client_type') and data.get('user_id') and data.get('user_token') and data.get('offer_meal') and data.get('offer_location')):
            abort(400)

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

        # Request coordinates based on Google geocode Api
        offerLocation = data.get('offer_location')
        status, latitude, longitude = utilities.getGeocodeLocation(offerLocation)
        if status != 200:
            body = jsonify({'error_message': 'Service temporary unavailable.'})
            response = make_response(body, 503)
            response.headers['Content-Type'] = 'application/json'
            return response
        elif latitude is None or longitude is None:
            body = jsonify({'message': 'Unknown location.'})
            response = make_response(body, 200)
            response.headers['Content-Type'] = 'application/json'
            return response

        offerMeal = data.get('offer_meal')
        currentTime = strftime("%Y-%m-%d %H:%M:%S")
        offer = Offer(user_id = user.id, time_created = currentTime, meal = offerMeal, location = offerLocation, latitude = latitude, longitude = longitude)
        session.add(offer)
        session.commit()
        print "Offer created."
        print repr(offer) # debug

        body = jsonify({'message': 'Offer created.'})
        response = make_response(body, 201)
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
