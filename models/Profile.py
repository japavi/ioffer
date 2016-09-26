from google.appengine.ext import db
from google.appengine.api import search
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
    facebook = db.StringProperty()
    twitter = db.StringProperty()
    youtube = db.StringProperty()
    geo_pt = db.GeoPtProperty()

            




    @classmethod
    def by_loc(cls, lat1, long1):

        coords = (lat1, long1)
        query = Profile.all()
        logging.error('tuputamadreyaquevamos: %s' % query)
        index = search.Index(name="geosearch1")

        try:
            while True:
                document_ids = [document.doc_id for document in index.get_range(ids_only=True)]
                if not document_ids:
                    break
                index.delete(document_ids)
        except search.Error:
            logging.exception("Error removing documents:")


        for entity in query:
            geopoint = search.GeoPoint(entity.geo_pt.lat, entity.geo_pt.lon)

            logging.error('geopoint: %s' % geopoint)

            offers = entity.offers

            for offer in offers:

                logging.error('entity.key().id(): %s' % entity.key().id())
                logging.error('offer.key().id(): %s' % offer.key().id())

                my_document = search.Document(
                    doc_id = str(offer.key().id()),
                    fields=[
                       search.TextField(name='name', value=entity.name),
                       search.TextField(name='city', value=entity.city),
                       search.TextField(name='country', value=entity.country),
                       search.TextField(name='offer_id', value=str(offer.key().id())),
                       search.TextField(name='offer_title', value=offer.offer_tittle),
                       search.TextField(name='offer_category', value=offer.offer_category),
                       search.TextField(name='offer_before', value=str(offer.offer_before)),
                       search.TextField(name='offer_after', value=str(offer.offer_after)),
                       search.TextField(name='offer_currency', value=offer.offer_currency),
                       search.GeoField(name='location', value=geopoint)
                       ])
                index.put(my_document)

        
        query_string = "distance(location, geopoint(%s, %s)) < 5000" % coords

        sort_distance = search.SortExpression(
        expression='distance(location, geopoint(%s, %s))' % coords,
        direction=search.SortExpression.ASCENDING,
        default_value=0)

        distance_expression = search.FieldExpression(
        name='distance', expression='distance(location, geopoint(%s, %s))' % coords)


        sort_options = search.SortOptions(expressions=[sort_distance])

        query_options = search.QueryOptions(returned_expressions=[distance_expression],sort_options=sort_options)

        query_dist = search.Query(query_string=query_string, options=query_options)


        search_results = index.search(query_dist)

        logging.error('tuputamadreya: %s' % search_results)

        return search_results

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
    def save_profile(cls, key_name, user, name, profile_type, geo_pt, phone = None, email = None, street_address = None, address_line_2 = None, region = None, city = None, zip_code = None, 
        country = None, web = None, facebook = None, twitter = None, youtube = None):

        return Profile(parent = profiles_key(),
                    key_name = user.name,
                    user = user,
                    name = name,
                    phone = phone,
                    email = email,
                    profile_type = profile_type,
                    geo_pt = geo_pt,
                    street_address = street_address,
                    address_line_2 = address_line_2,
                    region = region,
                    city = city,
                    zip_code = zip_code,
                    country = country,
                    web = web,
                    facebook = facebook,
                    twitter = twitter,
                    youtube = youtube)    

    @classmethod
    def update_profile(profile, key_name, user, name, profile_type, geo_pt, phone = None, email = None, street_address = None, address_line_2 = None, region = None, city = None, 
        zip_code = None, country = None, web = None, facebook = None, twitter = None, youtube = None):

        key_name.name = name
        key_name.phone = phone
        key_name.email = email
        key_name.profile_type = profile_type
        key_name.geo_pt = geo_pt
        key_name.street_address = street_address
        key_name.address_line_2 = address_line_2
        key_name.region = region
        key_name.city = city
        key_name.zip_code = zip_code
        key_name.country = country
        key_name.web = web
        key_name.facebook = facebook
        key_name.twitter = twitter
        key_name.youtube = youtube

        key_name.put()
        return key_name
