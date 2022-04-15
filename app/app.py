import os
import pandas as pd
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from datetime import date
from flask import Flask, flash, request, render_template, g, session

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

DB_USER = "jq2334"
DB_PASSWORD = "7666"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/proj1part2"

# Global Variables
login_uid = 'alice01'
attempt_id = 0
claim_id = 0

engine = create_engine(DATABASEURI)

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print ("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass

# Login

@app.route('/')
def home():
  if not session.get('logged_in'):
    return render_template('login.html')
  else:
    cursor1 = g.conn.execute("""
            SELECT
                name
            FROM
                users
            WHERE
                uid = %(username)s
        """, {
            'username': login_uid
        })
    result = cursor1.fetchone()
    cursor1.close()

    if result['name'] is None:
      user_name = ' '
    else:
      user_name = result['name']

    cursor2 = g.conn.execute("SELECT * FROM Topics")
    topic_names = []
    for name in cursor2:
      topic_names.append(name['topic_name']) 
    cursor2.close()

    context = dict(name = user_name, topic = topic_names)
    return render_template('homepage.html', **context)

@app.route('/login', methods=['POST'])
def do_admin_login():
  POST_USERNAME = str(request.form['username'])
  POST_PASSWORD = str(request.form['password'])
  cursor = g.conn.execute("""
            SELECT
                password
            FROM
                users
            WHERE
                uid = %(username)s
        """, {
            'username': POST_USERNAME
        })
  result = cursor.fetchone()
  cursor.close()
  if result is None:
    flash('User does not exist')
    return home()
  elif result['password'] == POST_PASSWORD or result['password'] == None:
    session['logged_in'] = True
    global login_uid
    login_uid = POST_USERNAME
  elif result['password'] != POST_PASSWORD:
    flash('wrong password!')
  return home()

# Profile

@app.route('/user_profile')
def user_profile():
  cursor1 = g.conn.execute("""
          SELECT
              Response.attempt_id, topic_name, SUM(score), time
          FROM
              Response, Attempt
          WHERE
              Response.uid = %(username)s AND Attempt.uid = Response.uid AND Attempt.attempt_id = Response.attempt_id
          GROUP BY
              Response.attempt_id, topic_name, time
          ORDER BY
              Response.attempt_id
        """, {
            'username': login_uid
      })
  attempt_summary_list = []
  for result in cursor1:
    attempt_summary_list.append(result)
  cursor1.close()

  attempt_summary = pd.DataFrame(attempt_summary_list, columns = ['Attempt No.', 'Topic', 'Attempt Score', 'Date Attempt Made']).set_index('Attempt No.')

  cursor2 = g.conn.execute("""
          SELECT
              isFriend.uid2, SUM(score)/ COUNT(DISTINCT attempt_id)
          FROM
              isFriend, Response
          WHERE
              isFriend.uid1 = %(username)s AND Response.uid = isFriend.uid2
          GROUP BY
              isFriend.uid2
        """, {
            'username': login_uid
      })
  friend_scores_list = []
  for result in cursor2:
    friend_scores_list.append(result)
  cursor2.close()

  friend_scores = pd.DataFrame(friend_scores_list, columns = ['Friend', 'Average Attempt Score'])

  cursor3 = g.conn.execute("""
          SELECT
              zipcode
          FROM
              Users
          WHERE
              uid = %(username)s
      """, {        
          'username': login_uid
      })
  login_zipcode = cursor3.fetchone()[0]
  cursor3.close()

  cursor4 = g.conn.execute("""
          SELECT
              Topics.topic_name, SUM(score)/ COUNT(DISTINCT attempt_id)
          FROM
              Users, Response, Claims, Topics
          WHERE
              Users.zipcode = %(zipcode)s AND Users.uid = Response.uid AND Response.claim_id = Claims.claim_id AND Claims.topic_name = Topics.topic_name
          GROUP BY
              Topics.topic_name
        """,  {
            'zipcode': login_zipcode
      })

  location_average_attempt_score_list = []
  for result in cursor4:
    location_average_attempt_score_list.append(result)
  cursor4.close()

  location_average_attempt_score = pd.DataFrame(location_average_attempt_score_list, columns = ['Topic', 'Average Attempt Score'])

  context = dict(uid = login_uid, tables1=[attempt_summary.to_html(classes='data')], titles1=attempt_summary.columns.values, tables2=[friend_scores.to_html(classes='data')], titles2=friend_scores.columns.values,  tables3=[location_average_attempt_score.to_html(classes='data')], titles3=location_average_attempt_score.columns.values)
  
  return render_template("profile.html", **context)

# Starting an Attempt

@app.route('/new_attempt', methods=['GET','POST'])
def new_attempt():

  topic_name = request.form['name']

  cursor2 = g.conn.execute("""
          SELECT
              claim_id, content
          FROM
              Claims
          WHERE
              topic_name = %(topic_name)s
      """, {
          'topic_name': topic_name
      })
  result2 = cursor2.fetchone()
  
  if result2 is None:
    flash('Topic not found, please try again')
    return home()
  else:
    global claim_id
    claim_id = result2['claim_id']
    claim = result2['content']
    cursor2.close()
    context = dict(claim = claim)

    cursor1 = g.conn.execute("""
            SELECT
                MAX(attempt_id) AS last_attempt
            FROM
                Attempt
            WHERE
                uid = %(username)s
        """, {
            'username': login_uid
        })
    result1 = cursor1.fetchone()
    if result1['last_attempt'] is None:
      global attempt_id
      attempt_id = 1
    else:
      attempt_id = result1['last_attempt'] + 1
    today = date.today()
    d = today.strftime("%Y-%m-%d")
    cmd = 'INSERT INTO Attempt VALUES (:attempt_id, :topic_name, :uid, :date)';
    g.conn.execute(text(cmd), attempt_id = attempt_id, topic_name = topic_name, uid = login_uid, date = d);

    return render_template('quiz.html', **context)

# Answering a quiz question

@app.route('/quiz', methods=['POST'])
def quiz():
  cursor1 = g.conn.execute("""
          SELECT
              verdict, explanation, source
          FROM
              Claims
          WHERE
              claim_id = %(claim_id)s
      """, {
          'claim_id': claim_id
      })
  result1 = cursor1.fetchone()
  verdict = int(request.form['verdict'])

  if verdict == result1['verdict']:
    score = 1
  else:
    score = 0

  cursor2 = g.conn.execute("""
          SELECT
              MAX(response_id) AS last_response
          FROM
              Response
          WHERE
              attempt_id = %(attempt_id)s AND claim_id = %(claim_id)s AND uid = %(username)s
      """, {
          'attempt_id': attempt_id, 'claim_id': claim_id, 'username': login_uid
      })
  result2 = cursor2.fetchone()
  if result2['last_response'] is None:
    response_id = 1
  else:
    response_id = result2['last_response'] + 1

  cmd = 'INSERT INTO Response VALUES (:response_id, :uid, :attempt_id, :claim_id, :verdict, :score)';
  g.conn.execute(text(cmd), response_id = response_id, uid = login_uid, attempt_id = attempt_id, claim_id = claim_id, verdict = verdict, score = score);

  context = dict(score = score, explanation = result1['explanation'], source = result1['source'])
  return render_template('answer.html', **context)
    

if __name__ == "__main__":
  import click
  app.secret_key = os.urandom(12)
  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    HOST, PORT = host, port
    print ("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  run()