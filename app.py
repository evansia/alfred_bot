from slackclient import SlackClient
from flask import Flask, request, make_response, Response
import os
from db import DB

slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

db = DB()

app = Flask(__name__)

def get_current_oncall():
  rota = db.fetch_on_call_rota()
  return rota['current']['name']

def get_next_oncall():
  rota = db.fetch_on_call_rota()
  return rota['next']['name']

def get_previous_oncall():
  rota = db.fetch_on_call_rota()
  return rota['previous']['name']

def update_oncall(name):
  if not db.update(name, {'is_on_call': 1}):
    return False
  return db.update(get_current_oncall(), {'is_on_call': 0})

def get_new_oncall_person_name(raw_text):
  """
  E.g. of raw text: "@Alfred Change current oncall to Evan"
  Output should be "Evan"
  """
  words = raw_text.split()
  return words[-1]

@app.route("/slack", methods=["POST"])
def command():
  data = request.get_json()
  print(data)

  response = ""
  if 'challenge' in data:
    response = data.get('challenge')
  elif 'event' in data:
    channelMsgText = "Sorry, I did not understand that."
    if data['event']['type'] == "app_mention":
      text = data['event']['text']
      text_in_lowercase = data['event']['text'].lower()
      if "who is on the rota?" in text_in_lowercase:
        pass
      if "who is currently oncall?" in text_in_lowercase:
        channelMsgText = get_current_oncall()
      elif "who is next oncall" in text_in_lowercase:
        channelMsgText = get_next_oncall()
      elif "who was previously oncall" in text_in_lowercase:
        channelMsgText = get_previous_oncall()
      elif "change current oncall to" in text_in_lowercase:
        name = get_new_oncall_person_name(text)
        if update_oncall(name):
          channelMsgText = "{} is now OnCall!".format(name)
        else:
          channelMsgText = "Sorry, I'm unable to change the current OnCall person to {}.".format(name)
      channelMsg = slack_client.api_call(
                      "chat.postMessage",
                      channel="#foo",
                      text=channelMsgText)

  return make_response(response, 200)

@app.route('/')
def index():
    return ""

if __name__ == "__main__":
    app.debug = True
    app.run(threaded=True, port=5000)