from slackclient import SlackClient
from flask import Flask, request, make_response, Response
import os

slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

# updateMsg = slack_client.api_call(
#     "chat.postMessage",
#     channel='#foo',
#     text="Hey!"
#   )

app = Flask(__name__)

@app.route("/slack", methods=["POST"])
def command():
  data = request.get_json()
  print(data)

  response = ""
  if 'challenge' in data:
    response = data.get('challenge')
  elif 'event' in data:
    if data['event']['type'] == "app_mention" and data['event']['text'] == "tell me a story":
      channelMsg = slack_client.api_call(
                      "chat.postMessage",
                      channel="#foo",
                      text="No.")
    else:
      channelMsg = slack_client.api_call(
                      "chat.postMessage",
                      channel="#foo",
                      text="Que?")

  return make_response(response, 200)

@app.route('/')
def index():
    return "<h1>Welcome!</h1>"

if __name__ == "__main__":
    app.debug = True
    app.run(threaded=True, port=5000)