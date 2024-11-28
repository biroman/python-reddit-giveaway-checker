import asyncpraw
import asyncio
from flask import Flask, render_template
from flask_socketio import SocketIO
import threading

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

async def create_reddit_instance():
    reddit = asyncpraw.Reddit(
        client_id="KMxosgu6dqaN09x6yDuhYA",
        client_secret="gcxn_2uK_m75gDinMgo-cdlb8DRayg",
        username="biroman",
        password="Regulering2regul",
        user_agent="subreddit_watcher (by u/biroman)",
    )
    return reddit

subreddits = ["pathofexile", "pathofexile2"]
keywords = ["giveaway", "giving away", "give away"]

async def watch_subreddit(reddit, subreddit_name):
    subreddit = await reddit.subreddit(subreddit_name)
    print(f"Watching for posts with any of the keywords {keywords} in r/{subreddit_name}...")
    try:
        async for submission in subreddit.stream.submissions(skip_existing=True):
            if any(keyword.lower() in submission.title.lower() for keyword in keywords):
                print(f"\nNew post found in r/{subreddit_name}: {submission.title}")
                socketio.emit("new_post", {
                    "id": submission.id,
                    "title": submission.title,
                    "subreddit": subreddit_name,
                    "url": submission.url,
                    "author": submission.author.name
                })
    except Exception as e:
        print(f"An error occurred in r/{subreddit_name}: {e}")

async def reddit_watcher():
    reddit = await create_reddit_instance()
    tasks = [watch_subreddit(reddit, subreddit) for subreddit in subreddits]
    await asyncio.gather(*tasks)

@socketio.on("post_comment")
def handle_comment(data):
    post_id = data["post_id"]
    comment_text = data["comment"]

    async def post_comment_async():
        reddit = await create_reddit_instance()
        try:
            submission = await reddit.submission(id=post_id)
            await submission.reply(comment_text)
            socketio.emit("comment_success", {"post_id": post_id})
        except Exception as e:
            print(f"Failed to comment on {post_id}: {e}")
            socketio.emit("comment_failure", {"post_id": post_id, "error": str(e)})
        finally:
            await reddit.close()  # Ensure the session is closed

    asyncio.run(post_comment_async())

def start_reddit_watcher():
    asyncio.run(reddit_watcher())

@app.route("/")
def index():
    return render_template("index.html")

threading.Thread(target=start_reddit_watcher, daemon=True).start()

if __name__ == "__main__":
    socketio.run(app, debug=True)
