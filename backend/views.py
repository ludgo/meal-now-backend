from flask import Flask, render_template, request
from oauth2client import client, crypt
from private_keys import GOOGLE_WEB_CLIENT_ID


app = Flask(__name__)

@app.route('/')
def welcomePage():
    return render_template('index.html')

@app.route('/api/v1/<provider>/login', methods=['POST'])
def loginUser(provider):
    data = request.json

    if provider == 'google':

        # from android app
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
        userid = idinfo['sub']

        print userid
        return userid




    else:
        return 'Unrecoginized Provider'





if __name__ == '__main__':
    #app.config['SECRET_KEY'] = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
