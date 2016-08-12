from flask import Flask, request
import traceback
import configparser
import datetime
from apihelper import SparkAPICaller

app = Flask(__name__)
spark_api = SparkAPICaller()

@app.route('/')
def hello():
    """Run your server and go browse to the root of your server: http://localhost:5000 and see if it is working. It shows the message Hello Spark World!"""
    return "Hello Spark World!"

@app.route("/webhook_messages", methods=['GET', 'POST'])
def webhook_messages():
    
    output = "Empty"
    
    try:
        parsed_input = parse_user_input(request)
    
        message = parsed_input["message"]
        message_id = parsed_input["message_id"]
        person_id = parsed_input["person_id"]
        person_email = parsed_input["person_email"]
        room_id = parsed_input["room_id"]
        
        #this logs the message on the console
        print ("Received: {}".format(message))
             
        #Build here the message that you want to post back on the same Spark room. 
        will_reply_something = False
        
        #Setting up some default values for the message to be posted.
        post_roomId = room_id #Usually it's the same room where you received the message. 
        post_toPersonId = None #
        post_toPersonEmail = None
        post_text = None
        post_markdown = None
        post_files = None
        
        #Here you will analyze all the messages received on the room and react to them
        #Here's a simple example.
        if (is_this_my_string(message, ["hi"])):
            post_text = "Hello there!"
            will_reply_something = True
        
        #Now we can start playing around with other functions of the Spark API
        elif (is_this_my_string(message, ["show me the money"])):
            post_text = "Here's your money, {}.\nYour Id is <{}>\nThe id of the message that triggered this interaction is <{}>".format(person_email, person_id, message_id)
            post_files = "https://cdn3.iconfinder.com/data/icons/free-icons-3/128/004_money_dollar_cash_coins_riches_wealth.png"
            will_reply_something = True
            
        elif (is_this_my_string (message, ["show me more money"])):
            post_text = "Fancy some gold?"
            post_files = "https://cdn0.iconfinder.com/data/icons/ie_Bright/128/gold.png"
            will_reply_something = True
        
        elif (is_this_my_string(message, ["who are you?", "who are you"])):
            post_text = "Hum! You're curious! I'm a bot that wants to help you. Do you know Siri? Waaaay better."
            will_reply_something = True
        
        elif (is_this_my_string(message, ["how can you help me?", "how can you help me", "help", "menu"])):
            post_text = "Here's what you can currently ask me: 'show me the money', 'show me more money', 'who am i?', 'who are you', 'which rooms'"
            will_reply_something = True
        
        elif (is_this_my_string(message, ["who am i?", "who am i"])):
            personDetail = spark_api.getPersonDetails(person_id)
            #print (json.dumps(personDetail))
            personName = personDetail["displayName"]
            
            personCreatedDate = personDetail["created"]
            creationDate = datetime.datetime.strptime(personCreatedDate, "%Y-%m-%dT%H:%M:%S.%fZ") 
            creationDateFormatted = creationDate.strftime("%B %d, %Y")
            delta = datetime.datetime.now() - creationDate
            delta = (str(delta)).split()
            delta = delta[0] + " " + delta[1]
            
            post_files = personDetail["avatar"]
            post_text = "Looking Good, {}!!".format(personName)
            post_text = post_text + "\nYour email is {}".format(person_email)
            post_text = post_text + "\nYour profile was created on {} ({} ago)".format(creationDateFormatted, delta)
            post_text = post_text + "\nYour ID is <{}>".format(person_id)
            
            will_reply_something = True
        
        elif (is_this_my_string(message, ["which rooms", "which rooms?"])):
            receivedJson = spark_api.getRooms()
            #print (json.dumps(receivedJson)) #in case you want to print the JSON
            
            listOfRooms = [] 
            for room in receivedJson['items']:
                if (room['type'] == "group"):
                    listOfRooms.append(room['title'])
            
            post_text = "I am part of {} conversations. Here's the list:".format(len(listOfRooms))
            #post_text = ";\n".join(listOfRooms) #would convert the list to string 
            
            #putting in a numbered way... 
            i = 1
            for room in listOfRooms:
                post_text = "{}\n{}) {}".format(post_text, str(i), room.encode('utf-8'))
                i = i + 1        
            
            will_reply_something = True
        
        #Now you can create your own app!
        elif (is_this_my_string(message, ["YOUR STRING"])):
            post_text = "Be creative and start playing with the API"
            #remember to set this flag to True, so that the program knows that it has to send something back to Spark
            will_reply_something = True
        
        #Now that you have treated the message. It's time to send something back.
        if (will_reply_something):
            write_to_spark(post_roomId, post_toPersonId, post_toPersonEmail, post_text, post_markdown, post_files)
            output = post_text
        else:
            output = "Success"
    
            
    except Exception as e:
        traceback.print_exc()   
        output = str(e)
    
    except:
        traceback.print_exc()   
        output = "Error occurred. Please try again later."
    
    #The return of the message will be sent via HTTP (not to Spark, but to the client who requested it)
    return output
    
def parse_user_input(request):
    """Helper function to parse the information received by spark."""
    
    http_method = None
    
    if (request.method == "GET"):
        http_method = "GET"
        message = request.args["message"]
        message_id = "FAKE"
        person_id = "FAKE"
        person_email = "FAKE"
        room_id = "FAKE"
        
    elif (request.method == "POST"):
        http_method = "POST"
    
        # Get the json data from HTTP request. This is what was written on the Spark room, which you are monitoring.
        requestJson  = request.json
        #print (json.dumps(requestJson))
        
        # parse the message id, person id, person email, and room id
        message_id = requestJson["data"]["id"]
        person_id = requestJson["data"]["personId"]
        person_email = requestJson["data"]["personEmail"]
        room_id = requestJson["data"]["roomId"]
        
        #At first, Spark does not give the message itself, but it gives the ID of the message. We need to ask for the content of the message
        message = read_from_spark(message_id)   
        
    else:
        output = "Error parsing user input on {} method".format(http_method)
        raise Exception(output)
    
    output = {"message" : message, "message_id" : message_id, "person_id" : person_id, "person_email" : person_email, "room_id" : room_id}
    return output

def read_from_spark(message_id):
    try:
        message = spark_api.getMessage(message_id)
    except:
        config = configparser.ConfigParser()
        config.read("config.ini")
        
        token = config.get('spark', 'token')
        
        if (token == "GET-YOUR-TOKEN"):
            output = "Please change the content of the config.ini file with your Spark token. Visit https://developer.ciscospark.com/getting-started.html for a tutorial"
            
        else:
            output  = "Unknown error while trying to READ from Spark." 
        raise Exception(output)

    return message 

def write_to_spark (room_id, to_person_id, to_person_email, text, markdown, files):
    try:
        if (room_id != "FAKE"):
            spark_api.postMessage(room_id, to_person_id, to_person_email, text, markdown, files)
    except:
        raise Exception("Error while trying to WRITE to Spark.")
    
def is_this_my_string (string, accepted_strings):
    """Helper function to compare an input with several options"""
    return (string.lower() in accepted_strings)

if __name__ == '__main__':
    app.run()