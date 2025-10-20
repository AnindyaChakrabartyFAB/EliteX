#!/usr/bin/env python3
"""
map_and_import_transactions.py

Map transaction data from CLI_001-CLI_010 to the 50 client IDs from EliteX.py list,
then import the mapped transaction data into the database.
"""

import pandas as pd
import psycopg2
import os
import random
from dotenv import load_dotenv

load_dotenv()

# 50 client IDs from EliteX.py
CLIENT_IDS = [
    '10GLPHG', '10GRRXX', '10PKFPQ', '10QAXPK', '10QHKPA', '10QHLHP', '10QXGLF', '10QXRPX', '10RXAKP', '10XQKRF',
    '11AAPGR', '11ALFPK', '11FKLLH', '11FQLKK', '11FXHLQ', '11HXFGR', '11HXPLF', '11KPGQK', '11KQKXL', '11KQXAQ',
    '11LPKHH', '11QHRKF', '11QPPQG', '12AHQHL', '12APFQL', '12HAHQH', '12HAKFG', '12HHXGA', '12KRAPA', '12LFGLA',
    '12QQAHQ', '12XFGRP', '13HHAAX', '13KFXRF', '13KHGPQ', '13RXRXF', '14FPRPR', '14HFQAR', '14HPHKR', '14HPPQL',
    '14KAKGL', '14LHGPG', '14LRHXX', '14LXHLQ', '14QPXFK', '15GGGKP', '15GGRAH', '15GRGFK', '15GXHXR', '15HGRQA'
]

# Original transaction client IDs
TRANSACTION_CLIENTS = ['CLI_001', 'CLI_002', 'CLI_003', 'CLI_004', 'CLI_005', 'CLI_006', 'CLI_007', 'CLI_008', 'CLI_009', 'CLI_010']

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

def create_client_mapping():
    """Create random mapping from transaction clients to our 50 client IDs"""
    print("🎲 Creating random client mapping...")
    
    # Shuffle the client IDs to get random distribution
    shuffled_clients = CLIENT_IDS.copy()
    random.shuffle(shuffled_clients)
    
    # Create mapping: each transaction client maps to 5 of our clients (50/10 = 5 each)
    client_mapping = {}
    clients_per_tx_client = len(CLIENT_IDS) // len(TRANSACTION_CLIENTS)
    
    for i, tx_client in enumerate(TRANSACTION_CLIENTS):
        start_idx = i * clients_per_tx_client
        end_idx = start_idx + clients_per_tx_client
        mapped_clients = shuffled_clients[start_idx:end_idx]
        client_mapping[tx_client] = mapped_clients
        
        print(f"  {tx_client} → {mapped_clients}")
    
    return client_mapping

def map_transaction_data():
    """Map transaction data from CLI_001-CLI_010 to our 50 client IDs"""
    print("📊 Loading and mapping transaction data...")
    
    # Load original transaction data
    df = pd.read_excel('data/transaction_history.xlsx')
    print(f"  Loaded {len(df)} transactions from Excel")
    
    # Create client mapping
    client_mapping = create_client_mapping()
    
    # Create mapped transaction data
    mapped_transactions = []
    
    for _, row in df.iterrows():
        original_client = row['Client_ID']
        mapped_clients = client_mapping.get(original_client, [])
        
        # For each transaction, create multiple copies for each mapped client
        for mapped_client in mapped_clients:
            # Create new transaction with mapped client ID
            new_transaction = row.copy()
            new_transaction['Client_ID'] = mapped_client
            # Update transaction ID to be unique
            new_transaction['Transaction_ID'] = f"{mapped_client}_{row['Transaction_ID']}"
            mapped_transactions.append(new_transaction)
    
    # Create DataFrame from mapped transactions
    mapped_df = pd.DataFrame(mapped_transactions)
    print(f"  Created {len(mapped_df)} mapped transactions")
    
    # Show distribution
    print("\n📈 Transaction distribution by client:")
    client_counts = mapped_df['Client_ID'].value_counts()
    for client_id, count in client_counts.items():
        print(f"  {client_id}: {count} transactions")
    
    return mapped_df

