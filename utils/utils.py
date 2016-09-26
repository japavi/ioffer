import re
import random
import hashlib
import hmac
import logging

from string import letters
from google.appengine.ext import db

secret = 'fart'

categories = dict([('BAR','Bars & Clubs'),('RST','Restaurants'),('BTY','Hair & Beauty'),('SRV','General Services'),('SHP','Shopping'),('MOT','Motoring'),('FIT','Fitness & Health'),
    ('HOT','Hotels'),('HOM','Home Services'),('INM','State Agent'),('TRV','Travel'),('PET','Pets & Animals'),('FOO','Food'),('LEI','Leisure & Adventure'),('OTH','Others')])

countries = dict([('ES','Spain'),('IE','Ireland'),('GB','United Kingdom'),('US','United States')])
currencies = dict([('USD','USD'),('GBP','GBP'),('EUR','EUR')])

cities = dict([('MAD','Madrid'),('ATL','Athlone'),('DUB','Dublin'),('ALC','Alcorcon')])
profile_types = dict([('particular','Particular'),('empresa','Empresa')])

##### user stuff
def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val

def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)

def valid_pw(name, password, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, password, salt)

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

#TO-DO no debe aceptar todo whitespaces
NAME_RE = re.compile(r"^[\w+\s\w+]{3,20}$")
def valid_name(name):
    return name and NAME_RE.match(name)    

PASS_RE = re.compile(r"^.{3,20}$")  
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)

COOKIE_EXP="; Expires=True, 1 Jan 2025 00:00:00 GMT"   

def geo_converter(geo_str):
    '''
    Converter function - return db.GeoPt from str
    '''

    logging.error('geo_str: %s' % geo_str)
    if geo_str:
        lat, lng = geo_str.split(',')
        return db.GeoPt(lat=float(lat), lon=float(lng))
    return None