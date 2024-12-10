from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import mysql.connector
import random
from decimal import Decimal



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
            SELECT GameID
            FROM Games
            WHERE HomeTeamID = (SELECT TeamID FROM Teams WHERE TeamName = %s)
            AND AwayTeamID = (SELECT TeamID FROM Teams WHERE TeamName = %s)
            AND GameDate = %s
            LIMIT 1;
            '''
            cursor.execute(query, (home_team, away_team, game_date))
            game_id = cursor.fetchone()
            game_id = game_id[0] if game_id else None
            print("GameID", game_id)
            query = '''
                START TRANSACTION;    
--              SET TRANSACTION ISOLATION LEVEL REPEATABLE READ COMMITTED;
                INSERT INTO UserBets (UserID, GameID, BetTypeID, Amount, Status)
                SELECT 
                    (SELECT UserID FROM UserInfo WHERE Username = %s) AS UserID,
                    %s AS GameID,
                    (SELECT BetTypeID FROM BetTypes WHERE BetTypeName = %s) AS BetTypeID,
                    %s AS Amount,
                    %s AS Status
                WHERE 
                    (SELECT UserID FROM UserInfo WHERE Username = %s) IS NOT NULL
                    AND (SELECT BetTypeID FROM BetTypes WHERE BetTypeName = %s) IS NOT NULL;
            
                SELECT ho.*, bt.BetTypeName, ht.TeamName AS HomeTeamName, at.TeamName AS AwayTeamName
                FROM HistoricalOdds ho
                JOIN Games g ON ho.GameID = g.GameID
                JOIN Teams ht ON g.HomeTeamID = ht.TeamID
                JOIN Teams at ON g.AwayTeamID = at.TeamID
                JOIN BetTypes bt ON ho.BetTypeID = bt.BetTypeID
                WHERE ht.TeamName = %s AND at.TeamName = %s;

                COMMIT;
            '''
        
            content = []
            for result in cursor.execute(query, (
                    username,
                    game_id,
                    bet_type,
                    bet_amount,
                    status,
                    username,
                    bet_type,
                    home_team,
                    away_team,
            ), multi=True):
                if result.with_rows:
                    content += cursor.fetchall()

            filtered_odds = [record[3] for record in content if record[4] == bet_type]
            average_odds = sum(filtered_odds) / len(filtered_odds) if filtered_odds else None


            conn.commit()
            return render_template('historical_odds.html', odds=filtered_odds, average_odds=average_odds, username=username, home_team=home_team, away_team=away_team, game_date=game_date, bet_type=bet_type)

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

            # query = '''
            #     COMMIT;
            # '''

            # cursor.execute(query, (
            #     # bet_status,
            #     # username,
            #     # home_team,
            #     # away_team,
            #     # game_date,
            #     # bet_type,
            #     # username,
            #     # bet_status,
            #     # username
            # ) , multi=False)

            query2 = '''
                    START TRANSACTION;    
--                  SET TRANSACTION ISOLATION LEVEL READ COMMITTED;

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

                    SELECT 
                    ub.UserID,
                    ub.GameID,
                    ub.BetTypeID,
                    ub.Amount,
                    ub.Status,
                    ht.TeamName AS HomeTeamName,
                    at.TeamName AS AwayTeamName,
                    g.GameDate
                    FROM UserBets ub
                    JOIN Games g ON ub.GameID = g.GameID
                    JOIN Teams ht ON g.HomeTeamID = ht.TeamID
                    JOIN Teams at ON g.AwayTeamID = at.TeamID
                    WHERE ub.UserID = (SELECT UserID FROM UserInfo WHERE Username = %s)
                        AND ub.Status = %s
                        AND ub.Amount <= (
                            SELECT AVG(Amount)
                            FROM UserBets
                    WHERE UserID = (SELECT UserID FROM UserInfo WHERE Username = %s)
                    );
                    COMMIT;
            '''

            content = []

            for result in cursor.execute(query2, (
                bet_status,
                username,
                home_team,
                away_team,
                game_date,
                bet_type,
                username,
                bet_status,
                username
            ), multi=True):
                if result.with_rows:
                    content += result.fetchall()

            # content = cursor.fetchall()

            conn.commit()

            print(content)

            bets = [i[3:] for i in content]

            # print(content[0][3:])


            return render_template('below_average_bets.html', bets=bets)

            # return jsonify({
            #     "content": content,
            #     "message": "Bet updated and query executed successfully"}), 200

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


