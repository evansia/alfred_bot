from slackclient import SlackClient
from flask import Flask, request, make_response, Response
import os, threading, time
from db import DB
from datetime import date, datetime

SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', '#foo')
ONCALL_WEEK = 3 # TODO probs can change this to an env var
FRIDAY = 4

slack_client = SlackClient(SLACK_BOT_TOKEN)
db = DB()
app = Flask(__name__)

def post_to_slack(channelMsgText):
  slack_client.api_call("chat.postMessage",
                        channel=SLACK_CHANNEL,
                        text=channelMsgText)

# def get_oncall_rota():
#   res = {}
#   rec = db.fetch_all_data()
#   rec = sorted(rec, key=lambda  k: k['order'])
#   for idx, r in enumerate(rec):
#       if r['is_on_call'] == 1:
#           res['current'] = r
#           res['previous'] = rec[idx-1] if idx > 0 else rec[-1]
#           res['next'] = rec[idx+1] if idx < len(rec) - 1 else rec[0]
#           break
#   return res

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
    previously = db.fetch_metadata("name", "last_oncall_person")[0]["value"]
    day = previously + 1
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

# def refresh_oncall_rota():
#   curr_oncall = get_current_oncall()
#   next_oncall = get_next_oncall()
#   db.update_data('name', curr_oncall, {'is_on_call': 0})
#   db.update_data('name', next_oncall, {'is_on_call': 1})
#   return next_oncall

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
    return False
  elif diff_in_weeks == ONCALL_WEEK:
    update_last_oncall_date(today)
    update_oncall_status(1)
    return True
  return False

def check_oncall_schedule():
  if not is_oncall_week():
    return
  curr_oncall = get_current_oncall()
  print(curr_oncall)
  return curr_oncall

  # if diff_in_weeks == 0:
  #   return
  # is_oncall_week = get_oncall_status()
  # if (not is_oncall_week) and (diff_in_weeks >= ONCALL_WEEK):
  #   update_last_oncall_date(today)
  #   update_oncall_status(1)
  #   curr_oncall = refresh_oncall_rota()
  #   post_to_slack("Hello! {} is OnCall today.".format(curr_oncall))
  # elif is_oncall_week and (diff_in_weeks < ONCALL_WEEK):
  #   update_oncall_status(0)

def handle_event(type, text):
  if not type == "app_mention":
    return
  channelMsgText = "Sorry, I did not understand that."
  text_in_lowercase = text.lower()
  if "when are we oncall" in text_in_lowercase:
    pass
  elif "who is on the rota" in text_in_lowercase:
    channelMsgText = get_all_oncall_person()
  elif "who is currently oncall" in text_in_lowercase:
    channelMsgText = get_current_oncall() or "No one."
  elif "who is next oncall" in text_in_lowercase:
    channelMsgText = get_next_oncall() or "No one."
  elif "who was previously oncall" in text_in_lowercase:
    channelMsgText = get_previous_oncall() or "No one."
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
  res = None
  while True:
    tmp = check_oncall_schedule()
    if tmp != res:
      post_to_slack("Hello! {} is OnCall today.".format(tmp))
      res = tmp
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