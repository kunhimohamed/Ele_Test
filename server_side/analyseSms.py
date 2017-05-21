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
		JsonDict = {'messages':jsonList}
		SenderNames = [eachCont for eachCont in set([each.get("number",None) for each in JsonDict['messages']]) if eachCont]
		SenderNamesFinalDict = {}
		FrontEndDict = {}

		for eachItem in SenderNames:
			if (('+' in str(eachItem)[1:-1]) or (str(eachItem)[1:-1].isdigit())):
				continue
			elif ('-' in str(eachItem)[1:-1]):
				if not (str(eachItem)[1:-1].split('-')[1].isdigit()):
					SenderNamesFinalDict[eachItem] = str(eachItem)[1:-1].split('-')[1]
			else:
				SenderNamesFinalDict[eachItem] = str(eachItem)[1:-1]

		for each in SenderNamesFinalDict:
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
			FrontEndDict[SenderNamesFinalDict[each]] = [str(TotalSmsCount), str(TotalTextmsgCount), str(TotalPromoCount)]

		wholeDict = {}
		for each in SenderNamesFinalDict:
			StoredList = []
			for eachOne in JsonDict['messages']:
				checkList = [eachData[1:-1] if (eachData.startswith('"') and eachData.endswith('"')) else eachData for eachData in eachOne.values()]
				if str(each)[1:-1] in checkList:
					StoredList.append(eachOne)
			if ('-' in str(each)[1:-1]):
				wholeDict[str(each)[1:-1].split('-')[1]] = StoredList
			else:
				wholeDict[str(each)[1:-1]] = StoredList

		storedJson = SMSRepository()
		storedJson.smsjson = json.dumps(wholeDict)
		Key = storedJson.put()
		logging.info(Key)
		time.sleep(5)
		memcache.set(key='fronEndDict', value=FrontEndDict)
		memcache.set(key='jsonKey', value=Key)
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
		try:
			logging.info(json.loads(self.request.body))
			sender = json.loads(self.request.body)['sender']
			JsonDict = json.loads(ndb.Key('SMSRepository',int(json.loads(self.request.body)["jsonkeyid"])).get().smsjson)
			logging.info(JsonDict)
			self.response.headers['Content-Type'] = 'application/json'
			self.response.out.write(json.dumps({sender:JsonDict[sender]}))
		except:
			self.response.headers['Content-Type'] = 'application/json'
			self.response.out.write(json.dumps({sender:[{'text':'could not find the key'}]}))	
		

application = webapp2.WSGIApplication([('/tobloburl', CreateBlobUrl),('/getbloburl', CreateBlobUrl),
	('/SaveDataInBlob', SaveContentInBlob), ('/tofrontend', DisplayToFront), ('/processfile', ProcessFileSaveIntoDb),
	('/forCollapseData', forCollapse)], debug=True)