#!/usr/bin/env python3
"""
import_transaction_data.py

Import transaction data from Excel file into the database for existing clients.
This will map CLI_001-CLI_010 transaction data to actual client IDs from the database.
"""

import pandas as pd
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def connect_to_database():
    """Connect to the Elite PostgreSQL database"""
    try:
        connection = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "elite_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "")
        )
        return connection
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def import_transaction_data():
    """Import transaction data from Excel to database"""
    print("🔄 Importing transaction data from Excel to database...")
    print("=" * 60)
    
    # Load transaction data
    df = pd.read_excel('data/transaction_history.xlsx')
    print(f"📊 Loaded {len(df)} transactions from Excel")
    
    # Connect to database
    connection = connect_to_database()
    if not connection:
        return
    
    cursor = connection.cursor()
    
    # Get first 10 clients from our list to map to CLI_001-CLI_010
    cursor.execute("SELECT client_id FROM core.client_context ORDER BY client_id LIMIT 10")
    db_clients = [row[0] for row in cursor.fetchall()]
    
    print(f"📋 Mapping transaction data to clients: {db_clients}")
    
    # Create mapping: CLI_001 -> first client, CLI_002 -> second client, etc.
    client_mapping = {}
    for i, tx_client in enumerate(['CLI_001', 'CLI_002', 'CLI_003', 'CLI_004', 'CLI_005', 
                                  'CLI_006', 'CLI_007', 'CLI_008', 'CLI_009', 'CLI_010']):
        if i < len(db_clients):
            client_mapping[tx_client] = db_clients[i]
    
    print(f"🗺️  Client mapping: {client_mapping}")
    
    # Import transactions
    imported_count = 0
    for _, row in df.iterrows():
        try:
            # Map client ID
            original_client = row['Client_ID']
            mapped_client = client_mapping.get(original_client)
            
            if not mapped_client:
                print(f"⚠️  Skipping transaction for unmapped client: {original_client}")
                continue
            
            # Insert transaction
            insert_query = """
            INSERT INTO core.client_transaction 
            (transaction_id, client_id, security_id, name, transaction_type, 
             date, tran_time, transaction_amount, currency, booking_geography, 
             last_import, time_key, load_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (transaction_id) DO NOTHING
            """
            
            cursor.execute(insert_query, (
                row['Transaction_ID'],
                mapped_client,  # Use mapped client ID
                None,  # security_id
                row['Description'],
                row['Type'],
                row['Date'],
                row['Date'],  # tran_time
                row['Amount'],
                'AED',  # currency (assuming AED)
                row['Location'],
                'now()',  # last_import
                row['Date'],  # time_key
                'now()'  # load_date
            ))
            
            imported_count += 1
            
        except Exception as e:
            print(f"❌ Error importing transaction {row['Transaction_ID']}: {e}")
    
    connection.commit()
    connection.close()
    
    print(f"✅ Successfully imported {imported_count} transactions")
    print(f"🎯 Clients now with transaction data: {list(client_mapping.values())}")

if __name__ == "__main__":
    import_transaction_data()
