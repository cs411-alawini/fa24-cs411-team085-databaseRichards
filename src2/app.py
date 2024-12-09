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


@app.route('/home/<username>/add_bet', methods=['GET', 'POST'])
def add_bet(username):
    if request.method == 'POST':
        # Handle adding the bet
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            
            # Retrieve form data
            new_bet = request.form
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
                (SELECT GameID 
                    FROM Games
                    WHERE HomeTeamID = (SELECT TeamID FROM Teams WHERE TeamName = %s)
                    AND AwayTeamID = (SELECT TeamID FROM Teams WHERE TeamName = %s)
                    AND GameDate = %s
                    LIMIT 1) AS GameID,
                (SELECT BetTypeID FROM BetTypes WHERE BetTypeName = %s) AS BetTypeID,
                %s AS Amount,
                %s AS Status
            WHERE 
                (SELECT UserID FROM UserInfo WHERE Username = %s) IS NOT NULL
                AND (SELECT TeamID FROM Teams WHERE TeamName = %s) IS NOT NULL
                AND (SELECT TeamID FROM Teams WHERE TeamName = %s) IS NOT NULL
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
            return jsonify({"message": "Bet added successfully"}), 201

        except mysql.connector.Error as err:
            return jsonify({"message": "Error adding bet", "error": str(err)}), 500
        finally:
            if conn:
                conn.close()
    
    # Render the add bet form for GET requests
    return render_template('add_bet.html', username=username)

@app.route('/home/<username>/edit_bet/<hometeam>/<awayteam>/<date>/<type>', methods=['GET', 'POST'])
def edit_bet(username, hometeam, awayteam, date, type):
    if request.method == 'POST':
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            form_data = request.form
            username = form_data['username']
            home_team = form_data['hometeam']
            away_team = form_data['awayteam']
            game_date = form_data['date']
            bet_amount = form_data['bet_amount']
            bet_status = form_data['status']
            bet_type = form_data['bet_type']

            query = '''

            UPDATE UserBets
            SET Status = %s
            WHERE UserID = (SELECT UserID FROM UserInfo WHERE Username = %s)
            AND GameID = (SELECT GameID 
                          FROM Games
                          WHERE HomeTeamID = (SELECT TeamID FROM Teams WHERE TeamName = %s)
                          AND AwayTeamID = (SELECT TeamID FROM Teams WHERE TeamName = %s)
                          AND GameDate = %s
                          LIMIT 1)
            AND BetTypeID = (SELECT BetTypeID FROM BetTypes WHERE BetTypeName = %s);

            SELECT UserID, GameID, BetTypeID, Amount, Status
            FROM UserBets
            WHERE UserID = (SELECT UserID FROM UserInfo WHERE Username = %s)
            AND Status = 'Loss'

            UNION

            SELECT UserID, GameID, BetTypeID, Amount, Status
            FROM UserBets
            WHERE UserID = (SELECT UserID FROM UserInfo WHERE Username = %s)
            AND Amount > (
                SELECT AVG(TotalAmount)
                FROM (
                    SELECT SUM(Amount) AS TotalAmount
                    FROM UserBets
                    WHERE UserID = (SELECT UserID FROM UserInfo WHERE Username = %s)
                    GROUP BY BetTypeID
                ) AS UserTotals
            );

            '''
            cursor.execute(query, (
                bet_status,
                username,
                home_team,
                away_team,
                game_date,
                bet_type,
                username,
                username,
                username
            ) , multi=True)

            conn.commit()
            return jsonify({"message": "Bet updated and query executed successfully"}), 200

        except mysql.connector.Error as err:
            return jsonify({"message": "Error updating bet", "error": str(err)}), 500
        finally:
            if conn:
                conn.close()

    bet = {
        'username': username,
        'hometeam': hometeam,
        'awayteam': awayteam,
        'date': date,
        'type': type,
    }
    return render_template('edit_bet.html', username=username, bet=bet)


# Delete a user bet
@app.route('/delete_bet/<int:bet_id>', methods=['DELETE'])
def delete_bet(bet_id):
    # Add logic to delete the bet from the database
    return jsonify({"message": "Bet deleted successfully", "bet_id": bet_id}), 200


@app.route('/query_historical', methods=['GET'])
def query_historical():
    home_team = request.args.get('home_team')
    away_team = request.args.get('away_team')
    game_date = request.args.get('game_date')

    # Ensure at least one of the parameters is provided
    if not home_team and not away_team and not game_date:
        return jsonify({"error": "At least one parameter (home_team, away_team, or game_date) is required"}), 400

    try:
        connection = mysql.connector.connect(**db_config)
        with connection.cursor(dictionary=True) as cursor:
            # Base query
            query = """
                SELECT 
                    g.GameID,
                    g.GameDate,
                    ht.TeamName AS HomeTeamName,
                    at.TeamName AS AwayTeamName,
                    g.WinTeamID,
                    g.LoseTeamID,
                    g.WinTeamScore,
                    g.LoseTeamScore
                FROM Games g
                JOIN Teams ht ON g.HomeTeamID = ht.TeamID
                JOIN Teams at ON g.AwayTeamID = at.TeamID
                WHERE 1 = 1
            """
            params = []

            # Add conditions dynamically
            if home_team:
                cursor.execute("SELECT TeamID FROM Teams WHERE TeamName = %s", (home_team,))
                home_team_id = cursor.fetchone()
                if not home_team_id:
                    return jsonify({"error": f"Home team '{home_team}' not found"}), 404
                query += " AND g.HomeTeamID = %s"
                params.append(home_team_id['TeamID'])

            if away_team:
                cursor.execute("SELECT TeamID FROM Teams WHERE TeamName = %s", (away_team,))
                away_team_id = cursor.fetchone()
                if not away_team_id:
                    return jsonify({"error": f"Away team '{away_team}' not found"}), 404
                query += " AND g.AwayTeamID = %s"
                params.append(away_team_id['TeamID'])

            if game_date:
                query += " AND g.GameDate = %s"
                params.append(game_date)

            # Execute the query with the dynamically added conditions
            cursor.execute(query, params)
            games = cursor.fetchall()


            # Return found games
            return jsonify({"games": games}), 200

    except mysql.connector.Error as err:
        # Handle database errors
        return jsonify({"error": f"Database error: {err}"}), 500

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500

    finally:
        # Ensure the database connection is closed
        if connection.is_connected():
            connection.close()


@app.route('/top5_average_points', methods=['GET'])
def top5_average_points():
    query = """ CALL GetTop5AveragePoints(); """
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        results = cursor.fetchall()
        return jsonify(results), 200
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/GetTopTeamsByWinPercentage', methods=['GET'])
def GetTopTeamsByWinPercentage():
    query = """ CALL GetTopTeamsByWinPercentage();"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        results = cursor.fetchall()
        return jsonify(results), 200
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()



if __name__ == '__main__':
    app.run(debug=True)
