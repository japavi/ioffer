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
import cgi

import os

import webapp2
import jinja2
import logging

import urllib
import urllib2
import json

import datetime
import time
import mimetypes
import re
import collections
import rest

from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from webapp2_extras import sessions
from google.appengine.api import images

from models.User import User
from models.Profile import Profile
from models.Offer import Offer, offers_key
from models.Image import Offer_Image

from utils.utils import make_secure_val, check_secure_val, valid_username, valid_password, valid_name, valid_email, categories, currencies, countries, profile_types, COOKIE_EXP, geo_converter

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
    key = 'loged_user' + str(logged_username)
    user = memcache.get(key)
    if user is None or update:
        logging.error('DB QUERY user')
        memcache.delete(key)

        user = User.by_name(str(logged_username))
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
            logging.error('Tipo de offers: %s' % type(offers))
            offers.order('-offer_created')
            memcache.set(key, offers)
        else:
            offers = None
    return offers

def list_offers_loc(lat1, long1, update = False):
    key = 'list_offers_loc' + str(lat1) + str(long1)
    offers = memcache.get(key)
    if offers is None or update:
        logging.error('DB QUERY')
        #TODO impl logica para sacar las ofertas por localizacion
        offers = Profile.by_loc(lat1, long1)
        memcache.set(key, offers)
        
    return offers


def queried_offers(offer_id, update = False):
    key = 'offer_id' + offer_id
    offer = memcache.get(key)
    if offer is None or update:
        logging.error('DB QUERY x offer')
        offer = Offer.by_id(long(offer_id))
        logging.error(offer.offer_tittle)
        memcache.set(key, offer)
    return offer 

# class JSONEncoder(json.JSONEncoder):

#     def default(self, o):
#         # If this is a key, you might want to grab the actual model.
#         if isinstance(o, db.Key):
#             o = db.get(o)

#         if isinstance(o, db.Model):
#             return db.to_dict(o)

#         elif isinstance(o, db.DateTimeProperty):
#             return str(o)
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

    def get_geo_params(self):
        client_ciudad = self.request.headers.get('X-AppEngine-City')
        client_pais = self.request.headers.get('X-AppEngine-Country')
        client_ip = cgi.escape(os.environ["REMOTE_ADDR"])
        geo_params = dict(client_ip = client_ip, client_pais = client_pais, client_ciudad = client_ciudad)
        return geo_params

    
    # def prueba(self):
    #     country = "ES"

    #     nom_fich = "%s_REG.csv" % country

    #     logging.error('nom_fich: %s' % nom_fich)

    #     try:
    #         fich = open(nom_fich, 'r')
    #     except:
    #         logging.error("El fichero no existe")
    #         return

    #     list_regs = []

    #     for line_reg in fich:
    #         reg_fields = line_reg.split(",")
    #         reg_params = dict(reg_code = reg_fields[1], reg_value = reg_fields[2])
    #         list_regs.append(reg_params)

    #     logging.error('list_regs: %s' % list_regs)    

    #get the latest 10 offers
    def get_last_10_offers(self):
        #logging.error('yaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
        

        last_10_offers = db.GqlQuery("select * from Offer where offer_end_date>=:1", datetime.datetime.now())
        #logging.error('last_10_offers:%s' % last_10_offers)
        for offer in last_10_offers:
            logging.error('oferta:%s; fecha_fin:%s' % (offer.offer_tittle, str(offer.offer_end_date)))
        return last_10_offers

class Signup_IOffer_Show(BaseHandler):
    def post(self):
        self.render('ioffer_signup_form.html')    

