#!/usr/bin/env python3
"""
descriptiveAnalytics.py - Data Quality Analysis for EliteX V7 with Full Table Columns

This script:
1. Selects ALL columns from each table using SELECT * (NO AGGREGATION)
2. Exports raw tables to Excel with ALL rows (including multiple rows per client)
3. Aggregates data with list creation ONLY for coverage analysis
4. Analyzes coverage and missing data on the aggregated dataset
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import db_engine
from sqlalchemy import text

print("\n" + "="*100)
print("ELITEX V7 - DATA QUALITY & COMPLETENESS ANALYSIS (ALL COLUMNS, NO AGGREGATION)")
print("="*100)
print(f"Analysis Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*100 + "\n")

# Create output directory
OUTPUT_DIR = Path("Output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Database engine
engine = db_engine.elite_engine

# ============================================================================
# STEP 1: LOAD CLIENT_CONTEXT - NO AGGREGATION
# ============================================================================
print("STEP 1: Loading core.client_context...")
print("-" * 100)

query_clients = """
SELECT * FROM core.client_context
WHERE client_id IS NOT NULL
"""

df_clients_raw = pd.read_sql(query_clients, engine)
df_clients_raw['client_id'] = df_clients_raw['client_id'].str.upper()

print(f"✓ Loaded {len(df_clients_raw):,} client records with {len(df_clients_raw.columns)} columns")
print(f"  Unique clients: {df_clients_raw['client_id'].nunique():,}")
print()

# ============================================================================
# STEP 2: LOAD CLIENT_INVESTMENT - NO AGGREGATION
# ============================================================================
print("STEP 2: Loading core.client_investment...")
print("-" * 100)

query_investment = """
SELECT * FROM core.client_investment
"""

try:
    df_investment_raw = pd.read_sql(query_investment, engine)
    df_investment_raw['client_id'] = df_investment_raw['client_id'].str.upper()
    
    print(f"✓ Loaded {len(df_investment_raw):,} investment records with {len(df_investment_raw.columns)} columns")
    print(f"  Unique clients: {df_investment_raw['client_id'].nunique():,}")
except Exception as e:
    print(f"✗ Error loading client_investment: {e}")
    df_investment_raw = pd.DataFrame(columns=['client_id'])

print()

# ============================================================================
# STEP 3: LOAD CLIENT_PORTFOLIO - NO AGGREGATION
# ============================================================================
print("STEP 3: Loading core.client_portfolio...")
print("-" * 100)

query_portfolio = """
SELECT * FROM core.client_portfolio
"""

try:
    df_portfolio_raw = pd.read_sql(query_portfolio, engine)
    df_portfolio_raw['client_id'] = df_portfolio_raw['client_id'].str.upper()
    
    print(f"✓ Loaded {len(df_portfolio_raw):,} portfolio records with {len(df_portfolio_raw.columns)} columns")
    print(f"  Unique clients: {df_portfolio_raw['client_id'].nunique():,}")
except Exception as e:
    print(f"✗ Error loading client_portfolio: {e}")
    df_portfolio_raw = pd.DataFrame(columns=['client_id'])

print()

# ============================================================================
# STEP 4: LOAD PRODUCTBALANCE - NO AGGREGATION (maps to customer_number)
# ============================================================================
print("STEP 4: Loading core.productbalance...")
print("-" * 100)

query_productbalance = """
SELECT * FROM core.productbalance
"""

try:
    df_productbalance_raw = pd.read_sql(query_productbalance, engine)
    df_productbalance_raw['customer_number'] = df_productbalance_raw['customer_number'].str.upper()
    
    print(f"✓ Loaded {len(df_productbalance_raw):,} product balance records with {len(df_productbalance_raw.columns)} columns")
    print(f"  Unique customers: {df_productbalance_raw['customer_number'].nunique():,}")
except Exception as e:
    print(f"✗ Error loading productbalance: {e}")
    df_productbalance_raw = pd.DataFrame(columns=['customer_number'])

print()

# ============================================================================
# STEP 5: LOAD CLIENT_PROD_BALANCE_MONTHLY - NO AGGREGATION
# ============================================================================
print("STEP 5: Loading core.client_prod_balance_monthly...")
print("-" * 100)

query_monthly = """
SELECT * FROM core.client_prod_balance_monthly
"""

try:
    df_monthly_raw = pd.read_sql(query_monthly, engine)
    df_monthly_raw['client_id'] = df_monthly_raw['client_id'].str.upper()
    
    print(f"✓ Loaded {len(df_monthly_raw):,} monthly balance records with {len(df_monthly_raw.columns)} columns")
    print(f"  Unique clients: {df_monthly_raw['client_id'].nunique():,}")
except Exception as e:
    print(f"✗ Error loading client_prod_balance_monthly: {e}")
    df_monthly_raw = pd.DataFrame(columns=['client_id'])

print()

# ============================================================================
# STEP 6: LOAD AECB ALERTS - NO AGGREGATION (maps to cif)
# ============================================================================
print("STEP 6: Loading core.aecbalerts...")
print("-" * 100)

query_aecb = """
SELECT * FROM core.aecbalerts
"""

try:
    df_aecb_raw = pd.read_sql(query_aecb, engine)
    df_aecb_raw['cif'] = df_aecb_raw['cif'].str.upper()
    
    print(f"✓ Loaded {len(df_aecb_raw):,} AECB alert records with {len(df_aecb_raw.columns)} columns")
    print(f"  Unique clients: {df_aecb_raw['cif'].nunique():,}")
except Exception as e:
    print(f"✗ Error loading aecbalerts: {e}")
    df_aecb_raw = pd.DataFrame(columns=['cif'])

print()

# ============================================================================
# STEP 7: LOAD BANCASSURANCE - NO AGGREGATION
# ============================================================================
print("STEP 7: Loading core.bancaclientproduct...")
print("-" * 100)

query_banca = """
SELECT * FROM core.bancaclientproduct
"""

try:
    df_banca_raw = pd.read_sql(query_banca, engine)
    df_banca_raw['client_id'] = df_banca_raw['client_id'].str.upper()
    
    print(f"✓ Loaded {len(df_banca_raw):,} bancassurance records with {len(df_banca_raw.columns)} columns")
    print(f"  Unique clients: {df_banca_raw['client_id'].nunique():,}")
except Exception as e:
    print(f"✗ Error loading bancaclientproduct: {e}")
    df_banca_raw = pd.DataFrame(columns=['client_id'])

print()

# ============================================================================
# STEP 8: LOAD UPSELL OPPORTUNITIES - NO AGGREGATION
# ============================================================================
print("STEP 8: Loading app.upsellopportunity...")
print("-" * 100)

query_upsell = """
SELECT * FROM app.upsellopportunity
"""

try:
    df_upsell_raw = pd.read_sql(query_upsell, engine)
    df_upsell_raw['client_id'] = df_upsell_raw['client_id'].str.upper()
    
    print(f"✓ Loaded {len(df_upsell_raw):,} upsell opportunity records with {len(df_upsell_raw.columns)} columns")
    print(f"  Unique clients: {df_upsell_raw['client_id'].nunique():,}")
except Exception as e:
    print(f"✗ Error loading upsellopportunity: {e}")
    df_upsell_raw = pd.DataFrame(columns=['client_id'])

print()

# ============================================================================
# STEP 9: LOAD RM MAPPING - NO AGGREGATION
# ============================================================================
print("STEP 9: Loading core.user_join_client_context...")
print("-" * 100)

query_rm = """
SELECT * FROM core.user_join_client_context
"""

try:
    df_rm_raw = pd.read_sql(query_rm, engine)
    df_rm_raw['client_id'] = df_rm_raw['client_id'].str.upper()
    
    print(f"✓ Loaded {len(df_rm_raw):,} RM-client mapping records with {len(df_rm_raw.columns)} columns")
    print(f"  Unique clients: {df_rm_raw['client_id'].nunique():,}")
except Exception as e:
    print(f"✗ Error loading user_join_client_context: {e}")
    df_rm_raw = pd.DataFrame(columns=['client_id'])

print()

# ============================================================================
# STEP 10: LOAD CALL REPORTS (TRANSCRIPTS)
# ============================================================================
print("STEP 10: Loading core.callreport...")
print("-" * 100)

query_callreport = """
SELECT * FROM core.callreport
"""

try:
    df_callreport_raw = pd.read_sql(query_callreport, engine)
    df_callreport_raw['client_id'] = df_callreport_raw['client_id'].str.upper()
    
    print(f"✓ Loaded {len(df_callreport_raw):,} call report records with {len(df_callreport_raw.columns)} columns")
    print(f"  Unique clients: {df_callreport_raw['client_id'].nunique():,}")
except Exception as e:
    print(f"✗ Error loading callreport: {e}")
    df_callreport_raw = pd.DataFrame(columns=['client_id'])

print()

# ============================================================================
# STEP 11: LOAD TRANSACTION ACCOUNT DATA
# ============================================================================
print("STEP 11: Loading core.clienttransactionaccount...")
print("-" * 100)

query_txn_account = """
SELECT * FROM core.clienttransactionaccount
"""

try:
    df_txn_account_raw = pd.read_sql(query_txn_account, engine)
    df_txn_account_raw['customer_id'] = df_txn_account_raw['customer_id'].str.upper()
    
    print(f"✓ Loaded {len(df_txn_account_raw):,} transaction account records with {len(df_txn_account_raw.columns)} columns")
    print(f"  Unique customers: {df_txn_account_raw['customer_id'].nunique():,}")
except Exception as e:
    print(f"✗ Error loading clienttransactionaccount: {e}")
    df_txn_account_raw = pd.DataFrame(columns=['customer_id'])

print()

# ============================================================================
# STEP 12: LOAD CREDIT TRANSACTION DATA
# ============================================================================
print("STEP 12: Loading core.clienttransactioncredit...")
print("-" * 100)

query_txn_credit = """
SELECT * FROM core.clienttransactioncredit
"""

try:
    df_txn_credit_raw = pd.read_sql(query_txn_credit, engine)
    df_txn_credit_raw['customer_number'] = df_txn_credit_raw['customer_number'].str.upper()
    
    print(f"✓ Loaded {len(df_txn_credit_raw):,} credit transaction records with {len(df_txn_credit_raw.columns)} columns")
    print(f"  Unique customers: {df_txn_credit_raw['customer_number'].nunique():,}")
except Exception as e:
    print(f"✗ Error loading clienttransactioncredit: {e}")
    df_txn_credit_raw = pd.DataFrame(columns=['customer_number'])

print()

# ============================================================================
# STEP 13: LOAD DEBIT TRANSACTION DATA
# ============================================================================
print("STEP 13: Loading core.clienttransactiondebit...")
print("-" * 100)

query_txn_debit = """
SELECT * FROM core.clienttransactiondebit
"""

try:
    df_txn_debit_raw = pd.read_sql(query_txn_debit, engine)
    df_txn_debit_raw['customer_number'] = df_txn_debit_raw['customer_number'].str.upper()
    
    print(f"✓ Loaded {len(df_txn_debit_raw):,} debit transaction records with {len(df_txn_debit_raw.columns)} columns")
    print(f"  Unique customers: {df_txn_debit_raw['customer_number'].nunique():,}")
except Exception as e:
    print(f"✗ Error loading clienttransactiondebit: {e}")
    df_txn_debit_raw = pd.DataFrame(columns=['customer_number'])

print()

# ============================================================================
# STEP 14: COVERAGE ANALYSIS BY MERGING EACH TABLE WITH CLIENT_CONTEXT
# ============================================================================
print("\n" + "="*100)
print("STEP 14: COVERAGE ANALYSIS - MERGING EACH TABLE WITH CLIENT_CONTEXT")
print("="*100)

# Get unique clients from client_context
df_clients = df_clients_raw.drop_duplicates(subset=['client_id'])
total_clients = len(df_clients)
print(f"Base: {total_clients:,} unique clients")
print("-" * 100)

# Dictionary to store coverage results
coverage_results = {}

# 1. Investment Coverage - Use inner join to get only clients WITH data
if not df_investment_raw.empty:
    df_with_inv = df_clients[['client_id']].merge(df_investment_raw[['client_id']].drop_duplicates(), on='client_id', how='inner')
    clients_with_data = len(df_with_inv)
    coverage_results['Investment'] = {
        'source_table': 'core.client_investment',
        'total_rows': len(df_investment_raw),
        'unique_clients_with_data': clients_with_data,
        'coverage_pct': round((clients_with_data / total_clients) * 100, 2),
        'total_columns': len(df_investment_raw.columns)
    }
    print(f"✓ Investment: {clients_with_data:,} clients have investment data ({coverage_results['Investment']['coverage_pct']}%)")
else:
    coverage_results['Investment'] = {'source_table': 'core.client_investment', 'total_rows': 0, 'unique_clients_with_data': 0, 'coverage_pct': 0.0, 'total_columns': 0}

# 2. Portfolio Coverage - Use inner join
if not df_portfolio_raw.empty:
    df_with_port = df_clients[['client_id']].merge(df_portfolio_raw[['client_id']].drop_duplicates(), on='client_id', how='inner')
    clients_with_data = len(df_with_port)
    coverage_results['Portfolio'] = {
        'source_table': 'core.client_portfolio',
        'total_rows': len(df_portfolio_raw),
        'unique_clients_with_data': clients_with_data,
        'coverage_pct': round((clients_with_data / total_clients) * 100, 2),
        'total_columns': len(df_portfolio_raw.columns)
    }
    print(f"✓ Portfolio: {clients_with_data:,} clients have portfolio data ({coverage_results['Portfolio']['coverage_pct']}%)")
else:
    coverage_results['Portfolio'] = {'source_table': 'core.client_portfolio', 'total_rows': 0, 'unique_clients_with_data': 0, 'coverage_pct': 0.0, 'total_columns': 0}

# 3. Product Balance Coverage - Use inner join on customer_number
if not df_productbalance_raw.empty:
    df_pb_unique = df_productbalance_raw[['customer_number']].drop_duplicates()
    df_pb_unique.columns = ['client_id']
    df_with_pb = df_clients[['client_id']].merge(df_pb_unique, on='client_id', how='inner')
    clients_with_data = len(df_with_pb)
    coverage_results['Product Balance'] = {
        'source_table': 'core.productbalance',
        'total_rows': len(df_productbalance_raw),
        'unique_clients_with_data': clients_with_data,
        'coverage_pct': round((clients_with_data / total_clients) * 100, 2),
        'total_columns': len(df_productbalance_raw.columns)
    }
    print(f"✓ Product Balance: {clients_with_data:,} clients have product data ({coverage_results['Product Balance']['coverage_pct']}%)")
else:
    coverage_results['Product Balance'] = {'source_table': 'core.productbalance', 'total_rows': 0, 'unique_clients_with_data': 0, 'coverage_pct': 0.0, 'total_columns': 0}

# 4. Monthly Balance Coverage - Use inner join
if not df_monthly_raw.empty:
    df_with_monthly = df_clients[['client_id']].merge(df_monthly_raw[['client_id']].drop_duplicates(), on='client_id', how='inner')
    clients_with_data = len(df_with_monthly)
    coverage_results['Monthly Balance'] = {
        'source_table': 'core.client_prod_balance_monthly',
        'total_rows': len(df_monthly_raw),
        'unique_clients_with_data': clients_with_data,
        'coverage_pct': round((clients_with_data / total_clients) * 100, 2),
        'total_columns': len(df_monthly_raw.columns)
    }
    print(f"✓ Monthly Balance: {clients_with_data:,} clients have monthly balance data ({coverage_results['Monthly Balance']['coverage_pct']}%)")
else:
    coverage_results['Monthly Balance'] = {'source_table': 'core.client_prod_balance_monthly', 'total_rows': 0, 'unique_clients_with_data': 0, 'coverage_pct': 0.0, 'total_columns': 0}

# 5. AECB Alerts Coverage - Use inner join on cif
if not df_aecb_raw.empty:
    df_aecb_unique = df_aecb_raw[['cif']].drop_duplicates()
    df_aecb_unique.columns = ['client_id']
    df_with_aecb = df_clients[['client_id']].merge(df_aecb_unique, on='client_id', how='inner')
    clients_with_data = len(df_with_aecb)
    coverage_results['AECB Alerts'] = {
        'source_table': 'core.aecbalerts',
        'total_rows': len(df_aecb_raw),
        'unique_clients_with_data': clients_with_data,
        'coverage_pct': round((clients_with_data / total_clients) * 100, 2),
        'total_columns': len(df_aecb_raw.columns)
    }
    print(f"✓ AECB Alerts: {clients_with_data:,} clients have AECB alerts ({coverage_results['AECB Alerts']['coverage_pct']}%)")
else:
    coverage_results['AECB Alerts'] = {'source_table': 'core.aecbalerts', 'total_rows': 0, 'unique_clients_with_data': 0, 'coverage_pct': 0.0, 'total_columns': 0}

# 6. Bancassurance Coverage - Use inner join
if not df_banca_raw.empty:
    df_with_banca = df_clients[['client_id']].merge(df_banca_raw[['client_id']].drop_duplicates(), on='client_id', how='inner')
    clients_with_data = len(df_with_banca)
    coverage_results['Bancassurance'] = {
        'source_table': 'core.bancaclientproduct',
        'total_rows': len(df_banca_raw),
        'unique_clients_with_data': clients_with_data,
        'coverage_pct': round((clients_with_data / total_clients) * 100, 2),
        'total_columns': len(df_banca_raw.columns)
    }
    print(f"✓ Bancassurance: {clients_with_data:,} clients have bancassurance data ({coverage_results['Bancassurance']['coverage_pct']}%)")
else:
    coverage_results['Bancassurance'] = {'source_table': 'core.bancaclientproduct', 'total_rows': 0, 'unique_clients_with_data': 0, 'coverage_pct': 0.0, 'total_columns': 0}

# 7. Upsell Coverage - Use inner join
if not df_upsell_raw.empty:
    df_with_upsell = df_clients[['client_id']].merge(df_upsell_raw[['client_id']].drop_duplicates(), on='client_id', how='inner')
    clients_with_data = len(df_with_upsell)
    coverage_results['Upsell Opportunities'] = {
        'source_table': 'app.upsellopportunity',
        'total_rows': len(df_upsell_raw),
        'unique_clients_with_data': clients_with_data,
        'coverage_pct': round((clients_with_data / total_clients) * 100, 2),
        'total_columns': len(df_upsell_raw.columns)
    }
    print(f"✓ Upsell Opportunities: {clients_with_data:,} clients have upsell opportunities ({coverage_results['Upsell Opportunities']['coverage_pct']}%)")
else:
    coverage_results['Upsell Opportunities'] = {'source_table': 'app.upsellopportunity', 'total_rows': 0, 'unique_clients_with_data': 0, 'coverage_pct': 0.0, 'total_columns': 0}

# 8. RM Mapping Coverage - Use inner join
if not df_rm_raw.empty:
    df_with_rm = df_clients[['client_id']].merge(df_rm_raw[['client_id']].drop_duplicates(), on='client_id', how='inner')
    clients_with_data = len(df_with_rm)
    coverage_results['RM Mapping'] = {
        'source_table': 'core.user_join_client_context',
        'total_rows': len(df_rm_raw),
        'unique_clients_with_data': clients_with_data,
        'coverage_pct': round((clients_with_data / total_clients) * 100, 2),
        'total_columns': len(df_rm_raw.columns)
    }
    print(f"✓ RM Mapping: {clients_with_data:,} clients have RM assigned ({coverage_results['RM Mapping']['coverage_pct']}%)")
else:
    coverage_results['RM Mapping'] = {'source_table': 'core.user_join_client_context', 'total_rows': 0, 'unique_clients_with_data': 0, 'coverage_pct': 0.0, 'total_columns': 0}

# 9. Call Reports Coverage - Use inner join
if not df_callreport_raw.empty:
    df_with_call = df_clients[['client_id']].merge(df_callreport_raw[['client_id']].drop_duplicates(), on='client_id', how='inner')
    clients_with_data = len(df_with_call)
    coverage_results['Call Reports (Transcripts)'] = {
        'source_table': 'core.callreport',
        'total_rows': len(df_callreport_raw),
        'unique_clients_with_data': clients_with_data,
        'coverage_pct': round((clients_with_data / total_clients) * 100, 2),
        'total_columns': len(df_callreport_raw.columns)
    }
    print(f"✓ Call Reports (Transcripts): {clients_with_data:,} clients have call transcripts ({coverage_results['Call Reports (Transcripts)']['coverage_pct']}%)")
else:
    coverage_results['Call Reports (Transcripts)'] = {'source_table': 'core.callreport', 'total_rows': 0, 'unique_clients_with_data': 0, 'coverage_pct': 0.0, 'total_columns': 0}

# 10. Transaction Account Coverage - Use inner join on customer_id
if not df_txn_account_raw.empty:
    df_txn_acc_unique = df_txn_account_raw[['customer_id']].drop_duplicates()
    df_txn_acc_unique.columns = ['client_id']
    df_with_txn_acc = df_clients[['client_id']].merge(df_txn_acc_unique, on='client_id', how='inner')
    clients_with_data = len(df_with_txn_acc)
    coverage_results['Transaction Account'] = {
        'source_table': 'core.clienttransactionaccount',
        'total_rows': len(df_txn_account_raw),
        'unique_clients_with_data': clients_with_data,
        'coverage_pct': round((clients_with_data / total_clients) * 100, 2),
        'total_columns': len(df_txn_account_raw.columns)
    }
    print(f"✓ Transaction Account: {clients_with_data:,} clients have account transactions ({coverage_results['Transaction Account']['coverage_pct']}%)")
else:
    coverage_results['Transaction Account'] = {'source_table': 'core.clienttransactionaccount', 'total_rows': 0, 'unique_clients_with_data': 0, 'coverage_pct': 0.0, 'total_columns': 0}

# 11. Credit Transaction Coverage - Use inner join on customer_number
if not df_txn_credit_raw.empty:
    df_txn_credit_unique = df_txn_credit_raw[['customer_number']].drop_duplicates()
    df_txn_credit_unique.columns = ['client_id']
    df_with_txn_credit = df_clients[['client_id']].merge(df_txn_credit_unique, on='client_id', how='inner')
    clients_with_data = len(df_with_txn_credit)
    coverage_results['Credit Transactions'] = {
        'source_table': 'core.clienttransactioncredit',
        'total_rows': len(df_txn_credit_raw),
        'unique_clients_with_data': clients_with_data,
        'coverage_pct': round((clients_with_data / total_clients) * 100, 2),
        'total_columns': len(df_txn_credit_raw.columns)
    }
    print(f"✓ Credit Transactions: {clients_with_data:,} clients have credit transactions ({coverage_results['Credit Transactions']['coverage_pct']}%)")
else:
    coverage_results['Credit Transactions'] = {'source_table': 'core.clienttransactioncredit', 'total_rows': 0, 'unique_clients_with_data': 0, 'coverage_pct': 0.0, 'total_columns': 0}

# 12. Debit Transaction Coverage - Use inner join on customer_number
if not df_txn_debit_raw.empty:
    df_txn_debit_unique = df_txn_debit_raw[['customer_number']].drop_duplicates()
    df_txn_debit_unique.columns = ['client_id']
    df_with_txn_debit = df_clients[['client_id']].merge(df_txn_debit_unique, on='client_id', how='inner')
    clients_with_data = len(df_with_txn_debit)
    coverage_results['Debit Transactions'] = {
        'source_table': 'core.clienttransactiondebit',
        'total_rows': len(df_txn_debit_raw),
        'unique_clients_with_data': clients_with_data,
        'coverage_pct': round((clients_with_data / total_clients) * 100, 2),
        'total_columns': len(df_txn_debit_raw.columns)
    }
    print(f"✓ Debit Transactions: {clients_with_data:,} clients have debit transactions ({coverage_results['Debit Transactions']['coverage_pct']}%)")
else:
    coverage_results['Debit Transactions'] = {'source_table': 'core.clienttransactiondebit', 'total_rows': 0, 'unique_clients_with_data': 0, 'coverage_pct': 0.0, 'total_columns': 0}

print()

# ============================================================================
# STEP 15: CREATE COVERAGE SUMMARY DATAFRAME
# ============================================================================
print("\n" + "="*100)
print("STEP 15: CREATING COVERAGE SUMMARY")
print("="*100)

# Convert coverage results to DataFrame
coverage_summary_data = []
for table_name, stats in coverage_results.items():
    coverage_summary_data.append({
        'table_name': table_name,
        'source_table': stats.get('source_table', ''),
        'total_rows': stats.get('total_rows', 0),
        'total_columns': stats.get('total_columns', 0),
        'unique_clients_with_data': stats.get('unique_clients_with_data', 0),
        'clients_without_data': total_clients - stats.get('unique_clients_with_data', 0),
        'coverage_pct': stats.get('coverage_pct', 0.0),
        'missing_pct': round(100 - stats.get('coverage_pct', 0.0), 2)
    })

df_table_coverage = pd.DataFrame(coverage_summary_data)
df_table_coverage = df_table_coverage.sort_values('coverage_pct', ascending=False)

print(f"✓ Coverage summary created for {len(df_table_coverage)} tables")
print()

# Print summary
print("Table Coverage Summary:")
print("-" * 100)
for _, row in df_table_coverage.iterrows():
    print(f"  {row['table_name']:<25} | {row['unique_clients_with_data']:>7,} clients ({row['coverage_pct']:>6.2f}%) | {row['total_rows']:>10,} rows")
print()

# ============================================================================
# STEP 16: GENERATE SUMMARY STATISTICS
# ============================================================================
print("\n" + "="*100)
print("STEP 16: GENERATING SUMMARY STATISTICS")
print("="*100)

# Calculate overall statistics
tables_with_data = len([v for v in coverage_results.values() if v.get('unique_clients_with_data', 0) > 0])
avg_coverage = round(np.mean([v.get('coverage_pct', 0) for v in coverage_results.values()]), 2)
total_raw_rows = sum([v.get('total_rows', 0) for v in coverage_results.values()])

summary_stats = {
    'total_unique_clients': total_clients,
    'total_tables_analyzed': len(coverage_results),
    'tables_with_client_data': tables_with_data,
    'total_raw_data_rows': total_raw_rows,
    'average_table_coverage_pct': avg_coverage,
    'clients_with_investment': coverage_results.get('Investment', {}).get('unique_clients_with_data', 0),
    'clients_with_portfolio': coverage_results.get('Portfolio', {}).get('unique_clients_with_data', 0),
    'clients_with_products': coverage_results.get('Product Balance', {}).get('unique_clients_with_data', 0),
    'clients_with_rm_assigned': coverage_results.get('RM Mapping', {}).get('unique_clients_with_data', 0)
}

print("Summary Statistics:")
print("-" * 100)
for key, value in summary_stats.items():
    print(f"  {key}: {value:,}" if isinstance(value, int) else f"  {key}: {value}")
print()

# ============================================================================
# STEP 17: EXPORT TO EXCEL WITH RAW DATA TABLES (NO AGGREGATION)
# ============================================================================
print("\n" + "="*100)
print("STEP 17: EXPORTING RESULTS TO EXCEL")
print("="*100)

# Helper function to remove timezone from datetime columns
def remove_timezone(df):
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            try:
                df[col] = df[col].dt.tz_localize(None)
            except:
                pass
    return df

# Remove timezone from all dataframes
df_clients_raw = remove_timezone(df_clients_raw)
if not df_investment_raw.empty:
    df_investment_raw = remove_timezone(df_investment_raw)
if not df_portfolio_raw.empty:
    df_portfolio_raw = remove_timezone(df_portfolio_raw)
if not df_productbalance_raw.empty:
    df_productbalance_raw = remove_timezone(df_productbalance_raw)
if not df_monthly_raw.empty:
    df_monthly_raw = remove_timezone(df_monthly_raw)
if not df_aecb_raw.empty:
    df_aecb_raw = remove_timezone(df_aecb_raw)
if not df_banca_raw.empty:
    df_banca_raw = remove_timezone(df_banca_raw)
if not df_upsell_raw.empty:
    df_upsell_raw = remove_timezone(df_upsell_raw)
if not df_rm_raw.empty:
    df_rm_raw = remove_timezone(df_rm_raw)
if not df_callreport_raw.empty:
    df_callreport_raw = remove_timezone(df_callreport_raw)
if not df_txn_account_raw.empty:
    df_txn_account_raw = remove_timezone(df_txn_account_raw)
if not df_txn_credit_raw.empty:
    df_txn_credit_raw = remove_timezone(df_txn_credit_raw)
if not df_txn_debit_raw.empty:
    df_txn_debit_raw = remove_timezone(df_txn_debit_raw)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_file = OUTPUT_DIR / f"EliteX_Data_Quality_Report_{timestamp}.xlsx"

print("Creating comprehensive Excel report with ALL RAW DATA (NO AGGREGATION)...")
print("-" * 100)

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    
    # Sheet 1: Executive Summary
    df_summary = pd.DataFrame([summary_stats]).T
    df_summary.columns = ['Value']
    df_summary.index.name = 'Metric'
    df_summary.to_excel(writer, sheet_name='Executive Summary')
    print("✓ Sheet 1: Executive Summary")
    
    # Sheet 2: Table Coverage Summary
    df_table_coverage.to_excel(writer, sheet_name='Table Coverage Summary', index=False)
    print(f"✓ Sheet 2: Table Coverage Summary ({len(df_table_coverage)} tables)")
    
    # Export all RAW tables with ALL ROWS (NO AGGREGATION)
    print("\nExporting RAW data tables (ALL COLUMNS, ALL ROWS, NO AGGREGATION)...")
    print("-" * 100)
    
    # Client Context (ALL ROWS)
    df_clients_raw.to_excel(writer, sheet_name='RAW_ClientContext', index=False)
    print(f"✓ RAW_ClientContext: {len(df_clients_raw):,} rows, {len(df_clients_raw.columns)} columns")
    
    # Investment (ALL ROWS - multiple per client)
    if not df_investment_raw.empty:
        df_investment_raw.to_excel(writer, sheet_name='RAW_Investment', index=False)
        print(f"✓ RAW_Investment: {len(df_investment_raw):,} rows, {len(df_investment_raw.columns)} columns")
    
    # Portfolio (ALL ROWS - multiple per client)
    if not df_portfolio_raw.empty:
        df_portfolio_raw.to_excel(writer, sheet_name='RAW_Portfolio', index=False)
        print(f"✓ RAW_Portfolio: {len(df_portfolio_raw):,} rows, {len(df_portfolio_raw.columns)} columns")
    
    # Product Balance (limited to 100k rows for Excel size)
    if not df_productbalance_raw.empty:
        df_pb_export = df_productbalance_raw.head(100000)
        df_pb_export.to_excel(writer, sheet_name='RAW_ProductBalance', index=False)
        print(f"✓ RAW_ProductBalance: {len(df_pb_export):,} rows (of {len(df_productbalance_raw):,}), {len(df_pb_export.columns)} columns")
    
    # Monthly Balance (limited to 50k rows)
    if not df_monthly_raw.empty:
        df_monthly_export = df_monthly_raw.head(50000)
        df_monthly_export.to_excel(writer, sheet_name='RAW_MonthlyBalance', index=False)
        print(f"✓ RAW_MonthlyBalance: {len(df_monthly_export):,} rows (of {len(df_monthly_raw):,}), {len(df_monthly_export.columns)} columns")
    
    # AECB Alerts (ALL ROWS)
    if not df_aecb_raw.empty:
        df_aecb_raw.to_excel(writer, sheet_name='RAW_AECB_Alerts', index=False)
        print(f"✓ RAW_AECB_Alerts: {len(df_aecb_raw):,} rows, {len(df_aecb_raw.columns)} columns")
    
    # Bancassurance (ALL ROWS)
    if not df_banca_raw.empty:
        df_banca_raw.to_excel(writer, sheet_name='RAW_Bancassurance', index=False)
        print(f"✓ RAW_Bancassurance: {len(df_banca_raw):,} rows, {len(df_banca_raw.columns)} columns")
    
    # Upsell (ALL ROWS)
    if not df_upsell_raw.empty:
        df_upsell_raw.to_excel(writer, sheet_name='RAW_Upsell', index=False)
        print(f"✓ RAW_Upsell: {len(df_upsell_raw):,} rows, {len(df_upsell_raw.columns)} columns")
    
    # RM Mapping (ALL ROWS)
    if not df_rm_raw.empty:
        df_rm_raw.to_excel(writer, sheet_name='RAW_RM_Mapping', index=False)
        print(f"✓ RAW_RM_Mapping: {len(df_rm_raw):,} rows, {len(df_rm_raw.columns)} columns")
    
    # Call Reports/Transcripts (ALL ROWS)
    if not df_callreport_raw.empty:
        df_callreport_raw.to_excel(writer, sheet_name='RAW_CallReports', index=False)
        print(f"✓ RAW_CallReports: {len(df_callreport_raw):,} rows, {len(df_callreport_raw.columns)} columns")
    
    # Transaction Account (limited to 100k rows for Excel size)
    if not df_txn_account_raw.empty:
        df_txn_acc_export = df_txn_account_raw.head(100000)
        df_txn_acc_export.to_excel(writer, sheet_name='RAW_TxnAccount', index=False)
        print(f"✓ RAW_TxnAccount: {len(df_txn_acc_export):,} rows (of {len(df_txn_account_raw):,}), {len(df_txn_acc_export.columns)} columns")
    
    # Credit Transactions (limited to 100k rows)
    if not df_txn_credit_raw.empty:
        df_txn_credit_export = df_txn_credit_raw.head(100000)
        df_txn_credit_export.to_excel(writer, sheet_name='RAW_TxnCredit', index=False)
        print(f"✓ RAW_TxnCredit: {len(df_txn_credit_export):,} rows (of {len(df_txn_credit_raw):,}), {len(df_txn_credit_export.columns)} columns")
    
    # Debit Transactions (limited to 100k rows for Excel size)
    if not df_txn_debit_raw.empty:
        df_txn_debit_export = df_txn_debit_raw.head(100000)
        df_txn_debit_export.to_excel(writer, sheet_name='RAW_TxnDebit', index=False)
        print(f"✓ RAW_TxnDebit: {len(df_txn_debit_export):,} rows (of {len(df_txn_debit_raw):,}), {len(df_txn_debit_export.columns)} columns")

print("\n" + "="*100)
print(f"✓ Excel report saved: {output_file}")
print("="*100)
print()

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*100)
print("ANALYSIS COMPLETE - FINAL SUMMARY")
print("="*100)
print()
print(f"Total Unique Clients: {total_clients:,}")
print(f"Total Tables Analyzed: {summary_stats['total_tables_analyzed']}")
print(f"Total Raw Data Rows: {summary_stats['total_raw_data_rows']:,}")
print(f"Average Table Coverage: {summary_stats['average_table_coverage_pct']}%")
print()
print("Client Coverage by Feature (All Tables):")
print("-" * 100)
for _, row in df_table_coverage.iterrows():
    print(f"  - {row['table_name']:<30} : {row['unique_clients_with_data']:>7,} clients ({row['coverage_pct']:>6.2f}%)")
print()
print(f"✓ Full report saved to: {output_file}")
print("="*100)
print()
print("Analysis finished successfully!")
print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
