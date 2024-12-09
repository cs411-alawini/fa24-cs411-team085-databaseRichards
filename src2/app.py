from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import mysql.connector
import random


app = Flask(__name__)
app.secret_key = "your_secret_key"


db_config = {
    'user': 'root',
    'password': '',
    'host': '34.136.188.227',
    'database': 'SportsBettingDB'
}


mock_historical_data = [
    {"team": "Team A", "year": 2023, "odds": "2.5", "outcome": "Win"},
    {"team": "Team B", "year": 2023, "odds": "1.8", "outcome": "Loss"}
]

mock_user_bets = [
    {"id": 1, "team": "Team A", "bet_amount": 100, "odds": "2.5", "date": "2024-12-01"},
    {"id": 2, "team": "Team B", "bet_amount": 50, "odds": "1.8", "date": "2024-12-02"}
]

@app.route('/')
def landing():
    return render_template('login.html')

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor(dictionary=True)

            query = "SELECT * FROM UserInfo WHERE Username = %s AND Password = %s"
            cursor.execute(query, (username, password))
            user = cursor.fetchone()

            if user:
                print(f"Welcome back, {user['Username']}!")
                flash(f"Welcome back, {user['Username']}!", "success")
                return redirect(url_for('home', username=username))

            else:
                flash("Invalid username or password.", "danger")
        
        except mysql.connector.Error as err:
            flash(f"Error: {err}", "danger")
        
        finally:
            cursor.close()
            conn.close()
            
    return render_template('login.html')

# Register Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        userId = random.randint(3000, 9999)

        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            query = "INSERT INTO UserInfo (UserID, Username, Email, Password) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (userId, username, email, password))
            conn.commit()

            flash("User registered successfully!", "success")
            return redirect(url_for('home', username=username))

        except mysql.connector.Error as err:
            flash(f"Error: {err}", "danger")

        finally:
            cursor.close()
            conn.close()

    return render_template('login.html')

def retreive_user_bets(username):    
    formatted_bets = []
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        print(username)
        
        query = "SELECT UserID FROM UserInfo WHERE Username = %s"
        cursor.execute(query, [username])
        user_id = cursor.fetchall()[0]['UserID']
        
        query = '''
            SELECT 
                ub.UserID,
                ub.Amount,
                ub.Status,
                bt.BetTypeName,
                g.GameID,
                g.GameDate,
                ht.TeamName AS HomeTeamName,
                at.TeamName AS AwayTeamName
            FROM UserBets ub
            JOIN Games g ON ub.GameID = g.GameID
            JOIN Teams ht ON g.HomeTeamID = ht.TeamID
            JOIN Teams at ON g.AwayTeamID = at.TeamID
            JOIN BetTypes bt ON ub.BetTypeID = bt.BetTypeID
            WHERE ub.UserID = %s;
        '''
        
        cursor.execute(query, [user_id])
        user_bets = cursor.fetchall()
        
        for bet in user_bets:
            game_id = bet['GameID']
            bet_amount = bet['Amount']
            bet_type = bet['BetTypeName']
            hometeam = bet['HomeTeamName']
            awayteam = bet['AwayTeamName']
            game_date = bet['GameDate']
            status = bet['Status']

            result = {
                "hometeam": hometeam,
                "awayteam": awayteam,
                "date": game_date.strftime("%Y-%m-%d"),
                "bet_amount": float(bet_amount),
                "type": bet_type,
                "status": status
            }

            formatted_bets.append(result)
        
        return formatted_bets
    
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None
    finally:
        if conn:
            conn.close()


# Home Page
@app.route('/home/<username>')
def home(username):
    formatted_bets = retreive_user_bets(username)
    print(formatted_bets)
    return render_template('home.html', username=username, user_bets=formatted_bets, historical_data=mock_historical_data)


@app.route('/add_bet', methods=['GET', 'POST'])
def add_bet(username):
    if request.method == 'POST':
        print("TEST")
        # Handle adding the bet as in your original code
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            
            new_bet = request.json
            username = new_bet['username']
            home_team = new_bet['hometeam']
            away_team = new_bet['awayteam']
            game_date = new_bet['date']
            bet_amount = new_bet['bet_amount']
            bet_type = new_bet['bet_type']
            status = new_bet['status']
            
            query = '''
            INSERT INTO UserBets (UserID, GameID, BetTypeID, Amount, Status)
            SELECT 
                (SELECT UserID FROM UserInfo WHERE Username = %s) AS UserID,
                (SELECT TOP 1 GameID 
                    FROM Games
                    WHERE HomeTeamID = (SELECT TeamID FROM Teams WHERE TeamName = %s)
                    AND AwayTeamID = (SELECT TeamID FROM Teams WHERE TeamName = %s)
                    AND GameDate = %s
                    ORDER BY GameDate ASC) AS GameID,
                (SELECT BetTypeID FROM BetTypes WHERE BetTypeName = %s) AS BetTypeID,
                %s AS Amount,
                %s AS Status
            WHERE 
                (SELECT UserID FROM UserInfo WHERE Username = %s) IS NOT NULL
                AND (SELECT TeamID FROM Teams WHERE TeamName = %s) IS NOT NULL
                AND (SELECT TeamID FROM Teams WHERE TeamName = %s) IS NOT NULL
                AND (SELECT TOP 1 GameID
                        FROM Games
                        WHERE HomeTeamID = (SELECT TeamID FROM Teams WHERE TeamName = %s)
                        AND AwayTeamID = (SELECT TeamID FROM Teams WHERE TeamName = %s)
                        AND GameDate = %s
                        ORDER BY GameDate ASC) IS NOT NULL
                AND (SELECT BetTypeID FROM BetTypes WHERE BetTypeName = %s) IS NOT NULL;
            '''
            cursor.execute(query, (
                username,
                home_team,
                away_team,
                game_date,
                bet_type,
                bet_amount,
                status,
                username,
                home_team,
                away_team,
                home_team,
                away_team,
                game_date,
                bet_type
            ))
            
            conn.commit()
            return jsonify({"message": "Bet added successfully", "bet": new_bet}), 201

        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return jsonify({"message": "Error adding bet", "error": str(err)}), 500
        finally:
            if conn:
                conn.close()
    
    # Handle GET request to show the bet form for the given username
    return render_template('add_bet.html', username=username)


# Edit an existing user bet
@app.route('/edit_bet/<int:bet_id>', methods=['PUT'])
def edit_bet(bet_id):
    updated_bet = request.json
    # Add logic to update the bet in the database
    return jsonify({"message": "Bet updated successfully", "bet": updated_bet}), 200

# Delete a user bet
@app.route('/delete_bet/<int:bet_id>', methods=['DELETE'])
def delete_bet(bet_id):
    # Add logic to delete the bet from the database
    return jsonify({"message": "Bet deleted successfully", "bet_id": bet_id}), 200

# Query historical betting data
@app.route('/query_historical', methods=['GET'])
def query_historical():
    team = request.args.get('team')
    year = request.args.get('year')
    # Add logic to query historical data from the database
    return jsonify({"team": team, "year": year, "data": mock_historical_data}), 200

if __name__ == '__main__':
    app.run(debug=True)