class Signup(BaseHandler):

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

        u = User.by_name(self.username)
        if u:
            params['error_username'] = "That user already exists"
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
            self.render('ioffer_signup_form.html', params = params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError

class Register(Signup):
    def done(self):

        u = User.register(self.username, self.password, self.email)
        u.put()

        self.login(u, False)
        logging.error('self.username: %s' % self.username)
        #loged_user(self.username)
        self.redirect('/ioffer/welcome')

class Login_IOffer_Show(BaseHandler):
    def post(self):
        self.render('login-form.html')

class Login_IOffer(BaseHandler):
    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')
        remember = self.request.get('remember')

        token = self.request.get('token')
        providerId = self.request.get('providerId')
        uid = self.request.get('uid')
        displayName = self.request.get('displayName')
        email = self.request.get('email')
        photoURL = self.request.get('photoURL')

        logging.error("username:%s" % username)
        logging.error("password:%s" % password)

        logging.error("token:%s" % token)
        logging.error("displayName:%s" % displayName)


        rem = False

        if remember and remember == 'on':
            rem = True

        if (token != ""):
            user=displayName
            userexists = User.by_name(user)

            if not userexists:

                logging.error("el usuario %s no existe. Se procede a darle de alta." % user)

                u = None;


                try:
                    u = User.register(str(displayName), "xxx%s" % user, email)
                    u.put()
                except:
                    logging.error("Error al dar de alta al usuario %s" % user)

                userexists = u
                logging.error("userlogged:%s" % str(userexists.key().id()))
                logging.error("userlogged:%s" % userexists.name)

                self.login(userexists, rem)
                #loged_user(userexists.name)
                self.redirect('/ioffer/welcome')

            else:

                self.login(userexists, rem)
                loged_user(userexists.name)
                self.redirect('/ioffer/welcome')
                #self.render('ioffer_welcome.html', user = displayName, categories = categories, countries = countries, last_10_offers = self.get_last_10_offers(), geo_params = self.get_geo_params())

        else:

            user = User.login(username, password)
            logging.error("user:%s" % user)
            if user:
                self.login(user, rem)
                loged_user(username)
                self.redirect('/ioffer/welcome')
            else:
                logging.error("login error")
                msg = 'Invalid login'
                self.render('login-form.html', error = msg)

class Logout(BaseHandler):
    def get(self):
        #self.session['user'] = None
        #self.session['profile'] = None
        self.logout()
        self.redirect('/ioffer/welcome')

class Welcome(BaseHandler):
    def get(self):
        uid = self.read_secure_cookie('user_id')
        user = uid and User.by_id(int(uid))
        logging.error('DB Query')
        logged_username = user and user.name

        

        if logged_username == '' or logged_username == None:
            self.redirect('/')
        else:

            offer_added = self.request.get('offer_added')

            u = loged_user(logged_username) #User.by_name(logged_username)

            profile = loged_profile(logged_username) 

            logging.error('profile en welcome: %s' % profile)

            if  valid_username(logged_username):
                if profile:

                    if offer_added:
                        self.render('ioffer_welcome.html', user = u, profile = profile, categories = categories, offer_added = True, last_10_offers = self.get_last_10_offers())
                    else:
                        self.render('ioffer_welcome.html', user = u, profile = profile, categories = categories, countries = countries, last_10_offers = self.get_last_10_offers(), geo_params = self.get_geo_params())
                else:
                    self.render('ioffer_welcome.html', user = u, last_10_offers = self.get_last_10_offers(), categories = categories, geo_params = self.get_geo_params())
            
            else:
                error_username = 'There was an error with user %s' % logged_username
                self.render('ioffer_welcome.html', user = u, error_username = error_username, last_10_offers = self.get_last_10_offers(), categories = categories, geo_params = self.get_geo_params())
            
class Init(BaseHandler):
    def get(self):
        # self.prueba()
        
        self.render('/ioffer_welcome.html', last_10_offers = self.get_last_10_offers(), categories = categories, countries = countries, geo_params = self.get_geo_params())

class Show_Profile(BaseHandler):

    def post(self):
        logged_username = self.request.get("user")

        u = loged_user(logged_username)
        profile = loged_profile(logged_username) #u.profiles #It is a set, but by now it only contains 1 profile 

        oprofile_types = collections.OrderedDict(sorted(profile_types.items()))

        if profile is None:
            logging.error('Show_Profile profile: %s' % profile)
            params = dict(username = logged_username, default_selected_type = 'empresa')
            self.render('ioffer_profile_form.html', params = params, countries = countries, profile_types = oprofile_types, btn_send = 'Save', last_10_offers = self.get_last_10_offers())
        else:
            self.render('ioffer_profile_form_edit.html', profile = profile, user = u, countries = countries, profile_types = oprofile_types, last_10_offers = self.get_last_10_offers())
            
class Modify_Profile(BaseHandler):

    def post(self):
        logged_username = self.request.get("username")
        u = loged_user(logged_username)
        profile = loged_profile(logged_username)

        logging.error('username: %s' % logged_username)
        logging.error('u: %s' % u)
        logging.error('profile: %s' % profile)

        logging.error('profile.country: %s' % profile.country)

        params = dict(username = profile.user.name, name = profile.name, email = profile.email, phone = profile.phone, profile_type = profile.profile_type, geo_pt = profile.geo_pt, 
            street_address = profile.street_address, address_line_2 = profile.address_line_2, city = profile.city, region = profile.region, zip_code = profile.zip_code, 
            country = profile.country, web = profile.web)

        self.render('ioffer_profile_form.html', params = params, countries = countries, profile_types = profile_types, btn_send = 'Modify', last_10_offers = self.get_last_10_offers())

class Save_Profile(BaseHandler):

    def post(self):
        logging.error("En save_profile")
        have_error = False
        self.username = self.request.get("username")

        self.u = loged_user(self.username)
        

        self.name = self.request.get("name")
        self.original_name = self.request.get("original_name")
        self.profile_type = self.request.get("profile_type")
        self.geo_pt = self.request.get("geo_pt")
        logging.error('self.geo_pt:%s' % self.geo_pt)
        self.email = self.request.get("email")
        self.phone = self.request.get("phone")
        self.street_address = self.request.get("street_address")
        self.address_line_2 = self.request.get("address_line_2")
        self.city = self.request.get("city")
        self.region = self.request.get("region")
        self.zip_code = self.request.get("zip_code")
        self.country = self.request.get("country")
        self.web = self.request.get("web")
        self.facebook = self.request.get("facebook")
        self.twitter = self.request.get("twitter")
        self.youtube = self.request.get("youtube")

        #logging.error('self.country:%s' % self.country)

        params = dict(name = self.name, original_name = self.original_name, email = self.email, phone = self.phone, profile_type = self.profile_type, geo_pt = self.geo_pt, 
            username = self.username, street_address = self.street_address, address_line_2 = self.address_line_2, city = self.city, region = self.region, zip_code = self.zip_code, 
            country = self.country, web = self.web, facebook = self.facebook, twitter = self.twitter, youtube = self.youtube)

        if not valid_name(self.name):
            params['error_name'] = "Invalid name"
            have_error = True
        
        if not valid_email(self.email):
            params['error_email'] = "Invalid email"
            have_error = True

        if have_error:
            logging.error('params:%s' % params)
            self.render('ioffer_profile_form.html', params = params, countries = countries, profile_types = profile_types, btn_send = 'Modify', last_10_offers = self.get_last_10_offers())
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
            p = Profile.save_profile(self.u.name, self.u, self.name, self.profile_type, geo_converter(self.geo_pt), self.phone, self.email, self.street_address, self.address_line_2, self.region, self.city, 
                self.zip_code, self.country, self.web, self.facebook, self.twitter, self.youtube)
            p.put()
        else:
            logging.error('A modificar profile')
            #logging.error('key:%s' % db.get(profile.key()))
            p = Profile.update_profile(profile, self.u, self.name, self.profile_type, geo_converter(self.geo_pt), self.phone, self.email, self.street_address, self.address_line_2, self.region, self.city, 
                self.zip_code, self.country, self.web, self.facebook, self.twitter, self.youtube)

        self.u = loged_user(self.u.name, True)
        p = loged_profile(self.u.name, True)
        self.render('ioffer_profile_form_edit.html', profile = p, user = self.u, countries = countries, profile_types = profile_types, last_10_offers = self.get_last_10_offers())            


class Show_Add_Offer(BaseHandler):

    def post(self):
        logged_username = self.request.get("user")
        offerid = self.request.get("offerid")
 
        u = loged_user(logged_username)
        p = loged_profile(logged_username) #u.profiles #It is a set, but by now it only contains 1 profile

        o = None

        if not offerid is None and not offerid == '':
            o = queried_offers(offerid)

        #logging.error('offerrrrrrrrrrrrrrrrrrr:%s' % o)
        if p is None:
            self.render('no_offers.html', text = 'Fill in your profile to start publishing offers.', last_10_offers = self.get_last_10_offers())
        elif o is None:#No hay oferta asi que se page es alta
            #logging.error('Show_Add_Offer profile: %s' % p)
            self.render('ioffer_add_offer_form.html', profile = p, user = u, categories = categories, currencies = currencies, last_10_offers = self.get_last_10_offers(), page = 'a')
        else:#Viene oferta asi que va a modificar oferta
            #logging.error('Show_Add_Offer profile: %s' % p)
            #logging.error('Show_Add_Offer offer: %s' % o)
            self.render('ioffer_add_offer_form.html', profile = p, user = u, offer = o, categories = categories, currencies = currencies, last_10_offers = self.get_last_10_offers(), page = 'm')


def getImageObject(imgObject):
    return images.Image (imgObject)

def getInitListFiles(listOfFiles):
    return [{'content': f.file.read(),
                         'filename': f.filename, 'mimetype': f.type, 'img_format': f.type.split('/')[1], 
                         'img_width': None, 'img_height': None} for f in listOfFiles]


                         # , 
                         # 'img_width': getImageObject(f.file.read()).width, 'img_height': getImageObject(f.file.read()).height


def getFinalListFiles(listOfFiles):
    return [{'content': f['content'],
                         'filename': f['filename'], 'mimetype': f['mimetype'], 'img_format': f['img_format'], 
                         'img_width': getImageObject(f['content']).width, 'img_height': getImageObject(f['content']).height} for f in listOfFiles]

def getFinalListFilesLight(listOfFiles):
    return [{'filename': f['filename'], 'mimetype': f['mimetype'], 'img_format': f['img_format'], 
                         'img_width': getImageObject(f['content']).width, 'img_height': getImageObject(f['content']).height} for f in listOfFiles]                         

class Add_Offer(BaseHandler, blobstore_handlers.BlobstoreUploadHandler):

    def post(self):
        have_error = False
        self.username = self.request.get("username")

        #logging.error('self.username:%s' % self.username )

        self.u = loged_user(self.username)

        self.name = self.request.get("name")
        self.offer_tittle = self.request.get("offer_tittle")
        #logging.error('self.offer_tittle:%s' % self.offer_tittle )

        


        self.offer_category = self.request.get("offer_category")
        #logging.error('self.offer_category:%s' % self.offer_category )
        self.offer_short_desc = self.request.get("offer_short_desc")
        self.offer_desc = self.request.get("offer_desc")
        #logging.error('self.offer_desc:%s' % self.offer_desc )
        self.offer_start_date = self.request.get("offer_start_date")
        #logging.error('self.offer_start_date:%s' % self.offer_start_date )
        self.offer_end_date = self.request.get("offer_end_date")
        #logging.error('self.offer_end_date:%s' % self.offer_end_date )

        self.offer_before = self.request.get("offer_before")
        self.offer_after = self.request.get("offer_after")
        self.offer_currency = self.request.get("offer_currency")

        self.image_offer = self.request.POST.getall("image_offer")
        #logging.error("self.image_offer:%s" % self.image_offer)
        #logging.error("self.image_offer[0]:%s" % self.image_offer[0])

        #logging.error('type(self.image_offer):%s' % type(self.image_offer))

        self._attachments = getInitListFiles(self.image_offer)

        #logging.error('type(self._attachments):%s' % type(self._attachments))

        self._attachmentslight = getFinalListFilesLight(self._attachments)

        self._attachments = getFinalListFiles(self._attachments)

        #logging.error('type(self._attachments):%s' % type(self._attachments))

        self.page = self.request.get("page")



        # [{'content': f.file.read(),
        #                  'filename': f.filename, 'mimetype': f.type} for f in self.image_offer]

        

        # img_format = self._attachments[0]['mimetype'].split('/')[1]

        # imageObj = images.Image (self._attachments[0]['content'])

        # img_width = imageObj.width
        # img_height = imageObj.height
        # logging.error('uploaded image is %s x %s [%s]' % (img_width, img_height, img_format))

        # img_format = mimetype.split('/')[1]

        # if (img_format == 'jpeg' or 'jpg' or 'gif' or 'png' or 'bmp' or 'tiff' or 'ico' or 'webp'):
        #     imageObj = images.Image (img_stream)
        #     width = imageObj.width
        #     height = imageObj.height
        #     self.response.out.write ('<html><body>uploaded image is %s x %s [%s]</body></html>' % (width, height, img_format))
        # else:
        #     self.response.out.write ('not valid format')

        #logging.error("_attachments:%s" % self._attachments[0]['content'])

        self.offer_conditions = self.request.get("offer_conditions")
        #logging.error('self.offer_conditions:%s' % self.offer_conditions )
        self.offerid = ""
        self.offerid = self.request.get("offerid")

        self.img_deletes = self.request.get_all("img_deletes")
        #logging.error('self.img_deletes:%s' % self.img_deletes )

        logging.info("En add_offer")
        #logging.error("offerid:%s" % self.offerid)

        params = dict(offer_tittle = self.offer_tittle, offer_category = self.offer_category, offer_short_desc = self.offer_short_desc, offer_desc = self.offer_desc, 
            offer_start_date = self.offer_start_date, offer_end_date = self.offer_end_date, offer_before = self.offer_before, offer_after = self.offer_after, 
            offer_currency = self.offer_currency, image_offer = self._attachmentslight, offer_conditions = self.offer_conditions, offerid = self.offerid)

        if self.offer_tittle is None or self.offer_tittle == '':
            params['error_offer_tittle'] = 'El titulo no puede ser vacio'
            have_error = True


        if self.offer_category is None or self.offer_category == '':
            params['error_offer_category'] = 'La categoria no puede ser vacio'
            have_error = True


        if self.offer_short_desc is None or self.offer_short_desc == '':
            params['error_offer_short_desc'] = 'La desc corta no puede ser vacio'
            have_error = True

        if self.offer_desc is None or self.offer_desc == '':
            params['error_offer_desc'] = 'La desc no puede ser vacio'
            have_error = True

        if not self.offer_end_date is None and not self.offer_end_date == '':
            datefin = datetime.datetime.strptime(self.offer_end_date, "%m/%d/%Y")
            if datefin.date() <= datetime.date.today():
                params['error_offer_end_date'] = 'La fecha del final de la oferta no puede ser anterior a hoy'
                have_error = True


        # if not valid_name(self.name):
        #     params['error_name'] = "Invalid name"
        #     have_error = True


        if self._attachments:
            for f in self._attachments:
                #logging.error('filename:%s' % f['filename'])
                #logging.error('\tmimetype:%s' % f['mimetype'])
                #logging.error('\timg_format:%s' % f['img_format'])
                #logging.error('\timg_width:%s' % f['img_width'])
                #logging.error('\timg_height:%s' % f['img_height'])

                if (f['img_format'] == 'jpeg' or 'jpg' or 'gif' or 'png' or 'bmp' or 'tiff' or 'ico' or 'webp'):
                    if int(f['img_width']) < 500:
                        params['error_img'] = 'Invalid image width:%spx. It must be at least 500px width.' % f['img_width']
                        params['filename'] = f['filename']
                        have_error = True
                    if int(f['img_height']) < 500:
                        params['error_img'] = 'Invalid image height:%spx. It must be at least 500px height.' % f['img_height']
                        params['filename'] = f['filename']
                        have_error = True
                else:
                    params['error_img'] = "Invalid image format:%s" % f['img_format']
                    params['filename'] = f['filename']
                    have_error = True

        if have_error:
            #self.render('welcome.html', last_10_offers = self.get_last_10_offers(), categories = categories, **params)
            params['hubo_error'] = 'yes'
            #logging.error('params:%s' % params)
            o = None
            if not self.offerid is None and not self.offerid == '':
                o = queried_offers(self.offerid)
            self.render('ioffer_add_offer_form.html', profile = self.u.profiles[0], user = self.u, categories = categories, currencies = currencies, offer = o, params = params, page = self.page)
            
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError

class Send_Offer(Add_Offer):
    def done(self):
        #u = User.by_name(self.username)
        #p = u.profiles #It is a set, but by now it only contains 1 profile
        profile = loged_profile(self.username)

        o = None
        if not self.offerid is None and not self.offerid == '':
            o = queried_offers(self.offerid)

        #logging.error('offerrrrrrrrrrrrrrrrrrr to modify:%s' % o)
        if not o is None:
            logging.info('A modificar offer')

            for key_img_delete in self.img_deletes:
                offer_im = Offer_Image.by_id(long(key_img_delete))
                offer_im.delete()

            logging.error('self.offer_before: %s' % self.offer_before)

            offer = Offer.update_offer(o, self.offer_tittle, self.offer_category, self.offer_short_desc, self.offer_desc, datetime.datetime.strptime(self.offer_start_date, "%m/%d/%Y"), 
                datetime.datetime.strptime(self.offer_end_date, "%m/%d/%Y"), float(self.offer_before), float(self.offer_after), self.offer_currency, self.offer_conditions)

            if self._attachments:
                for f in self._attachments:
                    oi = Offer_Image.save_offer_image(offer=offer, image_file_name=f['filename'], image_blob=f['content'])
                    oi.put()

            #offer.put()

            offers_user = loged_offers(self.u.name, True)
            offer = queried_offers(self.offerid, True)
            #logging.error('offer.offer_tittle:%s' % offer.offer_tittle)
            self.render('ioffer_offers_form.html', offer = offer, categories = categories, last_10_offers = self.get_last_10_offers())
        else:
            logging.info('A guardar offer')
            o = Offer.save_offer(profile, self.u.name, self.name, self.offer_tittle, self.offer_category, self.offer_short_desc, self.offer_desc, 
                datetime.datetime.strptime(self.offer_start_date, "%m/%d/%Y"), datetime.datetime.strptime(self.offer_end_date, "%m/%d/%Y"), 
                float(self.offer_before), float(self.offer_after), self.offer_currency, self.offer_conditions)
            o.put()

            if self._attachments:
                for f in self._attachments:
                    oi = Offer_Image.save_offer_image(offer=o, image_file_name=f['filename'], image_blob=f['content'])
                    oi.put()


            offers_user = loged_offers(self.u.name, True)
            #self.redirect('/ioffer/welcome?offer_added=True')
            #self.render('welcome.html', username = u.name, profile = p, categories = categories, offer_added = True)
            self.render('ioffer_offers_user.html', offers_user = offers_user, user = self.u, categories = categories, offer_added = True, last_10_offers = self.get_last_10_offers())
            #self.render('welcome.html', offer_added = True)

class Offers_User_Display(BaseHandler):
    def post(self):
        logged_username = self.request.get("username")
        u = loged_user(logged_username)
        profile = loged_profile(logged_username)


        # url = '%s/rest/offer?feq_username=%s' % (self.request.host_url, logged_username)
        # try:
        #     data = urlfetch.fetch(url).content
        #     # if result.status_code == 200:
        #     #     self.response.write(result.content)
        #     # else:
        #     #     self.response.status_code = result.status_code
        # except urlfetch.Error:
        #     logging.exception('Caught exception fetching url')

        # # response = requests.get('http://localhost:15080/rest/offer')
        # data = json.loads(data)
        # #data = data.json()
        # logging.error('DATA-->%s' % data)
        # logging.error('DATA type-->%s' % type(data))

        if profile:

            #logging.error('profile en offers_display: %s' % profile)

            #offers_user = db.GqlQuery("select * from Offer where username=:1", username)
            #offers_user = profile.offers
            offers_user = loged_offers(logged_username)
            number_of_offers = offers_user.count()
            #logging.error('offers_user en offers_display: %s' % type(offers_user))
            #logging.error('offers_user.count: %s' % number_of_offers)

            if number_of_offers > 0:
                self.render('ioffer_offers_user.html', offers_user = offers_user, user = u, categories = categories, last_10_offers = self.get_last_10_offers())
            else:
                self.render('no_offers.html', text='There are no offers yet', last_10_offers = self.get_last_10_offers())
        else:
            self.render('no_offers.html', text='There are no offers yet. You must first create a profile to start adding offers', last_10_offers = self.get_last_10_offers())



class OfferPage(BaseHandler):
    def get(self, offer_id):
        # key = db.Key.from_path('Offer', int(offer_id), parent=offers_key())
        # offer = db.get(key)

        offer = queried_offers(offer_id)

        if not offer:
            self.error(404)
            return

        self.render('ioffer_offers_form.html', offer = offer, categories = categories)

class OfferPageShow(BaseHandler):
    def get(self, offer_id):
        # key = db.Key.from_path('Offer', int(offer_id), parent=offers_key())
        # offer = db.get(key)

        offer = queried_offers(offer_id)

        if not offer:
            self.error(404)
            return

        self.render('ioffer_offers_show_form.html', offer = offer, categories = categories)        

class OffersListShow(BaseHandler):
    def get(self):

        lat1 = self.request.get("lat1")
        lon1 = self.request.get("lon1")


        #self.offers = list_offers_loc(lat1, lon1) #(53.4211041, -7.942588199999999)
        self.offers = offers = Profile.by_loc(lat1, lon1)
        logging.error('offers.results: %s' % type(self.offers.results))
        logging.error('offers.results[0]: %s' % type(self.offers.results[0]))
        logging.error('offers.results[0].fields: %s' % type(self.offers.results[0].fields))
        logging.error('al loro: %s' % self.offers)

        self.render('ioffer_offers_list.html', offers = self.offers)  

class ServeHandler(BaseHandler, blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, resource):
        resource = str(urllib.unquote(resource))
        #image = db.Key('Images', resource).get()
        #image = db.Key('Offer_Image', resource).get()
        image = Offer_Image.by_id(long(resource))
        #logging.error('image:%s' % type(image))
        self.response.headers[b'Content-Type'] = mimetypes.guess_type(image.image_file_name)[0]
        self.response.write(image.image_blob)

# class Show_Country_Regions(BaseHandler):
#     def post(self):
#         country = self.request.get("country")

#         nom_fich = "%s_REG.csv" % country

#         logging.error('nom_fich: %s' % nom_fich)

#         try:
#             fich = open(nom_fich, 'r')
#         except:
#             logging.error("El fichero no existe")
#             return

#         list_regs = []

#         for line_reg in fich:
#             reg_fields = line_reg.split(",")
#             reg_params = dict(reg_code = reg_fields[1], reg_value = reg_fields[2])
#             list_regs.append(reg_params)

#         logging.error('list_regs: %s' % list_regs) 

#         self.render('regions.html', list_regs = list_regs) 

# class Show_Region_Cities(BaseHandler):
#     def post(self):
#         #country = self.request.get("country")
#         region = self.request.get("region")

#         nom_fich = "%s_%s_CIT.csv" % ("ES", region)

#         logging.error('nom_fich: %s' % nom_fich)

#         try:
#             fich = open(nom_fich, 'r')
#         except:
#             logging.error("El fichero no existe")
#             return

#         list_cities = []

#         for line_reg in fich:
#             reg_fields = line_reg.split(",")
#             reg_params = dict(cit_code = reg_fields[0] + "_" + reg_fields[1] + "_" + reg_fields[2], cit_value = reg_fields[4], cit_zipcode = reg_fields[3])
#             list_cities.append(reg_params)

#         logging.error('list_cities: %s' % list_cities) 

#         self.render('cities.html', list_cities = list_cities) 

rest.Dispatcher.base_url = "/rest"

rest.Dispatcher.add_models({
  'offer' : (Offer, rest.READ_ONLY_MODEL_METHODS),
  'profile' : (Profile, ['GET_METADATA', 'GET', 'POST', 'PUT']) })

app = webapp2.WSGIApplication([
    ('/', Init),
    ('/rest/.*', rest.Dispatcher),
    ('/ioffer/signup', Register),
    ('/ioffer/signup_show', Signup_IOffer_Show),
    ('/ioffer/login', Login_IOffer),
    ('/ioffer/login_show', Login_IOffer_Show),
    ('/ioffer/logout', Logout),
    ('/ioffer/send_profile', Send_Profile),
    ('/ioffer/modify_profile', Modify_Profile),
    ('/ioffer/show_add_offer', Show_Add_Offer),
    ('/ioffer/add_offer', Send_Offer),
    ('/ioffer/offer_list', OffersListShow),
    ('/ioffer/offers_user_display', Offers_User_Display),
    ('/ioffer/show_profile', Show_Profile),
    # ('/ioffer/show_country_regions', Show_Country_Regions),
    # ('/ioffer/show_region_cities', Show_Region_Cities),
    ('/ioffer/offer/([0-9]+)', OfferPage),
    ('/ioffer/offer_show/([0-9]+)', OfferPageShow),
    ('/ioffer/images/([0-9]+)', ServeHandler),
    ('/ioffer/welcome', Welcome)], config=config, debug=True)

