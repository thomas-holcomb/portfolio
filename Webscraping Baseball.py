#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  3 15:17:57 2025

@author: tholcomb
"""
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
from sqlalchemy import create_engine

def scrape_conferences(conference_url, conference_name):
    # Set up Chrome in headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # New Chrome headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    try:
        # Loop through all websites
        driver.get(conference_url)
        time.sleep(3)  # To not overload sites
        
        # Get rendered HTML and read tables
        html = driver.page_source
        tables = pd.read_html(html)
        
        # Copying data to master tables
        if len(tables) >= 3:
            standings = tables[0].copy()
            batting = tables[1].copy()
            pitching = tables[2].copy()
        
            # Add conference column
            standings["Conference"] = conference_name
            batting["Conference"] = conference_name
            pitching["Conference"] = conference_name
        
            return standings, batting, pitching
        else:
            print(f"⚠️ Warning: {conference_url} returned {len(tables)} tables instead of 3")
            return None, None, None
    except Exception as e:
        print(f"Error scraping {conference_name}: {e}")
        return None, None, None
    
    driver.quit()
    

def scrape_teams(team_url, team_name):
    # Set up Chrome in headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # New Chrome headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try: 
        driver.get(team_url)
        time.sleep(3)  
    
        # Get HTML and read tables
        html = driver.page_source
        driver.quit()
        tables = pd.read_html(html)
        
        # Fill dataframes with necessary tables
        individual_batting = pd.DataFrame(tables[0])
        individual_pitching = pd.DataFrame(tables[1])
        individual_fielding = pd.DataFrame(tables[2])
        game_batting = pd.DataFrame(tables[6])
        game_pitching = pd.DataFrame(tables[7])
        
        return individual_batting, individual_pitching, individual_fielding, game_batting, game_pitching
    except Exception as e:
        print(f"Error scraping {team_name}: {e}")
        return None, None, None, None, None
    
    driver.quit()
    
def clean_conference_stats(batting, pitching, standings):
    # Clean Total Batting
    batting = batting[batting['Tm'] != 'League Totals']
    batting = batting.drop(columns=["Aff", 'BatAge'], errors='ignore')
    batting = batting.rename(columns={
        'R/G': 'runs_per_game', 'G': 'games_played', 'PA': 'plate_appearances', 
        'AB': 'at_bats', 'R': 'runs', 'H': 'hits', '2B': 'doubles', '3B': 'triples', 
        'HR': 'homeruns', 'RBI': 'rbi', 'SB': 'stolen_bases', 'CS': 'caught_stealing', 
        'BB': 'walks', 'SO': 'strikeouts', 'BA': 'avg', 'OBP': 'obp', 'SLG': 'slg', 
        'Tm': 'team', 'OPS': 'ops', 'TB': 'total_bases', 'GDP': 'gdp', 'HBP': 'hbp', 
        'SH': 'sac_bunts', 'SF': 'sac_flies', 'IBB': 'ibb'
    })
    batting = batting.drop(columns="Conference", errors='ignore')
    batting['season_year'] = '2025'

    # Standardize column casing
    batting.columns = [c.strip().lower() for c in batting.columns]

    # Clean Total Pitching
    pitching = pitching[pitching['Tm'] != 'League Totals']
    pitching = pitching.drop(columns=["Aff", 'PAge', 'GS', 'GF'], errors='ignore')
    pitching = pitching.rename(columns={
        'Tm': 'team', 'RA9': 'RA/9', 'H9': 'H/9', 'HR9': 'HR/9', 'BB9': 'BB/9', 'SO9': 'SO/9',
        'R/G': 'runs_per_game', 'W': 'wins', 'L': 'losses', 'ERA': 'era', 'RA/9': 'runs_per_9', 
        'G': 'games_played', 'CG': 'complete_games', 'SHO': 'shutouts', 'SV': 'saves', 
        'IP': 'innings_pitched', 'H': 'hits', 'R': 'runs', 'ER': 'earned_runs', 'HR': 'homeruns', 
        'BB': 'walks', 'IBB': 'ibb', 'HBP': 'hbp', 'BK': 'bk', 'WP': 'wp', 'SO': 'strikeouts',
        'BF': 'bf', 'WHIP': 'whip', 'H/9': 'hits_per_9', 'HR/9': 'homeruns_per_9', 
        'BB/9': 'walks_per_9', 'SO/9': 'strikeouts_per_9', 'SO/W': 'strikeout_to_walk'
    })
    pitching = pitching.drop(columns=["W-L%", "Conference"], errors='ignore')
    pitching['season_year'] = '2025'

    # Standardize column casing
    pitching.columns = [c.strip().lower() for c in pitching.columns]

    # Clean Total Standings
    standings = standings.drop(columns="GB", errors='ignore')
    standings.columns = [c.strip() for c in standings.columns]  # Trim spaces

    # Add Ties if missing
    if 'Ties' not in standings.columns:
        standings['Ties'] = 0
    standings['Ties'] = standings['Ties'].fillna(0).astype(int)

    # Rename to SQL-safe names
    rename_map = {'w': 'wins', 'l': 'losses', 'ties': 'ties', 'tm': 'team'}
    standings = standings.rename(columns=rename_map)
    standings = standings.drop(columns=["W-L%"], errors='ignore')
    standings['season_year'] = '2025'

    # Standardize column casing
    standings.columns = [c.strip().lower() for c in standings.columns]

    return batting, pitching, standings


def clean_team_stats(individual_batting, individual_pitching, individual_fielding):
    #Clean Individual Batting
    individual_batting = individual_batting[~individual_batting['Player'].str.contains('Total|Opponents', na=False)]
    individual_batting = individual_batting.astype({'#': int})
    individual_batting[['SB', 'SBA']] = individual_batting['SB-ATT'].str.split('-', expand=True)
    individual_batting['Player'] = individual_batting['Player'].str.split(r'\d', n=1).str[0].str.rstrip(", ")
    individual_batting[['GP', 'GS']] = individual_batting['GP-GS'].str.split('-', expand=True)
    individual_batting = individual_batting.drop(columns=['Bio Link', 'GP-GS', 'SB-ATT'])
    individual_batting = individual_batting.rename(columns = { 'GP':'games_played','GS':'games_started', 'AB': 'at_bats', 'R': 'runs'
                                 ,'H': 'hits', '2B': 'doubles', '3B': 'triples', 'HR':'homeruns', 'RBI':'rbi', 'SB': 'stolen_bases',
                                 'SBA': 'stolen_base_attempts', 'BB': 'walks', 'SO': 'strikeouts', 'AVG':'avg', 'OB%': 'obp', 'SLG%': 'slg', 
                                 'OPS': 'ops', 'TB': 'total_bases', 'GDP': 'gdp', 'HBP': 'hbp', 'SH': 'sac_bunts', 'SF': 'sac_flies'})
    individual_batting['season_year'] = '2025'
    individual_batting = individual_batting.drop(columns="#")

    #Clean individual pitching
    individual_pitching = individual_pitching[~individual_pitching['Player'].str.contains('Total|Opponents', na=False)]
    individual_pitching = individual_pitching.astype({'#': int})
    individual_pitching['Player'] = individual_pitching['Player'].str.split(r'\d', n=1).str[0].str.rstrip(", ")
    individual_pitching[['APP', 'GS']] = individual_pitching['APP-GS'].str.split('-', expand=True)
    individual_pitching[['W', 'L']] = individual_pitching['W-L'].str.split('-', expand=True)
    individual_pitching = individual_pitching.drop(columns=['Bio Link', 'APP-GS', 'SHO', 'W-L'])
    individual_pitching = individual_pitching.rename(columns={'W': 'wins', 'L':'losses', 'ERA':'era', 'GS': 'games_started', 'APP':'appearances',
                                'CG': 'complete_games', 'SV': 'saves', 'IP':'innings_pitched', 'H': 'hits', 'R':'runs',
                                'ER': 'earned_runs','2B': 'doubles', '3B': 'triples', 'HR':'homeruns', 'BB':'walks', 'HBP':'hbp', 'BK':'bk', 'WP':'wp',
                                'SFA':'sac_flies','SHA':'sac_bunts', 'WHIP': 'whip', 'SO': 'strikeouts','AB':'at_bats','B/AVG':'batting_avg_against' })
    individual_pitching['season_year'] = '2025'
    individual_pitching = individual_pitching.drop(columns="#")

    #Clean individual fielding
    individual_fielding = individual_fielding[~individual_fielding['Player'].str.contains('Total|Opponents', na=False)]
    individual_fielding['Player'] = individual_fielding['Player'].str.split(r'\d', n=1).str[0].str.rstrip(", ")
    individual_fielding = individual_fielding.astype({'#': int})
    individual_fielding = individual_fielding.rename(columns={'CSB':'CS'})
    individual_fielding = individual_fielding.drop(columns='Bio Link')

    individual_fielding = individual_fielding.rename(columns= {'C':'chances', 'PO':'putouts', 'A':'assists', 'E':'errors', 'FLD%':'fielding_pct', 'DP':'double_plays'
                                            ,'SBA':'sba', 'CS':'cs', 'PB':'pb', 'CI': 'ci'})
    individual_fielding['season_year'] = '2025'
    individual_fielding = individual_fielding.drop(columns="#")

    return individual_batting, individual_pitching, individual_fielding
    
    

conference_url = "https://www.baseball-reference.com/register/league.cgi?id=28759e8f" 
conference_name =  "MAC Commonwealth"
team_url = "https://gomustangsports.com/sports/baseball/stats"
team_name = "Stevenson Mustangs"

standings, batting, pitching = scrape_conferences(conference_url, conference_name)
individual_batting, individual_pitching, individual_fielding, game_batting, game_pitching = scrape_teams(team_url, team_name)

standings, batting, pitching = clean_conference_stats(batting, pitching, standings)
individual_batting, individual_pitching, individual_fielding = clean_team_stats(individual_batting, individual_pitching, individual_fielding)


## Have to do sql uploads manually instead of with functions
## Test with all links
    