@app.route('/home/<username>/delete_bet', methods=['POST'])
def delete_bet(username):
    hometeam = request.form['hometeam']
    awayteam = request.form['awayteam']
    date = request.form['date']
    bet_type = request.form['type']
    
    query = """ DELETE FROM UserBets
    WHERE UserID = (SELECT UserID FROM UserInfo WHERE Username = %s) AND GameID = (SELECT GameID FROM Games
    WHERE HomeTeamID = (SELECT TeamID FROM Teams WHERE TeamName = %s) AND AwayTeamID = (SELECT TeamID FROM Teams
    WHERE TeamName = %s) AND GameDate = %s) AND BetTypeID = (SELECT BetTypeID FROM BetTypes WHERE BetTypeName = %s);
    """
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(query, (username, hometeam, awayteam, date, bet_type))
        conn.commit()
        return jsonify({"message": "Bet deleted successfully"}), 200
    except mysql.connector.Error as err:
        return jsonify({"message": "Error deleting bet", "error": str(err)}), 500
    finally:
        if conn:
            conn.close()

def calculate_team_likelihood(games_data):
    if not games_data:
        return {"error": "No games data provided for likelihood calculation"}

    team_stats = {}

    for game in games_data:
        home_team = game['HomeTeamName']
        away_team = game['AwayTeamName']
        win_team = game['WinTeamName']

        lose_team = home_team if win_team == away_team else away_team
        point_diff = game['WinTeamScore'] - game['LoseTeamScore']

        if home_team not in team_stats:
            team_stats[home_team] = {'wins': 0, 'point_diff': 0, 'games': 0}
        if away_team not in team_stats:
            team_stats[away_team] = {'wins': 0, 'point_diff': 0, 'games': 0}

        team_stats[win_team]['games'] += 1
        team_stats[win_team]['wins'] += 1
        team_stats[win_team]['point_diff'] += point_diff

        team_stats[lose_team]['games'] += 1
        team_stats[lose_team]['point_diff'] -= point_diff

    for team, stats in team_stats.items():
        if stats['games'] > 0:
            stats['win_percentage'] = stats['wins'] / stats['games']
            stats['avg_point_diff'] = stats['point_diff'] / stats['games']
        else:
            stats['win_percentage'] = 0.0
            stats['avg_point_diff'] = 0.0

    home_team = games_data[0]['HomeTeamName']
    away_team = games_data[0]['AwayTeamName']

    if home_team not in team_stats or away_team not in team_stats:
        return {"error": "Could not find statistics for one or both of the teams"}

    home_stats = team_stats[home_team]
    away_stats = team_stats[away_team]

    home_raw_score = home_stats['win_percentage'] + (home_stats['avg_point_diff'] * 0.2)
    away_raw_score = away_stats['win_percentage'] + (away_stats['avg_point_diff'] * 0.2)

    home_score = max(home_raw_score, 0)
    away_score = max(away_raw_score, 0)

    total_score = home_score + away_score
    if total_score == 0:
        home_likelihood = 50.0
        away_likelihood = 50.0
    else:
        home_likelihood = (home_score / total_score) * 100
        away_likelihood = (away_score / total_score) * 100

    return {
        'HomeTeam': home_team,
        'AwayTeam': away_team,
        'HomeTeamLikelihood': round(home_likelihood, 2),
        'AwayTeamLikelihood': round(away_likelihood, 2)
    }

