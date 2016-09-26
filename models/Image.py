from google.appengine.ext import db
from models.Offer import Offer
import logging

def images_key(group = 'default'):
    return db.Key.from_path('images', group)    

class Offer_Image(db.Model):
    offer = db.ReferenceProperty(Offer,
                                   collection_name='images')

    
    image_file_name = db.StringProperty(required = True)
    image_blob = db.BlobProperty(required = True)

    @classmethod
    def by_id(cls, pid):
        return Offer_Image.get_by_id(pid, parent = images_key())

    @classmethod
    def by_image_file_name(cls, image_file_name):
        oi = Offer_Image.all().filter('image_file_name =', image_file_name).get()
        logging.error('oi:%s' % oi)
        return oi


    @classmethod
    def save_offer_image(cls, offer, image_file_name, image_blob):

        return Offer_Image(parent = images_key(),
                    offer = offer,
                    image_file_name = image_file_name,
                    image_blob = image_blob)

    @classmethod
    def update_offer_image(offer_image, key_name, image_file_name, image_blob):

        key_name.image_file_name = image_file_name
        key_name.image_blob = image_blob

        key_name.put()
        return key_name