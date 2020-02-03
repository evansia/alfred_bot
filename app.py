from slackclient import SlackClient
from flask import Flask, request, make_response, Response
import os, threading, time
from db import DB
from datetime import date, datetime

SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', '#foo')
ONCALL_WEEK = 3 # TODO probs can change this to an env var

slack_client = SlackClient(SLACK_BOT_TOKEN)
db = DB()
app = Flask(__name__)

def post_to_slack(channelMsgText):
  slack_client.api_call("chat.postMessage",
                        channel=SLACK_CHANNEL,
                        text=channelMsgText)

def get_oncall_rota():
  res = {}
  rec = db.fetch_all_data()
  rec = sorted(rec, key=lambda  k: k['order'])
  for idx, r in enumerate(rec):
      if r['is_on_call'] == 1:
          res['current'] = r
          res['previous'] = rec[idx-1] if idx > 0 else rec[-1]
          res['next'] = rec[idx+1] if idx < len(rec) - 1 else rec[0]
          break
  return res

def get_all_oncall_person():
  res = []
  rec = db.fetch_all_data()
  for r in rec:
    res.append(r['name'])
  return ", ".join(res)

def get_current_oncall():
  is_oncall_week = get_oncall_status()
  if not is_oncall_week:
    return "No one is OnCall this week."
  rota = get_oncall_rota()
  return rota['current']['name'] if rota else None

def get_next_oncall():
  rota = get_oncall_rota()
  return rota['next']['name'] if rota else None

def get_previous_oncall():
  rota = get_oncall_rota()
  is_oncall_week = get_oncall_status()
  if not is_oncall_week:
    return rota['current']['name'] if rota else None
  return rota['previous']['name'] if rota else None

def get_last_oncall_date():
  rec = db.fetch_metadata('name', 'last_oncall_date')
  return datetime.strptime(rec[0]['value'], '%Y/%m/%d').date() if rec else None

def get_oncall_status():
  rec = db.fetch_metadata('name', 'is_oncall_week')
  return rec[0]['value'] if rec else None

def update_last_oncall_date(new_date):
  return db.update_metadata('name', 'last_oncall_date', {'value': new_date.strftime("%Y/%m/%d")})

def update_oncall_status(new_status):
  return db.update_metadata('name', 'is_oncall_week', {'value': new_status})

def manually_update_oncall_person(name):
  curr_oncall = get_current_oncall()
  if not db.update_data('name', name, {'is_on_call': 1}):
    return False
  return db.update_data('name', curr_oncall, {'is_on_call': 0})

def refresh_oncall_rota():
  curr_oncall = get_current_oncall()
  next_oncall = get_next_oncall()
  db.update_data('name', curr_oncall, {'is_on_call': 0})
  db.update_data('name', next_oncall, {'is_on_call': 1})
  return next_oncall

def get_new_oncall_person_name(raw_text):
  """
  E.g. of raw text: "@Alfred Change current oncall to Evan"
  Output should be "Evan"
  """
  words = raw_text.split()
  return words[-1]

def check_oncall_schedule():
  today = date.today()
  last_oncall_date = get_last_oncall_date()
  diff_in_weeks = (today - last_oncall_date).days//7
  print("{}, {}, {}".format(today, last_oncall_date, diff_in_weeks))
  if diff_in_weeks == 0:
    return
  is_oncall_week = get_oncall_status()
  if (not is_oncall_week) and (diff_in_weeks >= ONCALL_WEEK):
    update_last_oncall_date(today)
    update_oncall_status(1)
    curr_oncall = refresh_oncall_rota()
    post_to_slack("Hello! {} is OnCall this week.".format(curr_oncall))
  elif is_oncall_week and (diff_in_weeks < ONCALL_WEEK):
    update_oncall_status(0)

def handle_event(type, text):
  if not type == "app_mention":
    return
  channelMsgText = "Sorry, I did not understand that."
  text_in_lowercase = text.lower()
  if "who is on the rota" in text_in_lowercase:
    channelMsgText = get_all_oncall_person()
  elif "who is currently oncall" in text_in_lowercase:
    channelMsgText = get_current_oncall()
  elif "who is next oncall" in text_in_lowercase:
    channelMsgText = get_next_oncall()
  elif "who was previously oncall" in text_in_lowercase:
    channelMsgText = get_previous_oncall()
  elif "change current oncall to" in text_in_lowercase:
    name = get_new_oncall_person_name(text)
    if manually_update_oncall_person(name):
      channelMsgText = "{} is now OnCall!".format(name)
    else:
      channelMsgText = "Sorry, I'm unable to change the current OnCall person to {}.".format(name)
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
  print("Worker thread started.")
  while True:
    check_oncall_schedule()
    time.sleep(20) #3600

if __name__ == "__main__":
  thread = threading.Thread(target=worker, args=())
  #thread.daemon = True
  thread.start()
  app.debug = True
  app.run(threaded=True, port=5000)