#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os

import webapp2
import jinja2
import logging

import urllib
import urllib2
import json

import datetime
import time

from google.appengine.ext import db
from google.appengine.api import memcache
from webapp2_extras import sessions

from models.User import User
from models.Profile import Profile
from models.Offer import Offer, offers_key
from utils.utils import make_secure_val, check_secure_val, valid_username, valid_password, valid_name, valid_email, categories, countries, profile_types, COOKIE_EXP

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'fart',
}


def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)


def loged_user(logged_username, update = False):
    key = 'loged_user' + logged_username
    user = memcache.get(key)
    if user is None or update:
        logging.error('DB QUERY user')
        memcache.delete(key)

        user = User.by_name(logged_username)
        memcache.set(key, user)
        #logging.error('memcache 1 [%s]:%s' % (key,memcache.get(key).name))
        logging.error('memcache.get(key).profiles.count:%s' % memcache.get(key).profiles.count())
        if memcache.get(key).profiles.count() > 0:
            logging.info('memcache 2 [%s]:%s' % (key,memcache.get(key).profiles[0].name)) #no quitar esta traza si no no refresca los perfiles al modificar el perfil
    return user


def loged_profile(logged_username, update = False):
    key = 'loged_profile' + logged_username
    profile = memcache.get(key)
    if profile is None or update:
        logging.error('DB QUERY profile')
        u = loged_user(logged_username, True)#User.by_name(logged_username)
        memcache.delete(key)
        profile = u.profiles
        if profile.count() > 0:
            memcache.set(key, profile[0])
            profile = profile[0]
            logging.error('DB QUERY profile profile:%s' % profile.name)
        else:
            profile = None
    return profile

def loged_offers(logged_username, update = False):
    key = 'loged_offers' + logged_username
    offers = memcache.get(key)
    if offers is None or update:
        logging.error('DB QUERY')
        u = loged_user(logged_username)#User.by_name(logged_username)

        profile = u.profiles
        if profile.count() > 0:
            profile = profile[0]
            offers = profile.offers
            memcache.set(key, offers)
        else:
            offers = None
    return offers

class JSONEncoder(json.JSONEncoder):

    def default(self, o):
        # If this is a key, you might want to grab the actual model.
        if isinstance(o, db.Key):
            o = db.get(o)

        if isinstance(o, db.Model):
            return db.to_dict(o)

        elif isinstance(o, db.DateTimeProperty):
            return str(o)
        #elif isinstance(o, (datetime, date, time)):
         #   return str(o)  # Or whatever other date format you're OK with...

class BaseHandler(webapp2.RequestHandler):
    
    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)
        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)
    @webapp2.cached_property
    def session(self):
        # Returns a session using the default cookie key.
        sess = self.session_store.get_session()
        
        #add some default values:
        if not sess.get('user'):
            sess['user'] = None
        if not sess.get('profile'):
            sess['profile'] = None
        return sess

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        params['user'] = self.user
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val, rem):
        cookie_val = make_secure_val(val)
        remember = ""
        if rem:
            remember = COOKIE_EXP
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/%s' % (name, cookie_val, remember))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user, remember):
        self.set_secure_cookie('user_id', str(user.key().id()), remember)

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))

