from google.appengine.ext import db
from models.Profile import Profile

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
    offer_desc = db.TextProperty()
    offer_start_date = db.DateTimeProperty()
    offer_end_date = db.DateTimeProperty()
    image_offer = db.StringProperty()
    offer_conditions = db.StringProperty()

    @classmethod
    def by_id(cls, pid):
        return Offer.get_by_id(pid, parent = offers_key())

    @classmethod
    def by_title(cls, title):
        o = Offer.all().filter('title =', title).get()
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
    def save_offer(cls, profile, username, name, offer_tittle, offer_category, offer_desc = None, offer_start_date = None, offer_end_date = None, image_offer = None, offer_conditions = None):

        return Offer(parent = offers_key(),
                    profile = profile,
                    username = username,
                    name = name,
                    offer_tittle = offer_tittle,
                    offer_category = offer_category,
                    offer_desc = offer_desc,
                    offer_start_date = offer_start_date,
                    offer_end_date = offer_end_date,
                    image_offer = image_offer,
                    offer_conditions = offer_conditions)