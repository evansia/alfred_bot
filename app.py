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
  info = request.form

  # # get uid of the user
  # im_id = slack_client.api_call(
  #   "im.open",
  #   user=info["user_id"]
  # )["channel"]["id"]

  # # send user a response via DM
  # ownerMsg = slack_client.api_call(
  #   "chat.postMessage",
  #   channel=im_id,
  #   text=commander.getMessage()

  # send channel a response
  channelMsg = slack_client.api_call(
    "chat.postMessage",
    channel="#" + info["channel_name"],
    text="Tested!")

  return make_response("", 200)

@app.route('/')
def index():
    return "<h1>Welcome!</h1>"

if __name__ == "__main__":
    #app.debug = True
    app.run(threaded=True, port=5000)