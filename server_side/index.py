import webapp2
import os
import logging
from google.appengine.ext.webapp import template
from google.appengine.api import app_identity



class MainPage(webapp2.RequestHandler):
    def get(self):
        # logging.info('hai')
        path = os.path.join(os.path.dirname(__file__), '../templates/index.html')
        self.response.out.write(template.render(path, {}))


app = webapp2.WSGIApplication([
    ('/', MainPage)], debug=True)