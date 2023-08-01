#Import packages
import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt

def create_parser():
    parser = argparse.ArgumentParser(description='Create a CSV file with the datamodel')
    parser.add_argument('data_path', type=str, help='The path where the raw files are stored.')
    parser.add_argument('match_raw', default='match.csv', type=str, help='The name of the original CSV containing match information.')
    parser.add_argument('group_raw', default='group.csv', type=str, help='The name of the original CSV containing group information.')
    parser.add_argument('data_model', default='model.csv', type=str, help='The name of the CSV file with the model data.')
    parser.add_argument('competitivity_param', default=3, type=int, help='The maximum number of points difference so the match is taken into account.')
    return parser

def set_winning_team_given_scores(score_Team1, score_Team2):
  
    if score_Team1 > score_Team2:
      return 1
    elif score_Team1 < score_Team2:
      return 2
    else:
      return -1

def set_winner(row):

    score_Team1, score_Team2 = row['FullScore'].split("–") #Note that the separation is not a simple hyphen

    win = set_winning_team_given_scores(score_Team1, score_Team2)
    if win > 0: 
        return pd.Series({'Winner': win, 'WinningType': 'NORM'}) #NORMal win

    if row['Penaltis'] == row['Penaltis']: #Taking advantage that nan != nan
        score_Team1, score_Team2 = row['Penaltis'].split("–")
        win = set_winning_team_given_scores(score_Team1, score_Team2)
        if win > 0:
          return pd.Series({'Winner': win, 'WinningType': 'PENA'}) #PENAlty

    elif row['VisitantAdvantage'] == row['VisitantAdvantage']:
        score_Team1, score_Team2 = row['VisitantAdvantage'].split("–")
        win = set_winning_team_given_scores(score_Team1, score_Team2)
        if win > 0: 
          return pd.Series({'Winner': win, 'WinningType': 'GAAT'}) #Goal Advantage as Away Team

def set_final_home_team(row):

    if row['PositionTeam1'] < row['PositionTeam2']:
        return 1
    else:
        return 2

def set_scores(row, column_name):

    score_Team1, score_Team2 = row[column_name].split("–")

    score_Team1 = int(score_Team1)
    score_Team2 = int(score_Team2)

    return score_Team1 - score_Team2

def map_to_data_model(data_path, match_raw, group_raw, data_model, competitivity_param):
    
    competitivity_param = competitivity_param
    
    dtype_groups = {
         'Year': int,
         'Position': int,
         'Club': str,
         'Points': int,
         'Country': str
        }

    dtype_scores = {
         'Year': int,
         'Team1': str,
         'FullScore': str,
         'Penaltis': str,
         'VisitantAdvantage': str,
         'Team2': str,
         'FirstMatch': str,
         'SecondMatch': str,
         'Anomaly': int
        }

    df_groups = pd.read_csv(os.path.join(data_path, group_raw), dtype = dtype_groups)

    df_scores = pd.read_csv(os.path.join(data_path, match_raw), dtype = dtype_scores)

    df_scores = df_scores[df_scores["Anomaly"] == 0]

    df_scores[['Winner', 'WinningType']] = df_scores.apply(set_winner, axis=1)

    df_scores = df_scores.merge(df_groups, left_on=['Year', 'Team1'], right_on=['Year', 'Club'], how='left').drop(['Club'], axis=1)
    df_scores.rename(columns={'Points': 'PointsTeam1',
                          'Position': 'PositionTeam1',
                          'Competition': 'Competition1',
                          'Country': 'CountryTeam1'}, inplace=True)
    
    df_scores = df_scores.merge(df_groups, left_on=['Year', 'Team2'], right_on=['Year', 'Club'], how='left').drop(['Club'], axis=1)
    df_scores.rename(columns={'Points': 'PointsTeam2',
                          'Position': 'PositionTeam2',
                          'Country': 'CountryTeam2'}, inplace=True)
    
    df_scores['PlayedHomeLastGame'] = df_scores.apply(set_final_home_team, axis=1)

    df_scores['ScoreDiffFirstMatch'] = df_scores.apply(set_scores, args=('FirstMatch', ), axis=1)
    df_scores['ScoreDiffSecondMatch'] = df_scores.apply(set_scores, args=('SecondMatch', ), axis=1)
    df_scores['ScoreDiff'] = df_scores['ScoreDiffFirstMatch'] + df_scores['ScoreDiffSecondMatch']

    mask_competitivity = ((abs(df_scores['PointsTeam1'] - df_scores['PointsTeam2']) <= competitivity_param) & (df_scores['Phase'] == "RoundOf16")) | (df_scores['Phase'] != "RoundOf16")

    df_scores = df_scores[mask_competitivity]

    df_scores['WinnerPlayedLastGameAtHome'] = df_scores['Winner'] == df_scores['PlayedHomeLastGame']

    df_scores['PointsDiff'] = df_scores['PointsTeam1'] - df_scores['PointsTeam2']

    df_scores['DecidedPenalty'] = df_scores['WinningType'] == "PENA"
    df_scores['DecidedGoalAwayRule'] = df_scores['WinningType'] == "GAAT"

    df_scores['SameCountry'] = df_scores['CountryTeam1'] == df_scores['CountryTeam2']

    keep = ['Year',
        'Team1',
        'Team2',
        'Winner',
        'WinnerPlayedLastGameAtHome',
        'SameCountry',
        'ScoreDiffFirstMatch',
        'ScoreDiffSecondMatch',
        'ScoreDiff',
        'WinningType',
        'DecidedPenalty',
        'DecidedGoalAwayRule',
        'Phase',
        'Competition'
        ]

    df_scores = df_scores[keep]

    df_scores.to_csv(os.path.join(data_path, data_model), index=False)


if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()

    map_to_data_model(args.data_path, args.match_raw, args.group_raw, args.data_model, args.competitivity_param)
