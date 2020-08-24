from flask import Flask
from flask import request
import random
#from flask import render_template

app = Flask(__name__)

@app.route('/')
def homepage():
    website = '''
<!DOCTYPE html>
<html>
<body>
    <h1>Demo of simple newsvendor model</h1>
    <ul>
        <li><a href="/playNewsvendor">click to play</a></li>
    </ul>
</body>
</html>'''
    return website

@app.route('/playNewsvendor')
def my_form():
    website = '''
<!DOCTYPE html>
<html>
<body>
    <h1>Newsvendor game</h1>
    <h2>(demand is uniformly distributed between 0 and 100)</h2>
    <h3>(price is $4, cost is $1)</h3>
    <h4>Enter your order quantity</h4>
    <form action="playNewsvendor" method="POST">
        <input type="text" name="InventoryDecision">
        <input type="submit" value="Check profit">
    </form>
</body>
</html>'''
    return website

@app.route('/playNewsvendor', methods=['POST'])
def my_form_post():
    Inventory = request.form['InventoryDecision']
    try:
        Inventory = float(Inventory)

        Profit = 4 * min(random.randint(0,100),Inventory) - 1 * Inventory
        return "You earned a profit of $" + str(Profit)
    except:
        return "That's not a number!"



if __name__ == '__main__':
    app.run()