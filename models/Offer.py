from google.appengine.ext import db
from models.Profile import Profile
import logging

def offers_key(group = 'default'):
    return db.Key.from_path('offers', group)    

class Offer(db.Model):
    profile = db.ReferenceProperty(Profile,
                                   collection_name='offers')

    username = db.StringProperty(required = True)
    name = db.StringProperty(required = True)
    offer_tittle = db.StringProperty(required = True)
    offer_category = db.StringProperty(required = True)
    offer_created = db.DateTimeProperty(auto_now_add = True)
    offer_last_modified = db.DateTimeProperty(auto_now = True)
    offer_short_desc = db.TextProperty()
    offer_desc = db.TextProperty()
    offer_start_date = db.DateTimeProperty()
    offer_end_date = db.DateTimeProperty()
    offer_before = db.FloatProperty()
    offer_after = db.FloatProperty()
    offer_currency = db.StringProperty()
    #image_offer = db.BlobProperty()
    offer_conditions = db.TextProperty()

    @classmethod
    def by_id(cls, pid):
        return Offer.get_by_id(pid, parent = offers_key())

    @classmethod
    def by_title(cls, title):
        logging.error('cls:%s' % cls)
        logging.error('title:%s' % title)
        o = Offer.all().filter('offer_tittle =', title).get()
        logging.error('o:%s' % o)
        return o

    @classmethod
    def by_username(cls, username):
        o = Offer.all().filter('username =', username).get()
        return o

    @classmethod
    def by_profile(cls, profile):
        o = Offer.all().filter('profile =', profile).get()
        return o

    @classmethod
    def save_offer(cls, profile, username, name, offer_tittle, offer_category, offer_short_desc, offer_desc = None, offer_start_date = None, offer_end_date = None, 
        offer_before = None, offer_after = None, offer_currency = None, offer_conditions = None):

        return Offer(parent = offers_key(),
                    profile = profile,
                    username = username,
                    name = name,
                    offer_tittle = offer_tittle,
                    offer_category = offer_category,
                    offer_short_desc = offer_short_desc,
                    offer_desc = offer_desc,
                    offer_start_date = offer_start_date,
                    offer_end_date = offer_end_date,
                    offer_before = offer_before,
                    offer_after = offer_after,
                    offer_currency = offer_currency,
                    offer_conditions = offer_conditions)

    @classmethod
    def update_offer(offer, key_name, offer_tittle, offer_category, offer_short_desc, offer_desc = None, offer_start_date = None, offer_end_date = None, 
        offer_before = None, offer_after = None, offer_currency = None, offer_conditions = None):

        
        logging.error('offer_before: %s' % offer_before)
        key_name.offer_tittle = offer_tittle
        key_name.offer_category = offer_category
        key_name.offer_short_desc = offer_short_desc
        key_name.offer_desc = offer_desc
        key_name.offer_start_date = offer_start_date
        key_name.offer_end_date = offer_end_date
        key_name.offer_before = float(offer_before)
        key_name.offer_after = float(offer_after)
        key_name.offer_currency = offer_currency
        key_name.offer_conditions = offer_conditions

        key_name.put()
        return key_name