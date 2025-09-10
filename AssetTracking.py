#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  9 19:53:26 2025

@author: tholcomb
"""

import pyodbc
import pandas as pd

# Set up the SQL connection
conn = pyodbc.connect('DRIVER={SQL Server};SERVER={server name} ;DATABASE={database name};Trusted_Connection=yes;')

# Query for SerNotDeprec
SerNotDeprec_query = """
    SELECT 
        [Item_ID] AS [Item ID],
        [Item_Name] AS [Item Name],
        [Item_Group] AS [Item Group],
        CAST([SerialNumbers_SerialNumber] AS varchar) AS [Serial Number],
        [SerialNumbers_OriginalCost] AS [Original Purchase Price],
        [SerialNumbers_PurchaseDate] AS [Purchase Date],
        [SerialNumbers_BookValue] AS [Net Book Value],
        [SerialNumbers_OnHand] AS [On Hand Qty],
        [SerialNumbers_OnRent] AS [On Rent Qty],
        SerialNumbers_Location
    FROM 
        [dbname].[ItemBkt_Exp]
    WHERE 
        SerialNumbers_ReadytoDepreciate = 'False'
      and Item_Type = 'serialized' 
      and SerialNumbers_Location NOT IN ('Lost Equipment', 'Discarded Equipment',' Lost Serial Numbers')
      and SerialNumbers_DateSold is null 
      and (SerialNumbers_OnHand = 1 or SerialNumbers_OnRent = 1) 
      and SerialNumbers_PurchaseDate >= '07/01/2019 00:00:00' 
      and SerialNumbers_BookValue is not null and SerialNumbers_BookValue > 0
    ORDER BY 
        SerialNumbers_SerialNumber;
"""

# Query for AutoReorder
AutoReorder_query = """
    SELECT DISTINCT
        [ItemID],
        [ItemName],
        [LastSaleDt],
        [LastPurchDt],
        SUM(IL.[OnHandQty]) AS [OnHandQty],
        [ItemGroup],
        ItemType,
        IL.LocKey
    FROM [dbname].[Item]
    LEFT JOIN dbname.ItemBkt IB ON Item.ItemKey = IB.ItemKey
    LEFT JOIN dbname.ItemLocation IL ON IB.ItemBktKey = IL.ItemBktKey
    WHERE 
        AutoReorder = 'False' 
        AND ItemStatus = 'Active' 
        AND ItemName NOT LIKE 'zz%' 
        AND itemID NOT LIKE 'zz%' 
        AND ExcludeFromPurchaseOrder = 'False'
        AND IL.LocKey = 106 
        AND (LastSaleDt >= DATEADD(YEAR, -1, GETDATE()) AND LastPurchDt >= DATEADD(YEAR, -1, GETDATE()))
        AND IL.OnHandQty <> 0
    GROUP BY ItemID, ItemName, LastSaleDt, LastPurchDt, ItemGroup, ItemType, IL.LocKey
    ORDER BY ItemID;
"""

# Fetch results into pandas DataFrames
SerNotDeprec_df = pd.read_sql(SerNotDeprec_query, conn)
AutoReorder_df = pd.read_sql(AutoReorder_query, conn)

# Close the connection
conn.close()

# Perform unique counts
serial_num_count = SerNotDeprec_df['Serial Number'].nunique()
item_ids_count = AutoReorder_df['ItemID'].nunique()

