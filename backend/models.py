from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
import random, string
from itsdangerous import(TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)


Base = declarative_base()
secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    email = Column(String)
    picture = Column(String)
    provider = Column(String(32))
    provider_id = Column(String, index=True)
    token = Column(String)

    def generate_auth_token(self, expiration=600):
        s = Serializer(secret_key, expires_in = expiration)
        # Token will live for specified amount of time
        self.token = s.dumps({'id': self.provider_id })
        return self.token

    def verify_auth_token(self, token):
        s = Serializer(secret_key)
        if (self.token != token):
            # http://stackoverflow.com/questions/27831064/destroy-a-flask-restful-token
            # User is signed out
            return None
        try:
            data = s.loads(token)
        except SignatureExpired:
            # Valid token, but expired
            return None
        except BadSignature:
            # Invalid token
            return None
        user_id = data['id']
        return user_id

    def __repr__(self):
        return "<User(id='%r', name='%r', email='%r', picture='%r', provider='%r', provider_id='%r', token='%r')>" % (
                             self.id, self.name, self.email, self.picture, self.provider, self.provider_id, self.token)


engine = create_engine('sqlite:///meal_now.db')
Base.metadata.create_all(engine)