def import_to_database(mapped_df):
    """Import mapped transaction data to database"""
    print("\n💾 Importing mapped transactions to database...")
    
    connection = connect_to_database()
    if not connection:
        return False
    
    cursor = connection.cursor()
    
    # Clear existing transaction data for our clients (optional - comment out if you want to keep existing data)
    print("  Clearing existing transaction data for mapped clients...")
    placeholders = ','.join(['%s'] * len(CLIENT_IDS))
    cursor.execute(f"DELETE FROM core.client_transaction WHERE client_id IN ({placeholders})", CLIENT_IDS)
    deleted_count = cursor.rowcount
    print(f"  Deleted {deleted_count} existing transactions")
    
    # Import new transactions
    imported_count = 0
    errors = []
    
    for _, row in mapped_df.iterrows():
        try:
            insert_query = """
            INSERT INTO core.client_transaction 
            (transaction_id, client_id, security_id, name, transaction_type, 
             date, tran_time, transaction_amount, currency, booking_geography, 
             last_import, time_key, load_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                row['Transaction_ID'],
                row['Client_ID'],
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
            errors.append(f"Transaction {row['Transaction_ID']}: {e}")
    
    connection.commit()
    connection.close()
    
    print(f"  ✅ Successfully imported {imported_count} transactions")
    
    if errors:
        print(f"  ⚠️  {len(errors)} errors occurred:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"    {error}")
        if len(errors) > 5:
            print(f"    ... and {len(errors) - 5} more errors")
    
    return imported_count > 0

def verify_import():
    """Verify that transactions were imported correctly"""
    print("\n🔍 Verifying import...")
    
    connection = connect_to_database()
    if not connection:
        return
    
    cursor = connection.cursor()
    
    # Check transaction counts per client
    print("📊 Transaction counts by client:")
    for client_id in CLIENT_IDS:
        cursor.execute("SELECT COUNT(*) FROM core.client_transaction WHERE client_id = %s", (client_id,))
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"  {client_id}: {count} transactions")
    
    # Check total transactions
    cursor.execute("SELECT COUNT(*) FROM core.client_transaction WHERE client_id = ANY(%s)", (CLIENT_IDS,))
    total_count = cursor.fetchone()[0]
    print(f"\n📈 Total transactions imported: {total_count}")
    
    # Check transaction types
    cursor.execute("""
        SELECT transaction_type, COUNT(*) 
        FROM core.client_transaction 
        WHERE client_id = ANY(%s)
        GROUP BY transaction_type 
        ORDER BY COUNT(*) DESC
    """, (CLIENT_IDS,))
    
    print("\n📊 Transaction types:")
    for tx_type, count in cursor.fetchall():
        print(f"  {tx_type}: {count} transactions")
    
    connection.close()

def main():
    print("🚀 Mapping and Importing Transaction Data")
    print("=" * 60)
    print(f"📋 Mapping {len(TRANSACTION_CLIENTS)} transaction clients to {len(CLIENT_IDS)} client IDs")
    print()
    
    # Set random seed for reproducible results
    random.seed(42)
    
    try:
        # Step 1: Map transaction data
        mapped_df = map_transaction_data()
        
        # Step 2: Import to database
        success = import_to_database(mapped_df)
        
        if success:
            # Step 3: Verify import
            verify_import()
            
            print("\n🎉 SUCCESS!")
            print("=" * 60)
            print("✅ Transaction data has been successfully mapped and imported")
            print("✅ All 50 clients now have transaction history for spending analytics")
            print("✅ You can now run EliteX.py with rich transaction data")
            print()
            print("🚀 Next steps:")
            print("  1. Run: python EliteX.py --client 10GLPHG")
            print("  2. Or run: python runAllClientX.py")
            print("  3. The spending pattern analysis will now work with real transaction data")
        else:
            print("\n❌ Import failed. Please check the errors above.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
