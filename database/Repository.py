from google.appengine.ext import db, ndb

class SMSRepository(ndb.Model):
	smsjson = ndb.JsonProperty()
