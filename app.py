from slackclient import SlackClient
from flask import Flask, request, make_response, Response
import os, threading, time
from db import DB
from datetime import date, datetime

SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', '#foo')
ONCALL_WEEK = os.environ.get('ONCALL_WEEK', 3) # TODO probs can change this to an env var
FRIDAY = 4

slack_client = SlackClient(SLACK_BOT_TOKEN)
db = DB()
app = Flask(__name__)

def post_to_slack(channelMsgText):
  res = slack_client.api_call("chat.postMessage",
                              channel=SLACK_CHANNEL,
                              text=channelMsgText)

def get_all_oncall_person():
  res = []
  rec = db.fetch_all_data()
  for r in rec:
    res.append(r['name'])
  return ", ".join(res)

def get_oncall_based_on_day(day):
  if day > FRIDAY or day < 0 or not get_oncall_status():
    return None
  elif day == FRIDAY:
    day = get_wildcard_oncall()
  rec = db.fetch_data("order", day % len(db.fetch_all_data()))
  return rec[0]

def get_current_oncall():
  day = date.today().weekday()
  rec = get_oncall_based_on_day(day)
  return rec["name"] if rec else None

def get_next_oncall():
  day = date.today().weekday() + 1
  rec = get_oncall_based_on_day(day)
  return rec["name"] if rec else None

def get_previous_oncall():
  day = date.today().weekday() - 1
  rec = get_oncall_based_on_day(day)
  return rec["name"] if rec else None

def get_wildcard_oncall():
  previously = db.fetch_metadata("name", "last_oncall_person")[0]["value"]
  newly = previously + 1
  return newly

def get_last_oncall_date():
  rec = db.fetch_metadata('name', 'last_oncall_date')
  return datetime.strptime(rec[0]['value'], '%Y/%m/%d').date() if rec else None

def get_oncall_status():
  rec = db.fetch_metadata('name', 'is_oncall_week')
  return rec[0]['value'] if rec else None

def get_current_oncall_person():
  rec = db.fetch_metadata('name', 'curr_oncall_person')
  return rec[0]['value'] if rec else None

def update_last_oncall_date(new_date):
  return db.update_metadata('name', 'last_oncall_date', {'value': new_date.strftime("%Y/%m/%d")})

def update_oncall_status(new_status):
  return db.update_metadata('name', 'is_oncall_week', {'value': new_status})

def update_last_oncall_person():
  return db.update_metadata("name", "last_oncall_person", {"value": get_wildcard_oncall() % len(db.fetch_all_data())})

def update_current_oncall_person(person):
  return db.update_metadata("name", "curr_oncall_person", {"value": person})

# def get_new_oncall_person_name(raw_text):
#   """
#   E.g. of raw text: "@Alfred Change current oncall to Evan"
#   Output should be "Evan"
#   """
#   words = raw_text.split()
#   return words[-1]

# def manually_update_oncall_person(name):
#   curr_oncall = get_current_oncall()
#   if not db.update_data('name', name, {'is_on_call': 1}):
#     return False
#   return db.update_data('name', curr_oncall, {'is_on_call': 0})

def is_oncall_week():
  today = date.today()
  day = today.weekday()
  if day > FRIDAY:
    return False

  last_oncall_date = get_last_oncall_date()
  diff_in_weeks = (today - last_oncall_date).days//7
  print("{}, {}, {}, {}".format(today, last_oncall_date, diff_in_weeks, day))
  if diff_in_weeks == 0:
    return True
  elif diff_in_weeks == 1:
    update_oncall_status(0)
    update_last_oncall_person()
    update_current_oncall_person("")
    return False
  elif diff_in_weeks == ONCALL_WEEK:
    update_last_oncall_date(today)
    update_oncall_status(1)
    return True
  return False

def check_oncall_schedule():
  if not is_oncall_week():
    print("!!!! IS NOT ONCALL WEEK")
    return None
  curr_oncall = get_current_oncall()
  return curr_oncall

def check_next_oncall_date():
  if get_oncall_status():
    return ONCALL_WEEK
  else:
    today = date.today()
    last_oncall_date = get_last_oncall_date()
    diff_in_weeks = (today - last_oncall_date).days//7
    return ONCALL_WEEK - diff_in_weeks

def handle_event(type, text):
  if not type == "app_mention":
    return
  channelMsgText = "Apologies, I did not quite catch that. Could you try again?"
  text_in_lowercase = text.lower()
  if "when are we next on support" in text_in_lowercase:
    channelMsgText = "My calendar says that the next support week is in {} week(s).".format(check_next_oncall_date())
  elif "who is on the rota" in text_in_lowercase:
    res = get_all_oncall_person()
    channelMsgText = "Masters {} are currently on the rota.".format(res) if res else "I'm afraid that there isn't anyone on the rota at the moment."
  elif "who is currently on support" in text_in_lowercase:
    res = get_current_oncall()
    channelMsgText = "Master {} is currently on support.".format(res) if res else "I'm afraid that there isn't anyone currently on support."
  elif "who is next on support" in text_in_lowercase:
    res = get_next_oncall()
    channelMsgText = "Master {} is next on on support".format(res) if res else "I'm afraid that there isn't anyone next on support."
  elif "who was previously on support" in text_in_lowercase:
    res = get_previous_oncall()
    channelMsgText = "Master {} was previously on support".format(res) if res else "I'm afraid that there wasn't anyone previously on support."
  # elif "change current oncall to" in text_in_lowercase:
  #   name = get_new_oncall_person_name(text)
  #   if manually_update_oncall_person(name):
  #     channelMsgText = "{} is now OnCall!".format(name)
  #   else:
  #     channelMsgText = "Sorry, I'm unable to change the current OnCall person to {}.".format(name)
  post_to_slack(channelMsgText)

@app.route("/slack", methods=["POST"])
def command():
  data = request.get_json()
  response = ""
  if 'challenge' in data:
    response = data.get('challenge')
  elif 'event' in data:
    handle_event(data['event']['type'], data['event']['text'])
  return make_response(response, 200)

@app.route('/')
def index():
  return ""

def worker():
  while True:
    prev = get_current_oncall_person()
    curr = check_oncall_schedule()
    print("!!!! P:{} vs. C:{}".format(prev, curr))
    if (curr is not None) and curr != prev:
      post_to_slack("Greetings, Master {} will be on support today.".format(curr))
      update_current_oncall_person(curr)
    time.sleep(3600)

def init():
  thread = threading.Thread(target=worker, args=())
  thread.daemon = True
  thread.start()
  return app

if __name__ == "__main__":
  thread = threading.Thread(target=worker, args=())
  thread.daemon = True
  thread.start()
  app.debug = False
  app.run(threaded=True, port=5000)