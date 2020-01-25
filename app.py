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

@app.route("/slack/test", methods=["POST"])
def command():
  # # send channel a response
  # channelMsg = slack_client.api_call(
  #   "chat.postMessage",
  #   channel="#foo",
  #   text="Tested!")

  return make_response("", 200)

@app.route('/')
def index():
    return "<h1>Welcome!</h1>"

if __name__ == "__main__":
    #app.debug = True
    app.run(threaded=True, port=5000)