from google.appengine.ext import db
from models.User import User
import logging

def profiles_key(group = 'default'):
    return db.Key.from_path('profiles', group)

class Profile(db.Model):
    user = db.ReferenceProperty(User,
                                   collection_name='profiles') #relation is 1 to 1 by now, but it is fine
    name = db.StringProperty(required = True)
    profile_created = db.DateTimeProperty(auto_now_add = True)
    profile_last_modified = db.DateTimeProperty(auto_now = True)
    email = db.StringProperty()
    profile_type = db.StringProperty(required = True)
    phone = db.StringProperty()
    street_address = db.StringProperty()
    address_line_2 = db.StringProperty()
    region = db.StringProperty()
    city = db.StringProperty()
    zip_code = db.StringProperty()
    country = db.StringProperty()
    web = db.StringProperty()

    @classmethod
    def by_id(cls, pid):
        return Profile.get_by_id(pid, parent = profiles_key())

    @classmethod
    def by_name(cls, name):
        p = Profile.all().filter('name =', name).get()
        return p

    @classmethod
    def by_user(cls, user):
        p = Profile.all().filter('user =', user).get()
        return p

    @classmethod
    def save_profile(cls, key_name, user, name, profile_type, phone = None, email = None, street_address = None, address_line_2 = None, region = None, city = None, zip_code = None, country = None, web = None):

        return Profile(parent = profiles_key(),
                    key_name = user.name,
                    user = user,
                    name = name,
                    phone = phone,
                    email = email,
                    profile_type = profile_type,
                    street_address = street_address,
                    address_line_2 = address_line_2,
                    region = region,
                    city = city,
                    zip_code = zip_code,
                    country = country,
                    web = web)    

    @classmethod
    def update_profile(profile, key_name, user, name, profile_type, phone = None, email = None, street_address = None, address_line_2 = None, region = None, city = None, zip_code = None, country = None, web = None):

        key_name.name = name
        key_name.phone = phone
        key_name.email = email
        key_name.profile_type = profile_type
        key_name.street_address = street_address
        key_name.address_line_2 = address_line_2
        key_name.region = region
        key_name.city = city
        key_name.zip_code = zip_code
        key_name.country = country
        key_name.web = web

        key_name.put()
        return key_name