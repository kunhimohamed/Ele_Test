import os
import webapp2
import logging
import json
from google.appengine.api import memcache
from google.appengine.ext.webapp import template
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from database.Repository import *
import time

class CreateBlobUrl(webapp2.RequestHandler):
	def get(self):
		upload_url = blobstore.create_upload_url('/SaveDataInBlob')
		data = {"url": upload_url}
		self.response.headers['Content-Type'] = 'application/json'
		self.response.out.write(json.dumps(data))

class SaveContentInBlob(blobstore_handlers.BlobstoreUploadHandler):
	def post(self):
		logging.info(self.get_uploads('file'))
		data = {"key": str(self.get_uploads('file')[0].key())}
		logging.info(data)
		self.response.headers['Content-Type'] = 'application/json'
		self.response.out.write(json.dumps(data))
		

class ProcessFileSaveIntoDb(webapp2.RequestHandler):
	def post(self):
		logging.info(json.loads(self.request.body)['key'])
		messageList = []
		file = blobstore.BlobReader(json.loads(self.request.body)['key'])
		messageList = []
		for line in file:
			messageList.append(line)
		StripedMessageList = [each.rstrip() for each in messageList]
		#print y
		MessageDict = {}
		jsonList = []
		for each in StripedMessageList:
			if (('=' in each) or ('{' in each)):
				continue
			elif ('}' in each):
				jsonList.append(MessageDict)
				MessageDict = {}
				continue
			else:
				MessageDict[each.split(':')[0].strip()[1:-1]] = "".join(each.split(':')[1:]).strip().replace(',','')
		storedJson = SMSRepository()
		storedJson.smsjson = json.dumps({'messages':jsonList})
		Key = storedJson.put()
		logging.info(Key)
		time.sleep(5)
		JsonDict = json.loads(Key.get().smsjson)
		SenderNames = set([each.get("number",None) for each in JsonDict['messages']])
		FrontEndDict = {}
		logging.info(SenderNames)
		# logging.info(JsonDict)
		# FrontEndDict['total_number_of_senders'] = len(SenderNames)
		for each in SenderNames:
			TotalSmsCount = 0
			TotalTextmsgCount = 0
			TotalPromoCount = 0
			for eachOne in JsonDict['messages']:
				SenderDict = {}
				if each in eachOne.values():
					TotalSmsCount = TotalSmsCount + 1
					if not str(each).strip().replace('+','')[1:-1].isdigit():
						TotalPromoCount = TotalPromoCount + 1
					else:
						TotalTextmsgCount = TotalTextmsgCount + 1
			FrontEndDict[str(each)[1:-1]] = [str(TotalSmsCount), str(TotalTextmsgCount), str(TotalPromoCount)]
		memcache.set(key='fronEndDict', value=FrontEndDict)
		memcache.set(key='jsonKey', value=Key)
		logging.info(FrontEndDict)
		self.response.headers['Content-Type'] = 'application/json'
		self.response.out.write(json.dumps(FrontEndDict))

class DisplayToFront(webapp2.RequestHandler):
	def get(self):
		templateValues = memcache.get('fronEndDict')
		jsonKey = memcache.get('jsonKey')
		memcache.flush_all()
		path = os.path.join(os.path.dirname(__file__), '../templates/index_2.html')
		self.response.out.write(template.render(path, {'data':templateValues, 'jsonKey':jsonKey.id()}))

class forCollapse(webapp2.RequestHandler):
	"""docstring for forCollapse"""
	def post(self):
		logging.info(json.loads(self.request.body)["jsonkeyid"])
		# jsonDict = ndb.Key('SMSRepository',int(json.loads(self.request.body)["jsonkeyid"])).get().smsjson
		JsonDict = json.loads(ndb.Key('SMSRepository',int(json.loads(self.request.body)["jsonkeyid"])).get().smsjson)
		wholeDict = {}
		SenderNames = set([each.get("number",None) for each in JsonDict['messages']])
		logging.info(SenderNames)
		for each in SenderNames:
			StoredList = []
			for eachOne in JsonDict['messages']:
				checkList = [eachData[1:-1] if (eachData.startswith('"') and eachData.endswith('"')) else eachData for eachData in eachOne.values()]
				logging.info(checkList)
				logging.info(each)
				strlist = [str(eachContent) for eachContent in checkList]
				logging.info(strlist)
				if str(each)[1:-1] in strlist:
					StoredList.append(eachOne)
			wholeDict[str(each)[1:-1]] = StoredList
		self.response.headers['Content-Type'] = 'application/json'
		self.response.out.write(json.dumps(wholeDict))
		# JsonDict = json.loads(Key('SMSRepository',json.loads(self.request.body)["jsonkeyid"]).get().smsjson)
		# logging.info(JsonDict)

		

application = webapp2.WSGIApplication([('/tobloburl', CreateBlobUrl),('/getbloburl', CreateBlobUrl),
	('/SaveDataInBlob', SaveContentInBlob), ('/tofrontend', DisplayToFront), ('/processfile', ProcessFileSaveIntoDb),
	('/forCollapseData', forCollapse)], debug=True)