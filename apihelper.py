#   Copyright 2015 maximumG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
'''
Created on Jul 15, 2016

@author: Rafael Carvalho (rafacarv@cisco.com)
'''
import requests
import json
import configparser
from datetime import datetime

class APICaller(object):

    cisco_app_name = "None set"

    def __init__(self, cisco_app_name):
        self.cisco_app_name = cisco_app_name
    
    def requestHTTP(self, url, method, headers, payload):
        self.log ("Requesting... " + url)
        response = requests.request(method, url, data=payload, headers=headers)

        #HTTP handling found on https://github.com/maximumG/piapi/blob/master/piapi.py
        if response.status_code == 200:
            self.log ("Success")
        elif response.status_code == 302:
            raise Exception("Incorrect credentials provided")
        elif response.status_code == 400:
            response_json = response.json()
            raise Exception("Invalid request: %s" % response_json["errorDocument"]["message"])
        elif response.status_code == 401:
            raise Exception("Unauthorized access")
        elif response.status_code == 403:
            raise Exception("Forbidden access to the REST API")
        elif response.status_code == 404:
            raise Exception("URL not found %s" % response.url)
        elif response.status_code == 406:
            raise Exception("The Accept header sent in the request does not match a supported type")
        elif response.status_code == 415:
            raise Exception("The Content-Type header sent in the request does not match a supported type")
        elif response.status_code == 500:
            raise Exception("An error has occurred during the API invocation")
        elif response.status_code == 502:
            raise Exception("The server is down or being upgraded")
        elif response.status_code == 503:
            raise Exception("The servers are up, but overloaded with requests. Try again later (rate limiting)")
        else:
            raise APIError("Unknown Request Error, return code is %s" % response.status_code)
        
        #if (response.status_code == 200):
        #    self.logWithCiscoAppName ("Success!")
        #else:
        #    self.logWithCiscoAppName (("Status: {} - Body {}").format(response.status_code, response.content))
        
        return response
    
    def requestHTTPJSON(self, url, method, headers, payload):
        httpResponse = self.requestHTTP(url, method, headers, payload)
        response_json = httpResponse.json() # Get the json-encoded content from response with "response_json = resp.json()
        #self.logWithCiscoAppName (json.dumps(response_json,indent=2))
        return response_json

    def __requestHTTPGET(self,request, url):
        return request.get(url)
    
    def __requestHTTPPOST(self, request, url):
        return request.post(url)
    
    def log (self, message):
        now = datetime.now().strftime("%Y/%m/%dT%H:%M:%S")
        formatted = "[{}][{}] {}".format(now, self.cisco_app_name, message)
        print (formatted)
    


class SparkAPICaller(APICaller):
    # read config
    config = configparser.ConfigParser()
    config.read("config.ini")
    
    token = config.get('spark', 'token')
    
    if (token == "GET-YOUR-TOKEN"):
        print ("Please change the content of the config.ini file with your Spark token. Visit https://developer.ciscospark.com/getting-started.html for a tutorial")
    
    API_SPARK_PRODUCTION = ["Spark", "https://api.ciscospark.com", "Bearer", token]
    API_REGISTERED_SERVERS = [API_SPARK_PRODUCTION]
    API_ACCESS = API_REGISTERED_SERVERS[0]
    
    API_V1 = "v1"
    
    API_MESSAGES = "messages"
    API_ROOMS = "rooms"
    API_WEBHOOKS = "webhooks"
    API_PEOPLE = "people"
    
    API_BASE_URL = API_ACCESS[1]
    API_AUTHENTICATION_TYPE = API_ACCESS[2]
    API_AUTHENTICATION_ID = API_ACCESS[3]
    
    VERSION = API_V1
    
    sparkHeaders = ""
    
    def __init__(self):
        super(SparkAPICaller, self).__init__("SPARK")
        self.sparkHeaders = {
            'authorization': "{} {}".format(self.API_AUTHENTICATION_TYPE, self.API_AUTHENTICATION_ID),
            'content-type': "application/json",
            'cache-control': "no-cache",
        }
    
    def postMessage(self, roomId, toPersonId, toPersonEmail, text, markdown, files):
        #https://developer.ciscospark.com/endpoint-messages-post.html 
        data = {}
        if (roomId):
            data["roomId"] = roomId
        if (toPersonId):
            data["toPersonId"] = toPersonId
        if (toPersonEmail):
            data["toPersonEmail"] = toPersonEmail
        if (text):
            if (len (text) > 7439):
                text = text[:7439]
            data["text"] = text
        if (markdown):
            if (len (markdown) > 7439):
                markdown = markdown[:7439]
            data["markdown"] = markdown
        if (files):
            data["files"] = files
        
        payload = json.dumps(data)
        
        url = self.__buildURLMessages() 
        return super(SparkAPICaller, self).requestHTTP(url, "POST", self.sparkHeaders, payload)
    
    def createWebhookSimplified(self, webhook_name, webhook_targetUrl, webhook_resource, webhook_roomId):   
        webhook_event = "created"
        webhook_filter = "roomId={}".format(webhook_roomId)
        self.createWebhook(webhook_name, webhook_targetUrl, webhook_resource, webhook_event, webhook_filter, None)
    
    def createWebhook (self, webhook_name, webhook_targetUrl, webhook_resource, webhook_event, webhook_filter, webhook_secret):
        #https://developer.ciscospark.com/endpoint-webhooks-post.html 
        
        if (webhook_name and webhook_targetUrl and webhook_resource and webhook_event):
            data = {}
            data["name"] = webhook_name
            data["targetUrl"] = webhook_targetUrl
            data["resource"] = webhook_resource
            data["event"] = webhook_event
            if (webhook_filter):
                data["filter"] = webhook_filter
            if (webhook_secret):
                data["secret"] = webhook_secret
            payload = json.dumps(data)
                
            url = self.__buildURLWebhook() 
            return super(SparkAPICaller, self).requestHTTP(url, "POST", self.sparkHeaders, payload)
        else:
            super(SparkAPICaller, self).log ("Required arguments not passed.")
    
    def getPersonDetails(self, webhook_personId):
        if (webhook_personId):
            url = self.__buildURLPeople() + "/" + webhook_personId
            return super(SparkAPICaller, self).requestHTTPJSON(url, "GET", self.sparkHeaders, None)
        else:
            print ("Required argument not passed.")
    
    def getMessage(self, messageId):
        url = self.__buildURLMessages() + "/" + messageId
        json = super(SparkAPICaller, self).requestHTTPJSON(url, "GET", self.sparkHeaders, None)
        return json["text"]
        
    def getRooms(self):    
        url = self.__buildURLRooms()
        server_response = super(SparkAPICaller, self).requestHTTPJSON(url, "GET", self.sparkHeaders, None)
        return server_response
    
    #HELPER METHODS TO CREATE URL's
    def __buildURLMessages(self):
        return "{}/{}/{}".format(self.API_BASE_URL, self.API_V1, self.API_MESSAGES)
    
    def __buildURLRooms(self):
        return "{}/{}/{}".format(self.API_BASE_URL, self.API_V1, self.API_ROOMS)
    
    def __buildURLWebhook(self):
        return "{}/{}/{}".format(self.API_BASE_URL, self.API_V1, self.API_WEBHOOKS)
    
    def __buildURLPeople(self):
        return "{}/{}/{}".format(self.API_BASE_URL, self.API_V1, self.API_PEOPLE)
    
class APIError(Exception):
    """
    Generic error raised by the API module.
    """
