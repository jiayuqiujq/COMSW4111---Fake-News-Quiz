from asyncio.windows_events import NULL
import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from datetime import date
from flask import Flask, flash, request, render_template, g, redirect, Response, session

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

DB_USER = "jq2334"
DB_PASSWORD = "7666"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/proj1part2"

# Global Variables
login_uid = 'alice01'

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
    user_name = result['name']
    cursor1.close()

    cursor2 = g.conn.execute("SELECT * FROM Topics")
    topic_names = []
    for name in cursor2:
      topic_names.append(name['topic_name']) 
    cursor2.close()

    context = dict(name = str(user_name), topic = topic_names)
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

@app.route("/logout")
def logout():
  session['logged_in'] = False
  global login_uid
  login_uid = NULL
  return home()


# Starting an Attempt

@app.route('/quiz', methods=['POST'])
def new_attempt():
  cursor1 = g.conn.execute("""
          SELECT
              MAX(attempt_id) AS last_attempt
          FROM
              Attempt
          GROUP BY
              uid = %(username)s
      """, {
          'username': login_uid
      })
  result = cursor1.fetchone()
  attempt_id= result['last_attempt'] + 1
  topic_name = request.form['name']
  today = date.today()
  d = today.strftime("%Y-%m-%d")
  cmd = 'INSERT INTO Attempt VALUES (:attempt_id), (:topic_name), (:uid), (:date)';
  g.conn.execute(text(cmd), attempt_id = attempt_id, topic_name = topic_name, uid = login_uid, date = d);

  cursor2 = g.conn.execute("""
          SELECT
              content
          FROM
              Claims
          WHERE
              topic_name = %(topic_name)s
      """, {
          'topic_name': topic_name
      })
  all_claims = []
  for claim in cursor2:
    all_claims.append(claim['content']) 
  cursor2.close()

  context = dict(claim = all_claims)

  return render_template('quiz.html', **context)


if __name__ == "__main__":
  app.secret_key = os.urandom(12)
  app.run(debug=True,host='0.0.0.0', port=4000)