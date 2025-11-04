#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 24 15:11:54 2025

@author: tholcomb
"""

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

import requests
from bs4 import BeautifulSoup

# ---- Step 1: Get tables from a boxscore URL ----
def get_play_by_play_tables(url):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(url)
    time.sleep(3)  # avoid overloading the site

    html = driver.page_source
    tables = pd.read_html(html)

    driver.quit()
    return tables

# ---- Step 2: Combine half-inning tables ----
def combine_innings(tables):
    play_tables = []
    for t in tables:
        if not isinstance(t, pd.DataFrame):
            continue
        # Check if it has a 'Play Description' column
        if any("Play Description" in str(col) for col in t.columns) and not any("Logo" in str(col) for col in t.columns):
            # Skip empty or duplicate tables
            if t.dropna(how="all").empty:
                break  # Stop once the first empty table appears
            play_tables.append(t)
    # Safety check
    if not play_tables:
        raise ValueError("No play-by-play tables found.")
    # Combine with inning/half tags
    combined = []
    for i, t in enumerate(play_tables, start=1):
        t = t.copy()
        t["Inning"] = (i + 1) // 2
        t["Half"] = "Top" if i % 2 != 0 else "Bottom"
        combined.append(t)
    df = pd.concat(combined, ignore_index=True)
    # Remove exact duplicate rows if the site repeated text blocks
    df = df.drop_duplicates(subset=df.columns, keep="first").reset_index(drop=True)
    return df

def parse_play(desc):
    desc = str(desc).lower()

    # Skip substitutions and pitching changes
    if any(x in desc for x in ["to p for", "pinch hit", "pinch ran", "to 1b for", "to ss for", "to 2b for", "to c for", "to lf for", "to rf for", "to cf for", "to 3b for"]):
        return "Substitution"

    # Basic outcomes
    if "walked" in desc:
        return "Walk"
    if "hit by pitch" in desc:
        return "Hit by Pitch"
    if "singled" in desc:
        return "Single"
    if "doubled" in desc:
        return "Double"
    if "tripled" in desc:
        return "Triple"
    if "homered" in desc:
        return "Home Run"
    if "struck out" in desc:
        return "Strikeout"

    # Outs
    if any(x in desc for x in ["grounded out", "flied out", "lined out", "popped up"]):
        return "Out"

    # Fielding events
    if "fielder's choice" in desc:
        return "Fielder's Choice"
    if "reached on a fielder's choice" in desc:
        return "Fielder's Choice"
    if "reached on a fielding error" in desc or "reached on a throwing error" in desc:
        return "Error"

    # Runner movements
    if "stole" in desc:
        return "Stolen Base"
    if "caught stealing" in desc:
        return "Caught Stealing"

    # Sacrifices
    if "sacrifice fly" in desc or "sac fly" in desc:
        return "Sacrifice Fly"
    if "sac bunt" in desc or "sacrifice bunt" in desc:
        return "Sacrifice Bunt"

    # Pitches/wild
    if "wild pitch" in desc:
        return "Wild Pitch"
    if "passed ball" in desc:
        return "Passed Ball"
    if "balk" in desc:
        return "Balk"
    if "double play" in desc:
        return "Double Play"
    if "triple play" in desc:
        return "Triple Play"


    # Everything else
    return "Other"

def update_state(play, state, desc=None):
    state = state.copy()

    # Base/Out reset logic
    if play == "Substitution":
        return state

    # --- Outs ---
    if play in ["Out", "Strikeout", "Sacrifice Fly", "Sacrifice Bunt"]:
        state["outs"] += 1

    elif play == "Double Play":
        state["outs"] += 2
        # assume lead runner erased if anyone on base
        if any(state["bases"]):
            # remove the lead runner
            for i in range(2, -1, -1):
                if state["bases"][i] == 1:
                    state["bases"][i] = 0
                    break

    elif play == "Triple Play":
        state["outs"] += 3

    # --- Walk / HBP ---
    elif play in ["Walk", "Hit by Pitch"]:
        if all(state["bases"]):
            state["runs"] += 1
        state["bases"] = [1] + state["bases"][:-1]

    # --- Single ---
    elif play == "Single":
        runs_scored = 0
        if state["bases"][2]:
            runs_scored += 1
        state["bases"] = [1, state["bases"][0], state["bases"][1]]
        state["runs"] += runs_scored

    # --- Double ---
    elif play == "Double":
        runs_scored = 0
        # more precise: read description for 'RBI' count
        if desc and "rbi" in desc.lower():
            import re
            rbi_match = re.search(r"(\d+) rbi", desc.lower())
            if rbi_match:
                runs_scored = int(rbi_match.group(1))
        else:
            runs_scored = state["bases"][2] + state["bases"][1]
        state["runs"] += runs_scored
        # shift bases logically: batter to 2nd, runner on 1st to 3rd if empty
        state["bases"] = [0, 1, state["bases"][0]]

    # --- Triple ---
    elif play == "Triple":
        runs_scored = sum(state["bases"])
        state["runs"] += runs_scored
        state["bases"] = [0, 0, 1]

    # --- Home Run ---
    elif play == "Home Run":
        state["runs"] += sum(state["bases"]) + 1
        state["bases"] = [0, 0, 0]

    # --- Fielder's Choice or Error ---
    elif play in ["Error", "Fielder's Choice"]:
        # approximate: runner reaches first, lead runner out if bases occupied
        if any(state["bases"]):
            state["outs"] += 1
            for i in range(2, -1, -1):
                if state["bases"][i] == 1:
                    state["bases"][i] = 0
                    break
        state["bases"] = [1] + state["bases"][:-1]

    # --- Stolen Base ---
    elif play == "Stolen Base":
        # move one runner forward if possible
        for i in range(2, -1, -1):
            if state["bases"][i] == 1:
                if i < 2:
                    state["bases"][i] = 0
                    state["bases"][i+1] = 1
                else:
                    state["bases"][i] = 0
                    state["runs"] += 1
                break

    # --- Caught Stealing ---
    elif play == "Caught Stealing":
        state["outs"] += 1

    # --- Wild Pitch / Passed Ball / Balk ---
    elif play in ["Wild Pitch", "Passed Ball", "Balk"]:
        runs_scored = 0
        if state["bases"][2]:
            runs_scored += 1
        state["bases"] = [0] + state["bases"][:-1]
        state["runs"] += runs_scored

    # --- Inning end reset ---
    if state["outs"] >= 3:
        state = {"outs": 0, "bases": [0, 0, 0], "runs": state["runs"]}

    return state


def process_game(df):
    df["Play Type"] = df["Play Description"].apply(parse_play)
    state = {"outs": 0, "bases": [0,0,0], "runs": 0}
    states = []
    for _, row in df.iterrows():
        play_type = row["Play Type"]
        desc = row["Play Description"]
        state = update_state(play_type, state, desc)
        states.append(state.copy())
    df["Outs"] = [s["outs"] for s in states]
    df["Bases"] = [s["bases"] for s in states]
    df["Runs"] = [s["runs"] for s in states]
    return df


# === STEP 1: Get all box score links for the team ===
def get_boxscore_links(schedule_url):
    """Scrape the schedule page and return all box score URLs."""
    r = requests.get(schedule_url)
    soup = BeautifulSoup(r.text, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True).lower()
        if "box score" in text and "baseball" in href:
            if href.startswith("/"):
                href = "https://auwolves.com" + href
            links.append(href)

    print(f"Found {len(links)} box score links.")
    return links


# === STEP 3: Run it for the team ===
schedule_url = "https://auwolves.com/sports/baseball/schedule"
links = get_boxscore_links(schedule_url)
all_games = []
for link in links:
    try:
        tables = get_play_by_play_tables(link)
        time.sleep(1)
        df = combine_innings(tables)
        df = process_game(df)
        all_games.append(df)
    except Exception as e:
        print(f"❌ Error processing {link}: {e}")    
final_df = pd.concat(all_games)

# Drop irrelevant team columns
drop_cols = [c for c in final_df.columns if c not in ["Play Description", "Inning", "Half", "Play Type", "Outs", "Bases", "Runs"]]
begin_mc = final_df.drop(columns=drop_cols)
# Compute runs per play
begin_mc["Runs_On_Play"] = begin_mc["Runs"].diff().fillna(0).astype(int)
# Reset runs per inning if desired (optional)
begin_mc["Runs_In_Inning"] = begin_mc.groupby(["Inning", "Half"])["Runs_On_Play"].cumsum()


output_csv = "alvernia_season.csv"
begin_mc.to_csv(output_csv, index= False)





