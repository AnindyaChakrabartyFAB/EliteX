#!/usr/bin/env python3
"""
check_transaction_clients.py

Check which clients from the EliteX.py list have transaction history available
in the core.client_transaction table.
"""

import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Client list from EliteX.py
CLIENT_IDS = [
    '10GLPHG', '10GRRXX', '10PKFPQ', '10QAXPK', '10QHKPA', '10QHLHP', '10QXGLF', '10QXRPX', '10RXAKP', '10XQKRF',
    '11AAPGR', '11ALFPK', '11FKLLH', '11FQLKK', '11FXHLQ', '11HXFGR', '11HXPLF', '11KPGQK', '11KQKXL', '11KQXAQ',
    '11LPKHH', '11QHRKF', '11QPPQG', '12AHQHL', '12APFQL', '12HAHQH', '12HAKFG', '12HHXGA', '12KRAPA', '12LFGLA',
    '12QQAHQ', '12XFGRP', '13HHAAX', '13KFXRF', '13KHGPQ', '13RXRXF', '14FPRPR', '14HFQAR', '14HPHKR', '14HPPQL',
    '14KAKGL', '14LHGPG', '14LRHXX', '14LXHLQ', '14QPXFK', '15GGGKP', '15GGRAH', '15GRGFK', '15GXHXR', '15HGRQA'
]

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

def check_client_transactions(connection, client_id):
    """Check if a client has transaction history"""
    try:
        cursor = connection.cursor()
        
        # Check if client has any transactions
        query = """
        SELECT 
            COUNT(*) as transaction_count,
            MIN(date) as earliest_transaction,
            MAX(date) as latest_transaction,
            COUNT(DISTINCT transaction_type) as unique_transaction_types
        FROM core.client_transaction 
        WHERE client_id = %s
        """
        
        cursor.execute(query, (client_id,))
        result = cursor.fetchone()
        
        if result:
            count, earliest, latest, unique_types = result
            return {
                'has_transactions': count > 0,
                'transaction_count': count,
                'earliest_transaction': earliest,
                'latest_transaction': latest,
                'unique_transaction_types': unique_types
            }
        else:
            return {
                'has_transactions': False,
                'transaction_count': 0,
                'earliest_transaction': None,
                'latest_transaction': None,
                'unique_transaction_types': 0
            }
            
    except Exception as e:
        print(f"❌ Error checking transactions for {client_id}: {e}")
        return {
            'has_transactions': False,
            'transaction_count': 0,
            'earliest_transaction': None,
            'latest_transaction': None,
            'unique_transaction_types': 0,
            'error': str(e)
        }

def get_transaction_types(connection, client_id):
    """Get the transaction types for a client"""
    try:
        cursor = connection.cursor()
        
        query = """
        SELECT 
            transaction_type,
            COUNT(*) as count,
            SUM(transaction_amount) as total_amount
        FROM core.client_transaction 
        WHERE client_id = %s
        GROUP BY transaction_type
        ORDER BY count DESC
        """
        
        cursor.execute(query, (client_id,))
        results = cursor.fetchall()
        
        return [
            {
                'type': row[0],
                'count': row[1],
                'total_amount': float(row[2]) if row[2] else 0
            }
            for row in results
        ]
        
    except Exception as e:
        print(f"❌ Error getting transaction types for {client_id}: {e}")
        return []

def main():
    print("🔍 Checking transaction history for clients from EliteX.py list")
    print("=" * 80)
    
    # Connect to database
    connection = connect_to_database()
    if not connection:
        return
    
    print(f"✅ Connected to Elite PostgreSQL database")
    print(f"📊 Checking {len(CLIENT_IDS)} clients for transaction history...")
    print()
    
    clients_with_transactions = []
    clients_without_transactions = []
    
    for i, client_id in enumerate(CLIENT_IDS, 1):
        print(f"[{i:2d}/{len(CLIENT_IDS)}] Checking {client_id}...", end=" ")
        
        # Check transaction history
        tx_data = check_client_transactions(connection, client_id)
        
        if tx_data['has_transactions']:
            clients_with_transactions.append({
                'client_id': client_id,
                'transaction_count': tx_data['transaction_count'],
                'earliest_transaction': tx_data['earliest_transaction'],
                'latest_transaction': tx_data['latest_transaction'],
                'unique_transaction_types': tx_data['unique_transaction_types']
            })
            print(f"✅ {tx_data['transaction_count']} transactions")
        else:
            clients_without_transactions.append(client_id)
            print("❌ No transactions")
    
    connection.close()
    
    print("\n" + "=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)
    
    print(f"✅ Clients WITH transaction history: {len(clients_with_transactions)}")
    print(f"❌ Clients WITHOUT transaction history: {len(clients_without_transactions)}")
    print()
    
    if clients_with_transactions:
        print("🎯 CLIENTS WITH TRANSACTION HISTORY:")
        print("-" * 50)
        for client in clients_with_transactions:
            print(f"  {client['client_id']:8s} | {client['transaction_count']:3d} transactions | "
                  f"{client['earliest_transaction']} to {client['latest_transaction']} | "
                  f"{client['unique_transaction_types']} types")
    
    if clients_without_transactions:
        print("\n❌ CLIENTS WITHOUT TRANSACTION HISTORY:")
        print("-" * 50)
        for client_id in clients_without_transactions:
            print(f"  {client_id}")
    
    # Show detailed transaction types for first few clients with transactions
    if clients_with_transactions:
        print(f"\n🔍 DETAILED TRANSACTION TYPES (first 3 clients):")
        print("-" * 50)
        
        connection = connect_to_database()
        if connection:
            for client in clients_with_transactions[:3]:
                print(f"\n📊 {client['client_id']} Transaction Types:")
                tx_types = get_transaction_types(connection, client['client_id'])
                for tx_type in tx_types:
                    print(f"    {tx_type['type']:15s} | {tx_type['count']:3d} transactions | "
                          f"Total: {tx_type['total_amount']:12,.2f}")
            connection.close()
    
    # Generate Python list for easy copy-paste
    print(f"\n📝 PYTHON LIST FOR CLIENTS WITH TRANSACTIONS:")
    print("-" * 50)
    if clients_with_transactions:
        client_list = [client['client_id'] for client in clients_with_transactions]
        print("CLIENTS_WITH_TRANSACTIONS = [")
        for i in range(0, len(client_list), 10):
            batch = client_list[i:i+10]
            print(f"    {repr(batch)[1:-1]},")
        print("]")
    else:
        print("CLIENTS_WITH_TRANSACTIONS = []")

if __name__ == "__main__":
    main()