class Signup(BaseHandler):
    def get(self):
        self.render("signup-form.html")

    def post(self):
        have_error = False
        self.username = self.request.get("username")
        self.password = self.request.get("password")
        self.verify = self.request.get("verify")
        self.email = self.request.get("email")

        params = dict(username = self.username, email = self.email)

        if not valid_username(self.username):
            params['error_username'] = "Invalid username"
            have_error = True

        if not valid_password(self.password):
            params['error_password'] = "Invalid password"
            have_error = True
        elif self.password != self.verify:
            params['error_verify'] = "Your password didn't match"
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "Invalid email"
            have_error = True

        if have_error:
            self.render('signup-form.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError

class Register(Signup):
    def done(self):
        #make sure the user doesn't already exist
        u = User.by_name(self.username)
        if u:
            msg = 'That user already exists.'
            self.render('signup-form.html', error_username = msg)
        else:
            u = User.register(self.username, self.password, self.email)
            u.put()

            self.login(u, False)
            self.redirect('/ioffer/welcome?username=' + self.username)

class Login(BaseHandler):
    def get(self):
        self.render('login-form.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')
        remember = self.request.get('remember')

        rem = False

        if remember and remember == 'on':
            rem = True

        user = User.login(username, password)
        if user:
            self.login(user, rem)
            loged_user(username)
            self.redirect('/ioffer/welcome')
        else:
            msg = 'Invalid login'
            self.render('login-form.html', error = msg)

class Logout(BaseHandler):
    def get(self):
        #self.session['user'] = None
        #self.session['profile'] = None
        self.logout()
        self.redirect('/')

class Welcome(BaseHandler):
    def get(self):
        uid = self.read_secure_cookie('user_id')
        user = uid and User.by_id(int(uid))
        logging.error('DB Query')
        logged_username = user and user.name

        if logged_username == '' or logged_username == None:
            self.redirect('/ioffer/login')
        else:

            offer_added = self.request.get('offer_added')

            u = loged_user(logged_username) #User.by_name(logged_username)

            profile = loged_profile(logged_username) 

            logging.error('profile en welcome: %s' % profile)

            if  valid_username(logged_username):
                if profile:

                    if offer_added:
                        self.render('welcome.html', user = u, profile = profile, categories = categories, offer_added = True)
                    else:
                        self.render('welcome.html', user = u, profile = profile, categories = categories)
                else:
                    self.render('welcome.html', user = u)
            
            else:
                error_username = 'There was an error with user %s' % logged_username
                self.render('welcome.html', user = u, error_username = error_username)
            
class Init(BaseHandler):
    def get(self):
        self.render('index.html')

class Show_Profile(BaseHandler):

    def post(self):
        logged_username = self.request.get("user")

        u = loged_user(logged_username)
        profile = loged_profile(logged_username) #u.profiles #It is a set, but by now it only contains 1 profile 

        if profile is None:
            logging.error('Show_Profile profile: %s' % profile)
            params = dict(username = logged_username, default_selected_type = 'empresa')
            self.render('profile_form.html', params = params, countries = countries, profile_types = profile_types, btn_send = 'Save')
        else:
            self.render('profile_form_edit.html', profile = profile, user = u, countries = countries, profile_types = profile_types)
            
class Modify_Profile(BaseHandler):

    def post(self):
        logged_username = self.request.get("username")
        u = loged_user(logged_username)
        profile = loged_profile(logged_username)

        logging.error('username: %s' % logged_username)
        logging.error('u: %s' % u)
        logging.error('profile: %s' % profile)

        logging.error('profile.country: %s' % profile.country)

        params = dict(username = profile.user.name, name = profile.name, email = profile.email, phone = profile.phone, profile_type = profile.profile_type, street_address = profile.street_address, address_line_2 = profile.address_line_2, city = profile.city, region = profile.region, zip_code = profile.zip_code, country = profile.country, web = profile.web)

        self.render('profile_form.html', params = params, countries = countries, profile_types = profile_types, btn_send = 'Modify')

class Save_Profile(BaseHandler):

    def post(self):
        logging.error("En save_profile")
        have_error = False
        self.username = self.request.get("username")

        self.u = loged_user(self.username)
        

        self.name = self.request.get("name")
        self.original_name = self.request.get("original_name")
        self.profile_type = self.request.get("profile_type")
        self.email = self.request.get("email")
        self.phone = self.request.get("phone")
        self.street_address = self.request.get("street_address")
        self.address_line_2 = self.request.get("address_line_2")
        self.city = self.request.get("city")
        self.region = self.request.get("region")
        self.zip_code = self.request.get("zip_code")
        self.country = self.request.get("country")
        self.web = self.request.get("web")

        logging.error('self.country:%s' % self.country)

        params = dict(name = self.name, original_name = self.original_name, email = self.email, phone = self.phone, profile_type = self.profile_type, username = self.username, street_address = self.street_address, address_line_2 = self.address_line_2, city = self.city, region = self.region, zip_code = self.zip_code, country = self.country, web = self.web)

        if not valid_name(self.name):
            params['error_name'] = "Invalid name"
            have_error = True
        
        if not valid_email(self.email):
            params['error_email'] = "Invalid email"
            have_error = True

        if have_error:
            logging.error('params:%s' % params)
            self.render('profile_form.html', params = params, countries = countries, profile_types = profile_types, btn_send = 'Modify')
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError  

class Send_Profile(Save_Profile):
    def done(self):
        #make sure the profile name doesn't already exist
        # p = Profile.by_name(self.name)
        # logging.error("p: %s" % p)
        # if p:
        #     msg = 'That name already exists.'
        #     self.render('welcome.html', profile = p, user = self.u, countries = countries, error_name = msg)
            
        # else:
        logging.error("En send_profile")
        profile = loged_profile(self.username)

        if not profile:

            logging.error('A guardar profile')
            p = Profile.save_profile(self.u.name, self.u, self.name, self.profile_type, self.phone, self.email, self.street_address, self.address_line_2, self.region, self.city, self.zip_code, self.country, self.web)
            p.put()
        else:
            logging.error('A modificar profile')
            #logging.error('key:%s' % db.get(profile.key()))
            p = Profile.update_profile(profile, self.u, self.name, self.profile_type, self.phone, self.email, self.street_address, self.address_line_2, self.region, self.city, self.zip_code, self.country, self.web)

        self.u = loged_user(self.u.name, True)
        p = loged_profile(self.u.name, True)
        self.render('profile_form_edit.html', profile = p, user = self.u, countries = countries, profile_types = profile_types)            


class Show_Add_Offer(BaseHandler):

    def post(self):
        logged_username = self.request.get("user")
 
        u = loged_user(logged_username)
        p = loged_profile(logged_username) #u.profiles #It is a set, but by now it only contains 1 profile 

        if p is None:
            self.render('no_offers.html', text = 'Fill in your profile to start publishing offers.')
        else:
            logging.error('Show_Add_Offer profile: %s' % p)
            self.render('add_offer_form.html', profile = p, user = u, categories = categories)


class Add_Offer(BaseHandler):

    def post(self):
        have_error = False
        self.username = self.request.get("username")

        self.u = loged_user(self.username)

        self.name = self.request.get("name")
        self.offer_tittle = self.request.get("offer_tittle")
        self.offer_category = self.request.get("offer_category")
        self.offer_desc = self.request.get("offer_desc")
        self.offer_start_date = self.request.get("offer_start_date")
        self.offer_end_date = self.request.get("offer_end_date")
        self.image_offer = self.request.get("image_offer")
        self.offer_conditions = self.request.get("offer_conditions")

        logging.error("En add_offer")

        params = dict(offer_tittle = self.offer_tittle, offer_category = self.offer_category, offer_desc = self.offer_desc, offer_start_date = self.offer_start_date, 
            offer_end_date = self.offer_end_date, image_offer = self.image_offer, offer_conditions = self.offer_conditions)

        # if not valid_name(self.name):
        #     params['error_name'] = "Invalid name"
        #     have_error = True


        if have_error:
            self.render('welcome.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError

class Send_Offer(Add_Offer):
    def done(self):
        #u = User.by_name(self.username)
        #p = u.profiles #It is a set, but by now it only contains 1 profile
        profile = loged_profile(self.username)

        #make sure the offer title doesn't already exist
        o = Offer.by_title(self.offer_tittle)
        logging.error("o: %s" % o)
        if o:
            msg = 'That title already exists.'
            self.render('welcome.html', error_name = msg)
        else:
            logging.error('A guardar offer')
            o = Offer.save_offer(profile, self.u.name, self.name, self.offer_tittle, self.offer_category, self.offer_desc, datetime.datetime.strptime(self.offer_start_date, "%m/%d/%Y"), datetime.datetime.strptime(self.offer_end_date, "%m/%d/%Y"), self.image_offer, self.offer_conditions)
            o.put()

            offers_user = loged_offers(self.u.name, True)
            #self.redirect('/ioffer/welcome?offer_added=True')
            #self.render('welcome.html', username = u.name, profile = p, categories = categories, offer_added = True)
            self.render('offers_user.html', offers_user = offers_user, user = self.u, categories = categories, offer_added = True)
            #self.render('welcome.html', offer_added = True)

class Offers_User_Display(BaseHandler):
    def post(self):
        logged_username = self.request.get("username")
        u = loged_user(logged_username)
        profile = loged_profile(logged_username)

        if profile:

            logging.error('profile en offers_display: %s' % profile)

            #offers_user = db.GqlQuery("select * from Offer where username=:1", username)
            #offers_user = profile.offers
            offers_user = loged_offers(logged_username)
            number_of_offers = offers_user.count()
            logging.error('offers_user en offers_display: %s' % type(offers_user))
            logging.error('offers_user.count: %s' % number_of_offers)

            if number_of_offers > 0:
                self.render('offers_user.html', offers_user = offers_user, user = u, categories = categories)
            else:
                self.render('no_offers.html', text='There are no offers yet')
        else:
            self.render('no_offers.html', text='There are no offers yet. You must first create a profile to start adding offers')



class OfferPage(BaseHandler):
    def get(self, order_id):
        key = db.Key.from_path('Offer', int(order_id), parent=offers_key())
        offer = db.get(key)

        if not offer:
            self.error(404)
            return

        self.render('offers_form.html', offer = offer, categories = categories)

app = webapp2.WSGIApplication([
    ('/', Init),
    ('/ioffer/signup', Register),
    ('/ioffer/login', Login),
    ('/ioffer/logout', Logout),
    ('/ioffer/send_profile', Send_Profile),
    ('/ioffer/modify_profile', Modify_Profile),
    ('/ioffer/show_add_offer', Show_Add_Offer),
    ('/ioffer/add_offer', Send_Offer),
    ('/ioffer/offers_user_display', Offers_User_Display),
    ('/ioffer/show_profile', Show_Profile),
    ('/ioffer/offer/([0-9]+)', OfferPage),
    ('/ioffer/welcome', Welcome)], config=config, debug=True)

