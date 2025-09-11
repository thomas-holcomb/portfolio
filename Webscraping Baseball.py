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

# Websites to navigate through
links = ["Baseball reference links to loop through"
]
# Set up Chrome in headless mode
chrome_options = Options()
chrome_options.add_argument("--headless=new")  # New Chrome headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# Empty DataFrames to store combined results
standings_df = pd.DataFrame()
batting_df = pd.DataFrame()
pitching_df = pd.DataFrame()

# Loop through all websites
for url, conference in links:
    driver.get(url)
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
        standings["Conference"] = conference
        batting["Conference"] = conference
        pitching["Conference"] = conference

        # Append to master DataFrames
        standings_df = pd.concat([standings_df, standings], ignore_index=True)
        batting_df = pd.concat([batting_df, batting], ignore_index=True)
        pitching_df = pd.concat([pitching_df, pitching], ignore_index=True)
    else:
        print(f"⚠️ Warning: {url} returned {len(tables)} tables instead of 3")
# Close webdriver
driver.quit()

# Empty dataframes for next link
individual_batting_df = pd.DataFrame()
individual_pitching_df = pd.DataFrame()
individual_fielding_df = pd.DataFrame()
game_batting_df = pd.DataFrame()
game_pitching_df = pd.DataFrame()

# Setup driver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
url2 = "Individualteamlink"

driver.get(url2)
time.sleep(3)  

# Get HTML and read tables
html2 = driver.page_source
driver.quit()
tables2 = pd.read_html(html2)

# Fill dataframes with necessary tables
individual_batting_df = pd.concat([individual_batting_df, tables2[0]], ignore_index=True)
individual_pitching_df = pd.concat([individual_pitching_df, tables2[1]], ignore_index=True)
individual_fielding_df = pd.concat([individual_fielding_df, tables2[2]], ignore_index=True)
game_batting_df = pd.concat([game_batting_df, tables2[6]], ignore_index=True)
game_pitching_df = pd.concat([game_pitching_df, tables2[7]], ignore_index=True)

# Clean Total Batting
batting_df = batting_df[batting_df['Tm'] != 'League Totals']
batting_df = batting_df.drop(columns=["Aff", 'BatAge'])
batting_df.rename(columns={'Tm': 'Team'}, inplace=True)

# Clean Total Pitching
pitching_df = pitching_df.drop(columns=["Aff", 'PAge', 'GS', 'GF'])
pitching_df = pitching_df[pitching_df['Tm'] != 'League Totals']
pitching_df.rename(columns={'Tm':'Team', 'RA9':'RA/9', 'H9':'H/9','HR9':'HR/9', 'BB9':'BB/9', 'SO9':'SO/9' }, inplace=True)

# Clean Total Standings
standings_df.fillna({'Ties': 0},inplace=True)
standings_df = standings_df.drop(columns="GB")
standings_df.rename(columns={'Tm': 'Team'}, inplace=True)
standings_df = standings_df.astype({'Ties': int})

# Clean game by game batting
game_batting_df.columns = game_batting_df.columns.str.strip()
game_batting_df['Loc'] = game_batting_df['Loc'].fillna('vs')
game_batting_df[['RS','RA']] = game_batting_df['Score'].str.split('-', expand=True).astype(int)
game_batting_df = game_batting_df.drop(columns='Score')

# Clean game by game pitching
game_pitching_df.columns = game_pitching_df.columns.str.strip()
game_pitching_df['Loc'] = game_pitching_df['Loc'].fillna('vs')
game_pitching_df[['RS','RA']] = game_pitching_df['Score'].str.split('-', expand=True).astype(int)
game_pitching_df = game_pitching_df.drop(columns='Score')

    
# Clean individual batting
individual_batting_df = individual_batting_df[~individual_batting_df['Player'].str.contains('Total|Opponents', na=False)]
individual_batting_df = individual_batting_df.astype({'#': int})
individual_batting_df[['SB', 'SBA']] = individual_batting_df['SB-ATT'].str.split('-', expand=True)
individual_batting_df['Player'] = individual_batting_df['Player'].str.split(r'\d', n=1).str[0].str.rstrip(", ")
individual_batting_df[['GP', 'GS']] = individual_batting_df['GP-GS'].str.split('-', expand=True)
individual_batting_df = individual_batting_df.drop(columns=['Bio Link', 'GP-GS', 'SB-ATT'])

# Clean individual pitching
individual_pitching_df = individual_pitching_df[~individual_pitching_df['Player'].str.contains('Total|Opponents', na=False)]
individual_pitching_df = individual_pitching_df.astype({'#': int})
individual_pitching_df['Player'] = individual_pitching_df['Player'].str.split(r'\d', n=1).str[0].str.rstrip(", ")
individual_pitching_df[['APP', 'GS']] = individual_pitching_df['APP-GS'].str.split('-', expand=True)
individual_pitching_df[['W', 'L']] = individual_pitching_df['W-L'].str.split('-', expand=True)
individual_pitching_df = individual_pitching_df.drop(columns=['Bio Link', 'APP-GS', 'SHO', 'W-L'])

# Clean individual fielding
individual_fielding_df = individual_fielding_df[~individual_fielding_df['Player'].str.contains('Total|Opponents', na=False)]
individual_fielding_df['Player'] = individual_fielding_df['Player'].str.split(r'\d', n=1).str[0].str.rstrip(", ")
individual_fielding_df = individual_fielding_df.astype({'#': int})
individual_fielding_df = individual_fielding_df.rename(columns={'CSB':'CS'})
individual_fielding_df = individual_fielding_df.drop(columns='Bio Link')


# Save results
batting_df.to_csv("totalbatting.csv", index=False)
pitching_df.to_csv("totalpitching.csv", index=False)
standings_df.to_csv("totalstandings.csv", index=False)
individual_batting_df.to_csv("individualbatting.csv", index=False)
individual_pitching_df.to_csv("individualpitching.csv", index=False)
individual_fielding_df.to_csv("individualfielding.csv", index=False)
game_batting_df.to_csv("gamebatting.csv", index=False)
game_pitching_df.to_csv("gamepitching.csv", index=False)