@app.route('/query_historical', methods=['GET'])
def query_historical():
    home_team = request.args.get('home_team')
    away_team = request.args.get('away_team')
    game_date = request.args.get('game_date')

    if not home_team and not away_team and not game_date:
        return jsonify({"error": "At least one parameter (home_team, away_team, or game_date) is required"}), 400

    try:
        connection = mysql.connector.connect(**db_config)
        with connection.cursor(dictionary=True) as cursor:
            query = """
                SELECT 
                    g.GameID,
                    g.GameDate,
                    ht.TeamName AS HomeTeamName,
                    at.TeamName AS AwayTeamName,
                    wt.TeamName AS WinTeamName,
                    g.WinTeamScore,
                    g.LoseTeamScore
                FROM Games g
                JOIN Teams ht ON g.HomeTeamID = ht.TeamID
                JOIN Teams at ON g.AwayTeamID = at.TeamID
                JOIN Teams wt ON g.WinTeamID = wt.TeamID
            """
            params = []

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

            cursor.execute(query, params)
            games = cursor.fetchall()
            print(games)
            likelihoods = calculate_team_likelihood(games)
            print(likelihoods)
            return jsonify({"games": games, "likelihoods": likelihoods}), 200

    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if connection.is_connected():
            connection.close()


@app.route('/top5_average_points', methods=['GET'])
def top5_average_points():
    query = "CALL GetTop5AveragePoints();"
    # query = '''
    #     SELECT t.TeamName, AVG(TeamScores.PointsScored) AS AveragePoints
    # FROM (
    #     SELECT HomeTeamID AS TeamID, 
    #            CASE 
    #                WHEN HomeTeamID = WinTeamID THEN WinTeamScore
    #                ELSE LoseTeamScore 
    #            END AS PointsScored
    #     FROM Games
    #     UNION ALL
    #     SELECT AwayTeamID AS TeamID, 
    #            CASE 
    #                WHEN AwayTeamID = WinTeamID THEN WinTeamScore
    #                ELSE LoseTeamScore 
    #            END AS PointsScored
    #     FROM Games
    # ) AS TeamScores
    # JOIN Teams t ON TeamScores.TeamID = t.TeamID                                                                                                                                  
    # GROUP BY t.TeamName
    # ORDER BY AveragePoints DESC
    # LIMIT 5;
    # '''
    try:
        content = []
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True, buffered=True)
        for result in cursor.execute(query, multi=True):
            if result.with_rows:
                content += result.fetchall()
        results = content
        return render_template('topaveragepoints.html', results=results)
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/GetTopTeamsByWinPercentage', methods=['GET'])
def GetTopTeamsByWinPercentage():
    query = "CALL GetTopTeamsByWinPercentage();"

    # query = """
        # WITH TotalGamesPerTeam AS (
        #     SELECT TeamID, COUNT(*) AS TotalGames
        #     FROM (
        #         SELECT HomeTeamID AS TeamID FROM Games
        #         UNION ALL
        #         SELECT AwayTeamID AS TeamID FROM Games
        #     ) AS AllGames
        #     GROUP BY TeamID
        # ),
        # TotalWinsPerTeam AS (
        #     SELECT WinTeamID AS TeamID, COUNT(*) AS Wins
        #     FROM Games
        #     WHERE WinTeamID IS NOT NULL
        #     GROUP BY WinTeamID
        # )
        # SELECT 
        #     Teams.TeamName,
        #     TotalGamesPerTeam.TotalGames,
        #     COALESCE(TotalWinsPerTeam.Wins, 0) AS Wins,
        #     (COALESCE(TotalWinsPerTeam.Wins, 0) * 100.0 / TotalGamesPerTeam.TotalGames) AS WinPercentage
        # FROM Teams
        # JOIN TotalGamesPerTeam ON Teams.TeamID = TotalGamesPerTeam.TeamID
        # LEFT JOIN TotalWinsPerTeam ON Teams.TeamID = TotalWinsPerTeam.TeamID
        # ORDER BY WinPercentage DESC
        # LIMIT 15;
    # """
    try:
        content = []
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True, buffered=True)
        for result in cursor.execute(query, multi=True):
            if result.with_rows:
                content += result.fetchall()
        results = content
        return render_template('topteamswinpercent.html', results=results)
    
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500



if __name__ == '__main__':
    app.run(debug=True)