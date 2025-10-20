#!/usr/bin/env python3
"""
EliteX.py - Elite Financial Strategy Framework using OpenAI Agent SDK

Simple structure with:
- Manager Agent (orchestrates)
- Investment Agent
- Loan Agent  
- BankingCASA Agent
- Risk & Compliance Agent

Uses AEDB alerts and Share of Potential for client-specific strategies.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import argparse

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Disable Agents SDK tracing before importing agents
os.environ["AGENTS_TRACING_DISABLED"] = "1"
from agents import Agent, Runner, function_tool  # type: ignore

# Import prompts
from promptElite import (
    ELITE_MANAGER_AGENT_PROMPT,
    ELITE_INVESTMENT_AGENT_PROMPT_UPDATED,
    ELITE_LOAN_AGENT_PROMPT_UPDATED,
    ELITE_BANKING_CASA_AGENT_PROMPT_UPDATED,
    ELITE_RISK_COMPLIANCE_AGENT_PROMPT_UPDATED
)

# ----------------------------
# Logging Setup
# ----------------------------
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("elite_agentsdk")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(LOGS_DIR / "agent_conversations_elite.log")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter(
    fmt="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(message)s")
console_handler.setFormatter(console_formatter)

if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# ----------------------------
# Database Manager
# ----------------------------
class EliteDatabaseManager:
    """Database manager for Elite application using existing tables"""
    
    def __init__(self):
        load_dotenv()
        self.db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "database": os.getenv("DB_NAME", "elite_db"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", "")
        }
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(**self.db_config)
            logger.info("✅ Connected to Elite PostgreSQL database")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def _execute_query(self, query: str, params: tuple = None) -> list:
        """Execute query and return results as list of dictionaries"""
        try:
            # Ensure we have a fresh connection for each query to avoid rollback issues
            if self.connection.closed:
                self._connect()
            
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            # Enhanced error logging to identify the problematic query
            logger.error(f"❌ Query execution failed: {e}")
            logger.error(f"❌ Query: {query[:200]}...")  # Log first 200 chars of query
            logger.error(f"❌ Params: {params}")
            if "tuple index out of range" in str(e):
                logger.error(f"❌ TUPLE INDEX ERROR - Query: {query}")
                logger.error(f"❌ TUPLE INDEX ERROR - Params: {params}")
            # Rollback the transaction and reconnect
            try:
                self.connection.rollback()
            except:
                pass
            # Reconnect for next query
            try:
                self._connect()
            except:
                pass
            return []  # Return empty list instead of raising to continue execution
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime, Decimal and other objects"""
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif hasattr(obj, '__class__') and 'Decimal' in str(obj.__class__):
            return float(obj)
        elif obj is None:
            return None
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def get_elite_client_data(self, client_id: str) -> str:
        """Get comprehensive client profile data"""
        query = """
        SELECT 
            client_id, first_name, last_name, employer, dob, age, gender, 
            occupation, education, family, income, occupation_sector, 
            customer_personal_nationality, customer_personal_residence, 
            customer_profile_banking_segment, customer_profile_subsegment, 
            emirate, communication_no_1, communication_type_1, 
            communication_no_2, communication_type_2, email, 
            client_off_us_relationships, client_off_us_relationship_bank, 
            risk_appetite, risk_level, risk_segment, open_date, tenure, 
            kyc_date, kyc_expiry_date, professional_investor_flag, 
            aecb_rating, client_picture, last_update
        FROM core.client_context 
        WHERE LOWER(client_id) = LOWER(%s)
        LIMIT 1
        """
        result = self._execute_query(query, (client_id,))

        # Fallback to transactional context if not found
        if not result:
            try:
                t_query = """
                SELECT *
                FROM core.t_client_context 
                WHERE LOWER(client_id) = LOWER(%s)
                LIMIT 1
                """
                result = self._execute_query(t_query, (client_id,))
            except Exception:
                result = []
        
        if result:
            client_data = dict(result[0])
            client_data['full_name'] = f"{client_data.get('first_name', '')} {client_data.get('last_name', '')}".strip()
            
            # Enhanced analysis with comprehensive data
            age = float(client_data.get('age', 0) or 0)
            income = float(client_data.get('income', 0) or 0)
            tenure = float(client_data.get('tenure', 0) or 0)
            risk_appetite = client_data.get('risk_appetite', '')
            risk_level = int(client_data.get('risk_level', 0) or 0)
            risk_segment = client_data.get('risk_segment', '')
            banking_segment = client_data.get('customer_profile_banking_segment', '')
            subsegment = client_data.get('customer_profile_subsegment', '')
            professional_investor = client_data.get('professional_investor_flag', '')
            aecb_rating = client_data.get('aecb_rating', '')
            
            # Enhanced life stage calculation
            if age < 25:
                life_stage = "early_career"
            elif age < 35:
                life_stage = "career_building"
            elif age < 50:
                life_stage = "mid_career"
            elif age < 65:
                life_stage = "pre_retirement"
            else:
                life_stage = "retirement"
            
            # Enhanced risk capacity calculation based on available data
            if income > 2000000 or banking_segment == 'ULTRA_HIGH_NET_WORTH':
                risk_capacity = "very_high"
            elif income > 1000000 or banking_segment == 'HIGH_NET_WORTH' or subsegment == 'Private Banking':
                risk_capacity = "high"
            elif income > 500000 or banking_segment == 'AFFLUENT':
                risk_capacity = "medium"
            else:
                risk_capacity = "low"
            
            # Investment sophistication level based on available data
            if professional_investor == 'Y' or banking_segment == 'WEALTH_MANAGEMENT':
                sophistication = "sophisticated"
            elif subsegment == 'Private Banking' or risk_level > 4:
                sophistication = "intermediate"
            else:
                sophistication = "basic"
            
            # Client tier analysis based on available data
            if banking_segment == 'ULTRA_HIGH_NET_WORTH' or income > 5000000:
                client_tier = "ultra_high_net_worth"
            elif banking_segment == 'HIGH_NET_WORTH' or subsegment == 'Private Banking' or income > 1000000:
                client_tier = "high_net_worth"
            elif banking_segment == 'AFFLUENT' or income > 500000:
                client_tier = "affluent"
            else:
                client_tier = "mass_market"
            
            # Relationship strength
            if tenure > 10:
                relationship_strength = "very_strong"
            elif tenure > 5:
                relationship_strength = "strong"
            elif tenure > 2:
                relationship_strength = "moderate"
            else:
                relationship_strength = "new"
            
            # Income category
            if income > 5000000:
                income_category = "ultra_high"
            elif income > 1000000:
                income_category = "high"
            elif income > 500000:
                income_category = "medium"
            else:
                income_category = "low"
            
            client_data.update({
                'calculated_risk_capacity': risk_capacity,
                'calculated_life_stage': life_stage,
                'calculated_sophistication': sophistication,
                'calculated_client_tier': client_tier,
                'calculated_relationship_strength': relationship_strength,
                'income_category': income_category,
                'data_source': 'core.client_context',
                'profile_completeness': len([v for v in client_data.values() if v is not None and v != '']) / len(client_data) * 100
            })
            
        else:
            client_data = {"client_id": client_id, "error": "Client not found"}
        
        return json.dumps(client_data, indent=2, default=self._json_serializer)
    
    def get_elite_engagement_analysis(self, client_id: str) -> str:
        """Get comprehensive engagement analysis data"""
        try:
            # Get engagement analysis data
            engagement_query = """
            SELECT 
                ea.id, ea.comm_log_id, ea.analysis_result, ea.last_updated,
                cl.communication_id, cl.communication_source, cl.client_id, 
                cl.rm_id, cl.type, cl.subtype, cl.description, cl.communication_date, cl.status
            FROM core.engagement_analysis ea
            JOIN core.communication_log cl ON ea.comm_log_id = cl.comm_log_id
            WHERE cl.client_id = %s
            ORDER BY ea.last_updated DESC
            LIMIT 100
            """
            engagement_data = self._execute_query(engagement_query, (client_id,))
            
            # Get communication summary
            comm_summary_query = """
            SELECT 
                type, subtype, status, COUNT(*) as count,
                MIN(communication_date) as first_communication,
                MAX(communication_date) as last_communication
            FROM core.communication_log 
            WHERE client_id = %s
            GROUP BY type, subtype, status
            ORDER BY count DESC
            """
            comm_summary = self._execute_query(comm_summary_query, (client_id,))
            
            return json.dumps({
                "client_id": client_id,
                "engagement_analysis": [dict(e) for e in engagement_data] if engagement_data else [],
                "communication_summary": [dict(c) for c in comm_summary] if comm_summary else [],
                "total_engagements": len(engagement_data) if engagement_data else 0,
                "data_source": "core.engagement_analysis + core.communication_log"
            }, indent=2, default=self._json_serializer)
            
        except Exception as e:
            return json.dumps({"error": f"Failed to get engagement analysis: {str(e)}"}, default=self._json_serializer)
    
    def get_elite_communication_history(self, client_id: str) -> str:
        """Get comprehensive communication history"""
        try:
            # Get detailed communication log
            comm_query = """
            SELECT 
                comm_log_id, communication_id, communication_source, client_id, 
                rm_id, type, subtype, description, communication_date, status, 
                resolution_description, transcript, last_updated, time_key, load_date
            FROM core.communication_log 
            WHERE client_id = %s
            ORDER BY communication_date DESC
            LIMIT 100
            """
            communications = self._execute_query(comm_query, (client_id,))
            
            # Get RM communication patterns
            rm_patterns_query = """
            SELECT 
                rm_id, type, COUNT(*) as count,
                AVG(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completion_rate,
                MIN(communication_date) as first_contact, MAX(communication_date) as last_contact
            FROM core.communication_log 
            WHERE client_id = %s
            GROUP BY rm_id, type
            ORDER BY count DESC
            """
            rm_patterns = self._execute_query(rm_patterns_query, (client_id,))
            
            # Get communication frequency analysis
            frequency_query = """
            SELECT 
                DATE_TRUNC('month', communication_date) as month,
                COUNT(*) as communications,
                COUNT(DISTINCT type) as communication_types,
                COUNT(DISTINCT rm_id) as active_rms
            FROM core.communication_log 
            WHERE client_id = %s
            AND communication_date >= CURRENT_DATE - INTERVAL '12 months'
            GROUP BY DATE_TRUNC('month', communication_date)
            ORDER BY month DESC
            """
            frequency_data = self._execute_query(frequency_query, (client_id,))
            
            return json.dumps({
                "client_id": client_id,
                "communications": [dict(c) for c in communications] if communications else [],
                "rm_communication_patterns": [dict(r) for r in rm_patterns] if rm_patterns else [],
                "monthly_frequency": [dict(f) for f in frequency_data] if frequency_data else [],
                "total_communications": len(communications) if communications else 0,
                "data_source": "core.communication_log"
            }, indent=2, default=self._json_serializer)
            
        except Exception as e:
            return json.dumps({"error": f"Failed to get communication history: {str(e)}"}, default=self._json_serializer)
    
    def get_elite_investment_data(self, client_id: str) -> str:
        """Get investment data"""
        # Get client holdings
        holdings_query = """
        SELECT 
            client_id, asset_class, product_type, security_name, 
            investment_value_usd, current_price
        FROM core.client_holding 
        WHERE client_id = %s
        LIMIT 50
        """
        holdings = self._execute_query(holdings_query, (client_id,))
        
        # Get available fund products
        funds_query = """
        SELECT 
            id, name, investment_objective, total_net_assets,
            annualized_return_3y, annualized_return_5y, morningstar_rating
        FROM core.funds
        ORDER BY name
        LIMIT 20
        """
        funds = self._execute_query(funds_query)
        
        total_value = sum(float(h.get('investment_value_usd', 0) or 0) for h in holdings)
        
        return json.dumps({
            "client_id": client_id,
            "current_holdings": [dict(h) for h in holdings],
            "available_funds": [dict(f) for f in funds],
            "total_holdings_value": total_value,
            "holdings_count": len(holdings)
        }, indent=2, default=self._json_serializer)
    
    def get_elite_loan_data(self, client_id: str) -> str:
        """Get loan and credit data"""
        # Get credit transactions
        transactions_query = """
        SELECT 
            transaction_id, client_id, transaction_type, transaction_amount, 
            date, currency, booking_geography, name
        FROM core.client_transaction 
        WHERE client_id = %s AND transaction_type IN ('credit', 'loan', 'advance')
        ORDER BY date DESC
        LIMIT 100
        """
        transactions = self._execute_query(transactions_query, (client_id,))
        
        # Get AEDB alerts for loan-related inquiries
        aedb_query = """
        SELECT 
            risk_name, risk_level, match_diff_from_house_rec
        FROM core.client_holdings_risk_level 
        WHERE client_id = %s
        AND (risk_name ILIKE %s OR risk_name ILIKE %s OR risk_name ILIKE %s OR risk_name ILIKE %s)
        ORDER BY risk_level DESC
        LIMIT 50
        """
        aedb_alerts = self._execute_query(aedb_query, (client_id, '%auto%', '%home%', '%loan%', '%mortgage%'))
        
        # Get client profile to determine target segment
        client_query = """
        SELECT 
            customer_profile_banking_segment, risk_appetite, income
        FROM core.client_context 
        WHERE client_id = %s
        LIMIT 1
        """
        client_profile = self._execute_query(client_query, (client_id,))
        
        # Determine target segment for loan recommendations
        target_segment = 'mass_market'  # default
        if client_profile:
            banking_segment = client_profile[0].get('customer_profile_banking_segment', '')
            if banking_segment:
                target_segment = banking_segment
        
        # Get available credit products from database
        # If core.credit_products is unavailable, fallback to local excel/empty
        credit_products = []
        
        # Get client's current holdings to check for existing loan products
        holdings_query = """
        SELECT 
            product_type, security_name, investment_value_usd
        FROM core.client_holding 
        WHERE client_id = %s
        AND (product_type ILIKE %s OR product_type ILIKE %s OR security_name ILIKE %s)
        """
        existing_holdings = self._execute_query(holdings_query, (client_id, '%loan%', '%credit%', '%loan%'))
        
        total_volume = sum(float(t.get('transaction_amount', 0) or 0) for t in transactions)
        
        return json.dumps({
            "client_id": client_id,
            "client_segment": target_segment,
            "credit_transactions": [dict(t) for t in transactions] if transactions else [],
            "aedb_alerts": [dict(a) for a in aedb_alerts] if aedb_alerts else [],
            "available_credit_products": [dict(p) for p in credit_products] if credit_products else [],
            "existing_loan_holdings": [dict(h) for h in existing_holdings] if existing_holdings else [],
            "total_credit_volume": total_volume,
            "transaction_count": len(transactions) if transactions else 0,
            "products_count": len(credit_products) if credit_products else 0,
            "note": f"Credit products filtered for {target_segment} segment with risk-appropriate recommendations"
        }, indent=2, default=self._json_serializer)
    
    def get_elite_banking_casa_data(self, client_id: str) -> str:
        """Get banking and CASA data with 6-month deposit analysis"""
        # Get comprehensive portfolio balances
        portfolio_query = """
        SELECT 
            id, portfolio_id, client_id, portfolio_type, currency, 
            last_valuation_date, aum, investible_cash, deposits, 
            performing_loans, portfolio_return_since_inception,
            overall_xirr_since_inception, benchmark_1yr_return, 
            benchmark_xirr_since_inception, revenue_generated_ytd,
            net_interest_income_ytd, non_fund_income_ytd, 
            profile_market_price, has_high_potential, mandate_push,
            due_for_followup, asset_distribution, 
            fixed_income_subtype_distribution, equity_subtype_distribution,
            cash_and_market_subtype_distribution, 
            alternative_asset_subtype_distribution, last_update
        FROM core.client_portfolio 
        WHERE client_id = %s
        ORDER BY last_valuation_date DESC
        LIMIT 5
        """
        portfolio = self._execute_query(portfolio_query, (client_id,))

        # Compute portfolio allocation percentages if possible
        portfolio_allocation = {}
        allocation_source = "none"
        try:
            latest_portfolio = dict(portfolio[0]) if portfolio else {}
            asset_distribution = latest_portfolio.get('asset_distribution')
            if asset_distribution:
                # Attempt to parse JSON-like asset distribution
                parsed = None
                if isinstance(asset_distribution, dict):
                    parsed = asset_distribution
                elif isinstance(asset_distribution, str):
                    import json as _json
                    try:
                        parsed = _json.loads(asset_distribution)
                    except Exception:
                        parsed = None
                if isinstance(parsed, dict):
                    lower_map = {str(k).lower(): v for k, v in parsed.items()}
                    def pick(*names):
                        for n in names:
                            if n in lower_map:
                                return float(lower_map[n] or 0)
                        return 0.0
                    portfolio_allocation = {
                        "equities": pick('equities', 'equity'),
                        "fixed_income": pick('fixed_income', 'bonds', 'bond'),
                        "cash_casa": pick('cash', 'cash_and_money_market', 'money_market', 'casa'),
                        "alternatives": pick('alternatives', 'alternative'),
                    }
                    allocation_source = "asset_distribution"
            # Fallback using balances
            if not portfolio_allocation:
                aum = float(latest_portfolio.get('aum', 0) or 0)
                investible_cash = float(latest_portfolio.get('investible_cash', 0) or 0)
                deposits = float(latest_portfolio.get('deposits', 0) or 0)
                cash_total = investible_cash + deposits
                cash_pct = (cash_total / aum * 100) if aum > 0 else 0
                portfolio_allocation = {
                    "equities": 0.0,
                    "fixed_income": 0.0,
                    "cash_casa": cash_pct,
                    "alternatives": 0.0,
                }
                allocation_source = "computed_from_balances"
        except Exception:
            portfolio_allocation = {}
            allocation_source = "error"
        
        # Get banking transactions for last 6 months
        transactions_query = """
        SELECT 
            transaction_id, client_id, transaction_type, transaction_amount, 
            date, currency, booking_geography, name
        FROM core.client_transaction 
        WHERE client_id = %s AND transaction_type IN ('deposit', 'withdrawal', 'transfer')
        AND date >= CURRENT_DATE - INTERVAL '6 months'
        ORDER BY date DESC
        LIMIT 100
        """
        transactions = self._execute_query(transactions_query, (client_id,))
        
        # Define deposit/banking product categories (since no dedicated deposit table exists)
        deposit_product_categories = [
            {
                "product_type": "current_account",
                "product_name": "Current Account",
                "description": "Daily banking account for transactions, payments, and cash management",
                "interest_rate": "0% - 0.5%",
                "features": "Unlimited transactions, debit card, online banking, mobile app"
            },
            {
                "product_type": "savings_account",
                "product_name": "Savings Account",
                "description": "Interest-bearing account for short-term savings and emergency funds",
                "interest_rate": "1% - 3%",
                "features": "Limited transactions, higher interest, minimum balance requirements"
            },
            {
                "product_type": "fixed_deposit",
                "product_name": "Fixed Deposit",
                "description": "Term deposit with fixed interest rate and maturity period",
                "interest_rate": "2.5% - 5%",
                "features": "Fixed term (3-60 months), guaranteed returns, early withdrawal penalties"
            },
            {
                "product_type": "money_market_account",
                "product_name": "Money Market Account",
                "description": "High-yield account with check-writing privileges and higher interest rates",
                "interest_rate": "2% - 4%",
                "features": "Higher minimum balance, limited transactions, competitive rates"
            },
            {
                "product_type": "islamic_deposit",
                "product_name": "Islamic Deposit Account",
                "description": "Sharia-compliant deposit account based on profit-sharing principles",
                "interest_rate": "Profit-sharing (2% - 4%)",
                "features": "Sharia-compliant, profit-sharing instead of interest, ethical banking"
            }
        ]
        
        # Calculate 6-month deposit average
        deposit_transactions = [t for t in transactions if t.get('transaction_type') == 'deposit']
        monthly_deposits = {}
        
        for txn in deposit_transactions:
            date = txn.get('date')
            if date:
                # Handle both date objects and string dates
                if hasattr(date, 'year'):
                    month_key = f"{date.year}-{date.month:02d}"
                else:
                    # If it's a string, parse it
                    from datetime import datetime as dt
                    date_obj = dt.strptime(str(date), '%Y-%m-%d')
                    month_key = f"{date_obj.year}-{date_obj.month:02d}"
                amount = float(txn.get('transaction_amount', 0) or 0)
                if month_key not in monthly_deposits:
                    monthly_deposits[month_key] = 0
                monthly_deposits[month_key] += amount
        
        # Calculate average of last 6 months
        sorted_months = sorted(monthly_deposits.keys(), reverse=True)
        last_6_months = sorted_months[:6]
        six_month_deposits = [monthly_deposits.get(month, 0) for month in last_6_months]
        six_month_average = sum(six_month_deposits) / len(six_month_deposits) if six_month_deposits else 0
        
        # Get current month deposit
        from datetime import datetime as dt
        current_month = dt.now().strftime('%Y-%m')
        current_month_deposit = monthly_deposits.get(current_month, 0)
        
        # Determine focus based on comparison
        focus_recommendation = "investment"
        if current_month_deposit > six_month_average * 1.2:  # 20% higher than average
            focus_recommendation = "investment"
        elif current_month_deposit < six_month_average * 0.8:  # 20% lower than average
            focus_recommendation = "loan"
        
        total_balance = sum(float(p.get('aum', 0) or 0) for p in portfolio) if portfolio else 0
        
        return json.dumps({
            "client_id": client_id,
            "portfolio_balances": [dict(p) for p in portfolio] if portfolio else [],
            "banking_transactions": [dict(t) for t in transactions] if transactions else [],
            "available_deposit_products": deposit_product_categories,
            "total_balance": total_balance,
            "accounts_count": len(portfolio) if portfolio else 0,
            "portfolio_allocation": portfolio_allocation,
            "allocation_source": allocation_source,
            "casa_analysis": {
                "six_month_deposits": six_month_deposits,
                "six_month_average": six_month_average,
                "current_month_deposit": current_month_deposit,
                "current_month": current_month,
                "monthly_breakdown": monthly_deposits,
                "focus_recommendation": focus_recommendation,
                "comparison_ratio": current_month_deposit / six_month_average if six_month_average > 0 else 0,
                "deposit_trend": "increasing" if current_month_deposit > six_month_average else "decreasing"
            },
            "note": "Deposit products are categorized by type since no dedicated deposit product table exists in database"
        }, indent=2, default=self._json_serializer)
    
    def get_elite_spending_pattern_analysis(self, client_id: str) -> str:
        """Get comprehensive spending pattern analysis for product recommendations"""
        # Get transaction data from client_transaction table (existing table)
        query = """
        SELECT 
            transaction_id,
            client_id,
            date,
            transaction_type,
            transaction_amount,
            name,
            booking_geography,
            currency
        FROM core.client_transaction 
        WHERE client_id = %s
        ORDER BY date DESC
        LIMIT 100
        """
        transactions = self._execute_query(query, (client_id,))
        
        if not transactions:
            return json.dumps({
                "client_id": client_id,
                "spending_patterns": {},
                "product_recommendations": {},
                "insights": "No transaction data available for spending pattern analysis",
                "note": "Unable to analyze spending patterns due to lack of transaction data"
            }, indent=2, default=self._json_serializer)

        # Analyze transaction patterns by transaction_type and enhanced categorization
        investment_transactions = []
        deposit_transactions = []
        payment_transactions = []
        loan_transactions = []
        transfer_transactions = []
        withdrawal_transactions = []
        other_transactions = []

        for txn in transactions:
            txn_type = txn.get('transaction_type', '')
            amount = float(txn.get('transaction_amount', 0) or 0)
            date = txn.get('date', '')
            name = txn.get('name', '') or ''
            geography = txn.get('booking_geography', '')
            currency = txn.get('currency', '')

            transaction_data = {
                'amount': amount,
                'date': date,
                'name': name,
                'geography': geography,
                'currency': currency,
                'type': txn_type
            }

            # Enhanced categorization based on transaction_type and name patterns
            # This incorporates insights from the Excel transaction_history data
            if txn_type == 'BUY':
                # BUY transactions are typically investments
                investment_transactions.append(transaction_data)
            elif txn_type == 'SELL':
                # SELL transactions could be investment exits or withdrawals
                if 'investment' in name.lower() or 'fund' in name.lower():
                    investment_transactions.append(transaction_data)
                else:
                    withdrawal_transactions.append(transaction_data)
            elif 'deposit' in txn_type.lower() or 'deposit' in name.lower():
                deposit_transactions.append(transaction_data)
            elif 'payment' in txn_type.lower() or 'payment' in name.lower():
                if 'loan' in name.lower():
                    loan_transactions.append(transaction_data)
                else:
                    payment_transactions.append(transaction_data)
            elif 'loan' in txn_type.lower() or 'loan' in name.lower():
                loan_transactions.append(transaction_data)
            elif 'transfer' in txn_type.lower() or 'transfer' in name.lower():
                transfer_transactions.append(transaction_data)
            elif 'withdrawal' in txn_type.lower() or 'withdrawal' in name.lower():
                withdrawal_transactions.append(transaction_data)
            else:
                # Default categorization based on amount and patterns
                if amount > 0:
                    # Positive amounts could be deposits or investments
                    if amount > 10000:  # Large amounts likely investments
                        investment_transactions.append(transaction_data)
                    else:
                        deposit_transactions.append(transaction_data)
                else:
                    # Negative amounts could be payments or withdrawals
                    payment_transactions.append(transaction_data)
        
        # Calculate spending pattern metrics
        investment_total = sum(t['amount'] for t in investment_transactions)
        deposit_total = sum(t['amount'] for t in deposit_transactions)
        payment_total = sum(t['amount'] for t in payment_transactions)
        loan_total = sum(t['amount'] for t in loan_transactions)
        transfer_total = sum(t['amount'] for t in transfer_transactions)
        withdrawal_total = sum(t['amount'] for t in withdrawal_transactions)
        other_total = sum(t['amount'] for t in other_transactions)

        total_volume = investment_total + deposit_total + payment_total + loan_total + transfer_total + withdrawal_total + other_total
        
        # Calculate key ratios
        investment_ratio = investment_total / total_volume if total_volume > 0 else 0
        deposit_ratio = deposit_total / total_volume if total_volume > 0 else 0
        payment_ratio = payment_total / total_volume if total_volume > 0 else 0
        loan_ratio = loan_total / total_volume if total_volume > 0 else 0

        # Determine spending pattern profile based on transaction types
        spending_profile = "Unknown"
        if investment_ratio > 0.3:
            spending_profile = "Investment-Focused"
        elif deposit_ratio > 0.3:
            spending_profile = "Deposit-Heavy"
        elif payment_ratio > 0.3:
            spending_profile = "Payment-Active"
        elif loan_ratio > 0.2:
            spending_profile = "Loan-Active"
        else:
            spending_profile = "Balanced"

        # Add frequency indicators
        total_transactions = len(transactions)
        if total_transactions > 50:
            spending_profile += " - High Frequency"
        elif total_transactions > 20:
            spending_profile += " - Moderate Frequency"
        else:
            spending_profile += " - Low Frequency"
        
        # Generate product recommendations based on transaction patterns
        investment_recommendations = []
        loan_recommendations = []
        banking_recommendations = []
        insurance_recommendations = []

        # Investment recommendations based on transaction patterns
        if investment_ratio > 0.2:
            investment_recommendations.extend([
                "PIMCO GIS Income Fund E Class USD Income",
                "Systematic Investment Plans (SIPs)",
                "Dollar-Cost Averaging strategies",
                "Long-term growth funds",
                "Retirement planning products"
            ])
            
            if len(investment_transactions) > 10:
                investment_recommendations.extend([
                    "Trading platforms and tools",
                    "Market research services",
                    "Risk management products",
                    "Real-time market data"
                ])

        # Loan recommendations based on loan transaction patterns
        if loan_ratio > 0.1 or len(loan_transactions) > 0:
            loan_recommendations.extend([
                "Home Loan - First Time Buyer (conservative approach)",
                "Auto Loan - New Vehicle (based on age and income)",
                "Personal Loan - Standard (for liquidity needs)",
                "Education Loan - Domestic (if applicable)"
            ])
            
            if loan_total > 100000:  # High loan volume
                loan_recommendations.append("Investment Property Loan (based on high loan volume)")

        # Banking recommendations based on deposit and payment patterns
        if deposit_ratio > 0.2:
            banking_recommendations.extend([
                "Premium Savings Account (high deposit activity)",
                "Money Market Account (competitive rates)",
                "Fixed Deposit (conservative approach)",
                "Islamic Deposit Account (if preferred)"
            ])
        
        if payment_ratio > 0.2:
            banking_recommendations.extend([
                "Current Account (high payment activity)",
                "Business Banking Account (if applicable)",
                "Digital Banking Services",
                "Mobile Payment Solutions"
            ])

        # Transfer-based recommendations
        if len(transfer_transactions) > 5:
            banking_recommendations.extend([
                "International Transfer Services",
                "Currency Exchange Services",
                "Multi-Currency Account",
                "Wire Transfer Services"
            ])

        # Insurance recommendations based on transaction patterns
        insurance_recommendations.extend([
            "Life Insurance (pre-retirement planning)",
            "Health Insurance (age-appropriate)",
            "Long-term Care Insurance",
            "Property Insurance (if applicable)"
        ])

        # Enhanced merchant/name-based recommendations using available data
        transaction_names = [txn.get('name', '') for txn in transactions if txn.get('name')]
        unique_names = list(set(transaction_names))
        
        # Analyze transaction names for patterns (similar to merchant analysis)
        if any('car' in name.lower() or 'auto' in name.lower() or 'vehicle' in name.lower() for name in unique_names):
            loan_recommendations.append("Auto Loan - Vehicle Purchase/Upgrade")
            insurance_recommendations.append("Auto Insurance")
        
        if any('school' in name.lower() or 'college' in name.lower() or 'education' in name.lower() or 'university' in name.lower() for name in unique_names):
            loan_recommendations.append("Education Loan - Academic Expenses")
            investment_recommendations.append("Education Savings Plan")
        
        # Analyze geography patterns
        geographies = [txn.get('geography', '') for txn in transactions if txn.get('geography')]
        unique_geographies = list(set(geographies))
        
        if len(unique_geographies) > 1:
            banking_recommendations.append("Multi-Currency Account (international transactions detected)")
            banking_recommendations.append("International Transfer Services")

        # High-value client recommendations
        premium_services = []
        if total_volume > 1000000:  # High transaction volume
            premium_services.extend([
                "Private banking services",
                "Exclusive investment opportunities",
                "Personalized wealth management",
                "Premium banking products",
                "Dedicated relationship manager services",
                "Concierge banking services",
                "Priority customer support"
            ])
        
        return json.dumps({
            "client_id": client_id,
            "spending_patterns": {
                "profile": spending_profile,
                "transaction_breakdown": {
                    "investment_transactions": {
                        "count": len(investment_transactions),
                        "total_amount": investment_total,
                        "avg_amount": investment_total / len(investment_transactions) if investment_transactions else 0,
                        "ratio": investment_ratio
                    },
                    "deposit_transactions": {
                        "count": len(deposit_transactions),
                        "total_amount": deposit_total,
                        "avg_amount": deposit_total / len(deposit_transactions) if deposit_transactions else 0,
                        "ratio": deposit_ratio
                    },
                    "payment_transactions": {
                        "count": len(payment_transactions),
                        "total_amount": payment_total,
                        "avg_amount": payment_total / len(payment_transactions) if payment_transactions else 0,
                        "ratio": payment_ratio
                    },
                    "loan_transactions": {
                        "count": len(loan_transactions),
                        "total_amount": loan_total,
                        "avg_amount": loan_total / len(loan_transactions) if loan_transactions else 0,
                        "ratio": loan_ratio
                    },
                    "transfer_transactions": {
                        "count": len(transfer_transactions),
                        "total_amount": transfer_total,
                        "avg_amount": transfer_total / len(transfer_transactions) if transfer_transactions else 0
                    },
                    "withdrawal_transactions": {
                        "count": len(withdrawal_transactions),
                        "total_amount": withdrawal_total,
                        "avg_amount": withdrawal_total / len(withdrawal_transactions) if withdrawal_transactions else 0
                    },
                    "other_transactions": {
                        "count": len(other_transactions),
                        "total_amount": other_total
                    }
                },
                "transaction_metrics": {
                    "total_volume": total_volume,
                    "total_transactions": total_transactions,
                    "unique_transaction_names": len(unique_names),
                    "top_transaction_names": list(set(transaction_names))[:5] if transaction_names else [],
                    "unique_geographies": len(unique_geographies),
                    "geographies": unique_geographies
                }
            },
            "product_recommendations": {
                "investment_products": investment_recommendations,
                "loan_products": loan_recommendations,
                "banking_products": banking_recommendations,
                "insurance_products": insurance_recommendations,
                "premium_services": premium_services
            },
            "insights": {
                "behavior_analysis": f"Client shows {spending_profile.lower()} behavior with {len(investment_transactions)} investment transactions, {len(deposit_transactions)} deposits, and {len(payment_transactions)} payments",
                "transaction_focus": f"Primary transaction focus: {max([('investment', investment_ratio), ('deposit', deposit_ratio), ('payment', payment_ratio), ('loan', loan_ratio)], key=lambda x: x[1])[0]}",
                "transaction_name_insights": f"Active with {len(unique_names)} different transaction types, indicating diverse financial activities",
                "geography_insights": f"Transactions across {len(unique_geographies)} geographies: {', '.join(unique_geographies)}",
                "relationship_opportunity": f"High transaction volume ({total_volume:,.0f}) indicates active financial management requiring personalized service"
            },
            "note": "Enhanced spending pattern analysis based on client_transaction table with intelligent categorization incorporating insights from transaction_history Excel data"
        }, indent=2, default=self._json_serializer)

    def get_elite_risk_compliance_data(self, client_id: str) -> str:
        """Get risk and compliance data including AEDB alerts focusing on specific products"""
        # Get AEDB alerts (using risk data)
        risk_query = """
        SELECT 
            client_id, risk_name, risk_level, match_diff_from_house_rec
        FROM core.client_holdings_risk_level 
        WHERE client_id = %s
        ORDER BY risk_level DESC
        LIMIT 20
        """
        risk_alerts = self._execute_query(risk_query, (client_id,))
        
        # Get complaints
        complaints_query = """
        SELECT 
            comm_log_id, client_id, type, subtype, description, status, communication_date
        FROM core.communication_log 
        WHERE client_id = %s AND type = 'complaint'
        ORDER BY communication_date DESC
        LIMIT 10
        """
        complaints = self._execute_query(complaints_query, (client_id,))
        
        # Get risk level definitions
        definitions_query = """
        SELECT 
            name, level, segment, last_updated
        FROM core.risk_level_definition 
        ORDER BY level
        """
        definitions = self._execute_query(definitions_query)
        
        # Focus on the HIGHEST priority AEDB alert for specific product recommendation
        top_alert = risk_alerts[0] if risk_alerts else None
        
        # Determine product focus based on alert type
        focus_product = "No specific product"
        product_category = "general"
        if top_alert:
            risk_name = top_alert.get('risk_name', '').lower()
            if 'auto' in risk_name or 'vehicle' in risk_name or 'car' in risk_name:
                focus_product = "Auto Loan Products"
                product_category = "auto_loan"
            elif 'home' in risk_name or 'property' in risk_name or 'mortgage' in risk_name:
                focus_product = "Home Loan Products"
                product_category = "home_loan"
            elif 'personal' in risk_name or 'unsecured' in risk_name:
                focus_product = "Personal Loan Products"
                product_category = "personal_loan"
            elif 'credit' in risk_name or 'card' in risk_name:
                focus_product = "Credit Card Products"
                product_category = "credit_card"
            elif 'investment' in risk_name or 'fund' in risk_name:
                focus_product = "Investment Products"
                product_category = "investment"
            else:
                focus_product = f"Products related to {top_alert.get('risk_name', 'general risk')}"
                product_category = "general"
        
        return json.dumps({
            "client_id": client_id,
            "focus_alert": top_alert,  # Single alert to focus on
            "focus_product": focus_product,  # Specific product to focus on
            "product_category": product_category,
            "alert_risk_name": top_alert.get('risk_name') if top_alert else "No alerts",
            "alert_risk_level": top_alert.get('risk_level') if top_alert else 0,
            "alert_match_diff": top_alert.get('match_diff_from_house_rec') if top_alert else 0,
            "all_aedb_alerts": [dict(r) for r in risk_alerts] if risk_alerts else [],
            "complaints": [dict(c) for c in complaints] if complaints else [],
            "risk_definitions": [dict(d) for d in definitions] if definitions else [],
            "total_alerts": len(risk_alerts),
            "active_complaints": len(complaints),
            "has_high_priority_alert": top_alert is not None and top_alert.get('risk_level', 0) > 3
        }, indent=2, default=self._json_serializer)
    
    def get_elite_share_of_potential(self, client_id: str) -> str:
        """Get Share of Potential analysis using ML algorithm data"""
        # Get ML Share of Potential data (without rm_id to avoid schema mismatch)
        ml_potential_query = """
        SELECT 
            client_id, has_high_potential, mandate_push
        FROM core.client_high_potential_and_mandate_push 
        WHERE client_id = %s
        """
        ml_potential = self._execute_query(ml_potential_query, (client_id,))
        
        # Get ML asset recommendations
        asset_recommendations_query = """
        SELECT 
            client_id, risk_appetite, segment_name, 
            fixed_income, equities, cash_and_money_market, alternatives,
            recommended_fixed_income, recommended_equities, 
            recommended_cash_and_money_market, recommended_alternatives
        FROM core.client_asset_recommendation 
        WHERE client_id = %s
        LIMIT 1
        """
        asset_recommendations = self._execute_query(asset_recommendations_query, (client_id,))
        
        # Get client holdings for current value calculation
        holdings_query = """
        SELECT 
            product_type, security_name, investment_value_usd, asset_class
        FROM core.client_holding 
        WHERE client_id = %s
        ORDER BY investment_value_usd DESC
        LIMIT 20
        """
        holdings = self._execute_query(holdings_query, (client_id,))
        
        # Get available products for potential calculation
        products_query = """
        SELECT 
            id, name, investment_objective, total_net_assets, 
            annualized_return_3y, annualized_return_5y, morningstar_rating
        FROM core.funds
        ORDER BY total_net_assets DESC
        LIMIT 30
        """
        products = self._execute_query(products_query)
        
        # Calculate current portfolio value
        current_portfolio_value = sum(float(h.get('investment_value_usd', 0) or 0) for h in holdings)
        
        # Get client's current product types
        current_product_types = set(h.get('product_type', '') for h in holdings)
        current_asset_classes = set(h.get('asset_class', '') for h in holdings)
        
        # Create Share of Potential analysis based on ML data
        prioritized_products = []
        for product in products:
            product_name = product.get('name', '')
            investment_objective = product.get('investment_objective', '')
            total_net_assets = product.get('total_net_assets', '0')
            
            # Parse potential value
            if total_net_assets and isinstance(total_net_assets, str):
                import re
                numbers = re.findall(r'[\d,]+\.?\d*', total_net_assets)
                if numbers:
                    potential_value = float(numbers[-1].replace(',', ''))
                else:
                    potential_value = 0
            else:
                potential_value = float(total_net_assets or 0)
            
            # Calculate current value
            current_value = 0
            for holding in holdings:
                security_name = holding.get('security_name', '') or ''
                if security_name and product_name and security_name.lower() in product_name.lower():
                    current_value = float(holding.get('investment_value_usd', 0) or 0)
                    break
            
            # Calculate share of potential (monetary amount of more business)
            share_of_potential = potential_value - current_value
            
            # Determine product category
            product_category = "unknown"
            if investment_objective and isinstance(investment_objective, str):
                investment_objective_lower = investment_objective.lower()
                if any(keyword in investment_objective_lower for keyword in ['equity', 'stock', 'share']):
                    product_category = "equity"
                elif any(keyword in investment_objective_lower for keyword in ['bond', 'fixed income', 'debt']):
                    product_category = "fixed_income"
                elif any(keyword in investment_objective_lower for keyword in ['money market', 'cash', 'liquidity']):
                    product_category = "money_market"
                elif any(keyword in investment_objective_lower for keyword in ['islamic', 'sharia']):
                    product_category = "islamic"
            
            if share_of_potential > 0:
                prioritized_products.append({
                    "product_id": product.get('id'),
                    "product_name": product_name,
                    "investment_objective": investment_objective,
                    "product_category": product_category,
                    "band_median": potential_value,
                    "current_value": current_value,
                    "share_of_potential": share_of_potential,
                    "annualized_return_3y": product.get('annualized_return_3y'),
                    "annualized_return_5y": product.get('annualized_return_5y'),
                    "morningstar_rating": product.get('morningstar_rating'),
                    "is_new_category": product_category not in current_asset_classes,
                    "priority_score": share_of_potential * (1.5 if product_category not in current_asset_classes else 1.0)
                })
        
        # Sort by priority score
        prioritized_products.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Focus on the TOP product with highest share of potential
        top_product = prioritized_products[0] if prioritized_products else None
        
        # Calculate total potential value (monetary amount of more business)
        total_potential_value = sum(p['share_of_potential'] for p in prioritized_products)
        
        return json.dumps({
            "client_id": client_id,
            "ml_analysis": {
                "has_high_potential": ml_potential[0].get('has_high_potential') if ml_potential else False,
                "mandate_push": ml_potential[0].get('mandate_push') if ml_potential else False,
                "assigned_rm": None,
                "total_potential_value": total_potential_value,
                "current_portfolio_value": current_portfolio_value
            },
            "focus_product": top_product,  # Single product to focus on
            "product_name": top_product.get('product_name') if top_product else "No products available",
            "share_of_potential": top_product.get('share_of_potential') if top_product else 0,
            "priority_score": top_product.get('priority_score') if top_product else 0,
            "investment_objective": top_product.get('investment_objective') if top_product else "N/A",
            "product_category": top_product.get('product_category') if top_product else "N/A",
            "current_value": top_product.get('current_value') if top_product else 0,
            "band_median": top_product.get('band_median') if top_product else 0,
            "annualized_return_3y": top_product.get('annualized_return_3y') if top_product else "N/A",
            "annualized_return_5y": top_product.get('annualized_return_5y') if top_product else "N/A",
            "morningstar_rating": top_product.get('morningstar_rating') if top_product else "N/A",
            "ml_asset_recommendations": dict(asset_recommendations[0]) if asset_recommendations else {},
            "all_prioritized_products": prioritized_products[:5],  # Keep top 5 for reference
            "current_holdings_count": len(holdings),
            "current_product_types": list(current_product_types),
            "current_asset_classes": list(current_asset_classes),
            "analysis_summary": {
                "top_opportunity": top_product,
                "new_categories_available": len([p for p in prioritized_products if p['is_new_category']]),
                "total_opportunity_value": sum(p['share_of_potential'] for p in prioritized_products[:5]),
                "ml_high_potential_flag": ml_potential[0].get('has_high_potential') if ml_potential else False,
                "ml_mandate_push_flag": ml_potential[0].get('mandate_push') if ml_potential else False
            }
        }, indent=2, default=self._json_serializer)
    
    def get_elite_client_behavior_analysis(self, client_id: str) -> str:
        """Analyze client transaction patterns for product recommendations"""
        # Get all client transactions
        transactions_query = """
        SELECT 
            transaction_id, transaction_type, transaction_amount, 
            date, currency, booking_geography, name
        FROM core.client_transaction 
        WHERE client_id = %s
        ORDER BY date DESC
        LIMIT 100
        """
        transactions = self._execute_query(transactions_query, (client_id,))
        
        # Get client portfolio changes
        portfolio_query = """
        SELECT 
            client_id, aum, investible_cash, deposits, performing_loans,
            portfolio_return_since_inception, last_valuation_date
        FROM core.client_portfolio 
        WHERE client_id = %s
        ORDER BY last_valuation_date DESC
        LIMIT 5
        """
        portfolio = self._execute_query(portfolio_query, (client_id,))
        
        # Analyze transaction patterns
        transaction_analysis = {
            "total_transactions": len(transactions),
            "transaction_types": {},
            "monthly_patterns": {},
            "geographic_patterns": {},
            "amount_patterns": {},
            "product_interest_indicators": []
        }
        
        # Analyze transaction types and amounts
        for txn in transactions:
            txn_type = txn.get('transaction_type', 'unknown')
            amount = float(txn.get('transaction_amount', 0) or 0)
            date = txn.get('date')
            geography = txn.get('booking_geography', 'unknown')
            description = txn.get('name', '') or ''
            description = description.lower() if description else ''
            
            # Count transaction types
            if txn_type not in transaction_analysis["transaction_types"]:
                transaction_analysis["transaction_types"][txn_type] = {"count": 0, "total_amount": 0}
            transaction_analysis["transaction_types"][txn_type]["count"] += 1
            transaction_analysis["transaction_types"][txn_type]["total_amount"] += amount
            
            # Geographic patterns
            if geography not in transaction_analysis["geographic_patterns"]:
                transaction_analysis["geographic_patterns"][geography] = 0
            transaction_analysis["geographic_patterns"][geography] += 1
            
            # Product interest indicators based on transaction descriptions
            if any(keyword in description for keyword in ['auto', 'car', 'vehicle', 'automobile']):
                transaction_analysis["product_interest_indicators"].append({
                    "product": "auto_loan",
                    "indicator": "auto_related_transaction",
                    "description": description,
                    "amount": amount,
                    "date": date
                })
            elif any(keyword in description for keyword in ['home', 'house', 'property', 'real estate', 'mortgage']):
                transaction_analysis["product_interest_indicators"].append({
                    "product": "home_loan",
                    "indicator": "property_related_transaction",
                    "description": description,
                    "amount": amount,
                    "date": date
                })
            elif any(keyword in description for keyword in ['education', 'school', 'university', 'tuition']):
                transaction_analysis["product_interest_indicators"].append({
                    "product": "education_loan",
                    "indicator": "education_related_transaction",
                    "description": description,
                    "amount": amount,
                    "date": date
                })
            elif any(keyword in description for keyword in ['investment', 'fund', 'equity', 'bond']):
                transaction_analysis["product_interest_indicators"].append({
                    "product": "investment_products",
                    "indicator": "investment_related_transaction",
                    "description": description,
                    "amount": amount,
                    "date": date
                })
        
        # Analyze CASA balance changes
        casa_analysis = {
            "current_balance": 0,
            "balance_trend": "stable",
            "liquidity_indicators": []
        }
        
        if portfolio:
            latest_portfolio = portfolio[0]
            casa_analysis["current_balance"] = float(latest_portfolio.get('investible_cash', 0) or 0)
            
            # Calculate trend if multiple portfolio records
            if len(portfolio) > 1:
                current_cash = float(latest_portfolio.get('investible_cash', 0) or 0)
                previous_cash = float(portfolio[1].get('investible_cash', 0) or 0)
                if current_cash > previous_cash * 1.1:
                    casa_analysis["balance_trend"] = "increasing"
                elif current_cash < previous_cash * 0.9:
                    casa_analysis["balance_trend"] = "decreasing"
        
        return json.dumps({
            "client_id": client_id,
            "transaction_analysis": transaction_analysis,
            "casa_analysis": casa_analysis,
            "portfolio_summary": [dict(p) for p in portfolio[:3]],
            "recommendation_insights": {
                "high_interest_products": list(set([ind["product"] for ind in transaction_analysis["product_interest_indicators"]])),
                "transaction_volume": sum(t["total_amount"] for t in transaction_analysis["transaction_types"].values()),
                "geographic_diversity": len(transaction_analysis["geographic_patterns"]),
                "liquidity_status": casa_analysis["balance_trend"]
            }
        }, indent=2, default=self._json_serializer)
    
    def get_elite_rm_strategy(self, client_id: str) -> str:
        """Get RM information and develop conversation strategy"""
        # Get assigned RM from ML data
        rm_assignment_query = """
        SELECT 
            client_id, has_high_potential, mandate_push
        FROM core.client_high_potential_and_mandate_push 
        WHERE client_id = %s
        LIMIT 1
        """
        rm_assignment = self._execute_query(rm_assignment_query, (client_id,))
        
        assigned_rm_id = None
        
        # Get specific RM portfolio information
        rm_query = """
        SELECT 
            rm_id, first_name, last_name, advisory_client_count,
            total_ntb_clients_ytd, aum_total, aum_dpm
        FROM core.rm_portfolio 
        WHERE rm_id = %s
        """
        rm_data = self._execute_query(rm_query, (assigned_rm_id,)) if assigned_rm_id else []
        
        # Get communication history
        comm_query = """
        SELECT 
            comm_log_id, client_id, type, subtype, description, 
            status, communication_date, communication_source
        FROM core.communication_log 
        WHERE client_id = %s
        ORDER BY communication_date DESC
        LIMIT 20
        """
        comm_history = self._execute_query(comm_query, (client_id,))
        
        # Get client context for RM strategy
        client_query = """
        SELECT 
            client_id, first_name, last_name, age, income, tenure,
            risk_appetite, customer_profile_banking_segment
        FROM core.client_context 
        WHERE client_id = %s
        LIMIT 1
        """
        client_data = self._execute_query(client_query, (client_id,))
        
        # Analyze communication patterns
        comm_analysis = {
            "total_communications": len(comm_history),
            "communication_types": {},
            "recent_activity": [],
            "preferred_channels": {},
            "complaint_history": []
        }
        
        for comm in comm_history:
            comm_type = comm.get('type', 'unknown')
            channel = comm.get('communication_source', 'unknown')
            status = comm.get('status', 'unknown')
            
            # Count communication types
            if comm_type not in comm_analysis["communication_types"]:
                comm_analysis["communication_types"][comm_type] = 0
            comm_analysis["communication_types"][comm_type] += 1
            
            # Count channels
            if channel not in comm_analysis["preferred_channels"]:
                comm_analysis["preferred_channels"][channel] = 0
            comm_analysis["preferred_channels"][channel] += 1
            
            # Track complaints
            if comm_type == 'complaint':
                comm_analysis["complaint_history"].append({
                    "description": comm.get('description'),
                    "status": status,
                    "date": comm.get('communication_date')
                })
            
            # Recent activity (last 5)
            if len(comm_analysis["recent_activity"]) < 5:
                comm_analysis["recent_activity"].append({
                    "type": comm_type,
                    "subtype": comm.get('subtype'),
                    "date": comm.get('communication_date'),
                    "status": status
                })
        
        # Develop RM conversation strategy
        rm_strategy = {
            "rm_id": rm_data[0].get('rm_id') if rm_data else "Not Assigned",
            "rm_name": f"{rm_data[0].get('first_name', '')} {rm_data[0].get('last_name', '')}".strip() if rm_data else "Not Assigned",
            "rm_aum_total": float(rm_data[0].get('aum_total', 0) or 0) if rm_data else 0,
            "rm_advisory_clients": rm_data[0].get('advisory_client_count', 0) if rm_data else 0,
            "conversation_approach": "professional",
            "key_talking_points": [],
            "product_priorities": [],
            "risk_considerations": [],
            "follow_up_strategy": "standard"
        }
        
        # Determine conversation approach based on client profile
        if client_data:
            client = client_data[0]
            age = client.get('age', 0)
            income = float(client.get('income', 0) or 0)
            risk_appetite = client.get('risk_appetite', '')
            segment = client.get('customer_profile_banking_segment', '')
            
            # Adjust approach based on client characteristics
            if age > 50:
                rm_strategy["conversation_approach"] = "conservative_focused"
                rm_strategy["key_talking_points"].append("Retirement planning and wealth preservation")
            elif age < 35:
                rm_strategy["conversation_approach"] = "growth_focused"
                rm_strategy["key_talking_points"].append("Long-term wealth building and investment growth")
            
            if income > 1000000:  # High income
                rm_strategy["key_talking_points"].append("Premium banking services and exclusive products")
                rm_strategy["follow_up_strategy"] = "high_touch"
            
            if risk_appetite in ['R4', 'R5']:
                rm_strategy["key_talking_points"].append("High-yield investment opportunities")
                rm_strategy["risk_considerations"].append("Client has high risk tolerance - suitable for aggressive strategies")
            elif risk_appetite in ['R1', 'R2']:
                rm_strategy["key_talking_points"].append("Capital preservation and stable returns")
                rm_strategy["risk_considerations"].append("Client prefers conservative approach - focus on low-risk products")
        
        # Add product priorities based on communication history
        if comm_analysis["complaint_history"]:
            rm_strategy["key_talking_points"].append("Address previous concerns and improve service quality")
            rm_strategy["follow_up_strategy"] = "recovery_focused"
        
        return json.dumps({
            "client_id": client_id,
            "rm_information": rm_strategy,
            "communication_analysis": comm_analysis,
            "client_profile": dict(client_data[0]) if client_data else {},
            "strategy_recommendations": {
                "conversation_tone": rm_strategy["conversation_approach"],
                "primary_focus": rm_strategy["key_talking_points"][0] if rm_strategy["key_talking_points"] else "General financial planning",
                "follow_up_frequency": "Weekly" if rm_strategy["follow_up_strategy"] == "high_touch" else "Monthly",
                "risk_level": "High" if "aggressive" in rm_strategy["conversation_approach"] else "Moderate"
            }
        }, indent=2, default=self._json_serializer)

# ----------------------------
# Initialize Database Manager
# ----------------------------
db_manager = EliteDatabaseManager()

# ----------------------------
# Tool Functions
# ----------------------------
@function_tool
def get_elite_client_data(client_id: str) -> str:
    """Get comprehensive client profile data for elite analysis"""
    return db_manager.get_elite_client_data(client_id)

@function_tool
def get_elite_investment_data(client_id: str) -> str:
    """Get investment data including holdings and available funds"""
    return db_manager.get_elite_investment_data(client_id)

@function_tool
def get_elite_loan_data(client_id: str) -> str:
    """Get loan and credit data including transactions and products"""
    return db_manager.get_elite_loan_data(client_id)

@function_tool
def get_elite_banking_casa_data(client_id: str) -> str:
    """Get banking and CASA data including balances and transactions"""
    return db_manager.get_elite_banking_casa_data(client_id)

@function_tool
def get_elite_risk_compliance_data(client_id: str) -> str:
    """Get risk and compliance data including AEDB alerts"""
    return db_manager.get_elite_risk_compliance_data(client_id)

@function_tool
def get_elite_share_of_potential(client_id: str) -> str:
    """Get Share of Potential analysis for upsell opportunities"""
    return db_manager.get_elite_share_of_potential(client_id)

@function_tool
def get_elite_client_behavior_analysis(client_id: str) -> str:
    """Analyze client transaction patterns and behavior for product recommendations"""
    return db_manager.get_elite_client_behavior_analysis(client_id)

@function_tool
def get_elite_rm_strategy(client_id: str) -> str:
    """Get RM information and develop conversation strategy"""
    return db_manager.get_elite_rm_strategy(client_id)

@function_tool
def get_elite_engagement_analysis(client_id: str) -> str:
    """Get comprehensive engagement analysis and communication insights"""
    return db_manager.get_elite_engagement_analysis(client_id)

@function_tool
def get_elite_communication_history(client_id: str) -> str:
    """Get detailed communication history and RM interaction patterns"""
    return db_manager.get_elite_communication_history(client_id)

@function_tool
def get_elite_spending_pattern_analysis(client_id: str) -> str:
    """Get comprehensive spending pattern analysis for product recommendations"""
    return db_manager.get_elite_spending_pattern_analysis(client_id)

# ----------------------------
# Agent Creation
# ----------------------------
def create_elite_agents() -> Dict[str, Agent]:
    """Create all Elite agents with their tools"""
    
    # Load model from environment
    load_dotenv()
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # Manager Agent - Enhanced with all tools for comprehensive analysis
    manager = Agent(
        name="Elite_Manager",
        instructions=ELITE_MANAGER_AGENT_PROMPT,
        tools=[
            get_elite_client_data, 
            get_elite_share_of_potential,
            get_elite_client_behavior_analysis,
            get_elite_rm_strategy,
            get_elite_risk_compliance_data,
            get_elite_engagement_analysis,
            get_elite_communication_history,
            get_elite_spending_pattern_analysis
        ],
        model=model,
    )
    
    # Investment Agent - Focused on investment analysis only
    investment = Agent(
        name="Elite_Investment_Expert",
        instructions=ELITE_INVESTMENT_AGENT_PROMPT_UPDATED,
        tools=[
            get_elite_investment_data, 
            get_elite_client_data,
            get_elite_share_of_potential,
            get_elite_client_behavior_analysis
        ],
        model=model,
    )
    
    # Loan Agent - Focused on loan analysis only
    loan = Agent(
        name="Elite_Loan_Expert",
        instructions=ELITE_LOAN_AGENT_PROMPT_UPDATED,
        tools=[
            get_elite_loan_data, 
            get_elite_client_data,
            get_elite_client_behavior_analysis,
            get_elite_risk_compliance_data
        ],
        model=model,
    )
    
    # BankingCASA Agent - Focused on banking analysis only
    banking_casa = Agent(
        name="Elite_BankingCASA_Expert",
        instructions=ELITE_BANKING_CASA_AGENT_PROMPT_UPDATED,
        tools=[
            get_elite_banking_casa_data, 
            get_elite_client_data,
            get_elite_client_behavior_analysis
        ],
        model=model,
    )
    
    # Risk & Compliance Agent - Focused on risk analysis only
    risk_compliance = Agent(
        name="Elite_Risk_Compliance_Expert",
        instructions=ELITE_RISK_COMPLIANCE_AGENT_PROMPT_UPDATED,
        tools=[
            get_elite_risk_compliance_data, 
            get_elite_client_data,
            get_elite_client_behavior_analysis
        ],
        model=model,
    )
    
    return {
        "manager": manager,
        "investment": investment,
        "loan": loan,
        "banking_casa": banking_casa,
        "risk_compliance": risk_compliance,
    }

# ----------------------------
# Main Execution
# ----------------------------
def run_individual_agent_analysis(agents: Dict[str, Agent], client_id: str, consolidated_log_file) -> Dict[str, str]:
    """Run individual agent analyses and log responses"""
    agent_responses = {}
    
    # Define analysis requests for each agent
    agent_requests = {
        "investment": f"Analyze investment opportunities for client {client_id}. Focus on Share of Potential, current holdings, and behavior-based recommendations.",
        "loan": f"Analyze loan and credit opportunities for client {client_id}. Consider transaction patterns, CASA balance changes, and AEDB alerts for auto loans, home loans, etc.",
        "banking_casa": f"Analyze banking and CASA opportunities for client {client_id}. Focus on balance trends, transaction patterns, and liquidity management.",
        "risk_compliance": f"Analyze risk and compliance for client {client_id}. Review AEDB alerts, complaints, and risk appetite alignment."
    }
    
    for agent_name, request in agent_requests.items():
        try:
            print(f"\n🔍 Running {agent_name.replace('_', ' ').title()} Analysis...")
            print(f"Request: {request}")
            print("-" * 80)
            
            # Log to consolidated file
            consolidated_log_file.write(f"\n{'='*80}\n")
            consolidated_log_file.write(f"=== {agent_name.replace('_', ' ').title()} Analysis for Client {client_id} ===\n")
            consolidated_log_file.write(f"Timestamp: {datetime.now()}\n")
            consolidated_log_file.write(f"Request: {request}\n")
            consolidated_log_file.write(f"{'='*80}\n")
            consolidated_log_file.flush()
            
            logger.info(f"Starting {agent_name} analysis for client {client_id}")
            
            result = Runner.run_sync(
                starting_agent=agents[agent_name],
                input=request,
                max_turns=5
            )
            
            agent_responses[agent_name] = result.final_output
            
            # Print response to console
            print(f"\n📋 {agent_name.replace('_', ' ').title()} Response:")
            print("=" * 60)
            print(result.final_output)
            print("=" * 60)
            print()  # Add extra line for better separation
            
            # Log response to consolidated file
            consolidated_log_file.write(f"\nResponse:\n{result.final_output}\n")
            consolidated_log_file.flush()
            
            logger.info(f"✅ {agent_name} analysis completed")
            print(f"✅ {agent_name.replace('_', ' ').title()} Analysis completed")
            
        except Exception as e:
            error_msg = f"❌ Error in {agent_name} analysis: {e}"
            print(error_msg)
            print("=" * 60)
            
            # Log error to consolidated file
            consolidated_log_file.write(f"\nERROR: {error_msg}\n")
            consolidated_log_file.flush()
            
            logger.error(error_msg)
            agent_responses[agent_name] = f"Error: {e}"
    
    return agent_responses

def run_manager_context_setting(agents: Dict[str, Agent], client_id: str, consolidated_log_file) -> str:
    """Run Manager Agent to set comprehensive client context"""
    try:
        print(f"\n🎯 STEP 1: Manager Context Setting")
        print("-" * 40)
        print(f"Setting comprehensive context for client {client_id}...")
        print("-" * 80)
        
        # Log to consolidated file
        consolidated_log_file.write(f"\n{'='*80}\n")
        consolidated_log_file.write(f"=== MANAGER CONTEXT SETTING for Client {client_id} ===\n")
        consolidated_log_file.write(f"Timestamp: {datetime.now()}\n")
        consolidated_log_file.write(f"{'='*80}\n")
        consolidated_log_file.flush()
        
        context_request = f"""
               As the Elite Manager, please set the comprehensive context for client {client_id} by providing:

               1. **CLIENT PROFILE SUMMARY**:
                  - Retrieve and summarize client demographics, income, risk appetite, banking segment, and relationship details
                  - Include age, income level, risk appetite (R1-R5), client tier, and relationship strength

               2. **INVESTMENT HOLDINGS OVERVIEW**:
                  - Current investment portfolio composition and total value
                  - Asset class distribution (equity, fixed income, alternatives, cash)
                  - Top holdings by value and performance

               3. **LOAN PRODUCT OPPORTUNITIES**:
                  - Available credit products suitable for client's segment and risk profile
                  - Key loan products with rates, terms, and eligibility criteria
                  - AEDB alerts indicating loan interest or inquiries

               4. **CASA BALANCE ANALYSIS**:
                  - Current CASA balance and trend analysis
                  - 6-month deposit patterns and liquidity status
                  - Banking transaction volume and patterns

               5. **COMPREHENSIVE SPENDING PATTERN ANALYSIS**:
                  - Detailed transaction pattern analysis using spending analytics
                  - Transaction breakdown by type (investment, deposit, payment, loan, transfer, withdrawal)
                  - Spending profile classification (e.g., "Investment-Focused - High Frequency")
                  - Transaction volume, frequency, and geographic patterns
                  - Merchant/transaction name analysis for specific spending categories
                  - Product recommendations based on spending behavior

               6. **MAJOR TRANSACTION PATTERNS**:
                  - Recent transaction activity and volume
                  - Transaction types and geographic patterns
                  - Investment vs banking transaction breakdown

               Please provide a comprehensive context summary that includes detailed spending analytics and will guide the specialized agents in their analysis.
               """
        
        logger.info(f"Starting Manager context setting for client {client_id}")
        
        result = Runner.run_sync(
            starting_agent=agents["manager"],
            input=context_request,
            max_turns=5
        )
        
        context_summary = result.final_output
        
        # Print response to console
        print(f"\n📋 Manager Context Summary:")
        print("=" * 60)
        print(context_summary)
        print("=" * 60)
        print()
        
        # Log response to consolidated file
        consolidated_log_file.write(f"\nContext Summary:\n{context_summary}\n")
        consolidated_log_file.flush()
        
        logger.info(f"✅ Manager context setting completed")
        print(f"✅ Manager Context Setting completed")
        
        return context_summary
        
    except Exception as e:
        error_msg = f"❌ Manager context setting failed: {e}"
        print(error_msg)
        
        # Log error to consolidated file
        consolidated_log_file.write(f"\nERROR: {error_msg}\n")
        consolidated_log_file.flush()
        
        logger.error(error_msg)
        return f"Error: {e}"

def run_sequential_agent_analysis(agents: Dict[str, Agent], client_id: str, context_summary: str, consolidated_log_file) -> Dict[str, str]:
    """Run specialized agents sequentially with context"""
    agent_responses = {}
    
    # Define analysis requests for each agent with context
    agent_requests = {
        "investment": f"""
        Based on the Manager's comprehensive context summary, analyze investment opportunities for client {client_id}.

        CONTEXT SUMMARY (includes spending analytics):
        {context_summary}

        Focus on:
        - Share of Potential analysis with specific product recommendations
        - Current holdings optimization opportunities
        - Investment recommendations based on spending pattern analysis (transaction types, volume, frequency)
        - Risk appetite alignment with investment products
        - Use spending analytics insights for behavior-based investment recommendations
        """,
        "loan": f"""
        Based on the Manager's comprehensive context summary, analyze loan and credit opportunities for client {client_id}.

        CONTEXT SUMMARY (includes spending analytics):
        {context_summary}

        Focus on:
        - Available credit products from the database
        - AEDB alerts indicating loan interest
        - Loan recommendations based on spending pattern analysis (loan payments, transaction names, merchant patterns)
        - CASA balance analysis for loan capacity
        - Client segment-appropriate loan recommendations using spending behavior insights
        """,
        "banking_casa": f"""
        Based on the Manager's comprehensive context summary, analyze banking and CASA opportunities for client {client_id}.

        CONTEXT SUMMARY (includes spending analytics):
        {context_summary}

        Focus on:
        - CASA balance trends and liquidity management
        - Banking recommendations based on spending pattern analysis (deposit patterns, payment frequency, transfer needs)
        - Deposit and savings product opportunities using transaction behavior insights
        - Cash management and liquidity optimization based on spending patterns
        """,
        "risk_compliance": f"""
        Based on the Manager's comprehensive context summary, analyze risk and compliance for client {client_id}.

        CONTEXT SUMMARY (includes spending analytics):
        {context_summary}

        Focus on:
        - AEDB alerts and risk level analysis
        - Risk appetite alignment with current holdings and spending patterns
        - Compliance status and complaint history
        - Risk mitigation recommendations based on transaction volume and patterns
        - Spending behavior risk assessment using transaction analytics
        """
    }
    
    # Run agents in specific order
    agent_order = ["investment", "loan", "banking_casa", "risk_compliance"]
    
    for agent_name in agent_order:
        try:
            print(f"\n🔍 STEP {agent_order.index(agent_name) + 2}: {agent_name.replace('_', ' ').title()} Analysis...")
            print(f"Request: {agent_requests[agent_name][:100]}...")
            print("-" * 80)
            
            # Log to consolidated file (without repeating Manager context)
            consolidated_log_file.write(f"\n{'='*80}\n")
            consolidated_log_file.write(f"=== {agent_name.replace('_', ' ').title()} Analysis for Client {client_id} ===\n")
            consolidated_log_file.write(f"Timestamp: {datetime.now()}\n")
            consolidated_log_file.write(f"Request: Based on Manager's comprehensive context summary, analyze {agent_name.replace('_', ' ')} opportunities for client {client_id}.\n")
            consolidated_log_file.write(f"{'='*80}\n")
            consolidated_log_file.flush()
            
            logger.info(f"Starting {agent_name} analysis for client {client_id}")
            
            result = Runner.run_sync(
                starting_agent=agents[agent_name],
                input=agent_requests[agent_name],
                max_turns=5
            )
            
            agent_responses[agent_name] = result.final_output
            
            # Print response to console
            print(f"\n📋 {agent_name.replace('_', ' ').title()} Response:")
            print("=" * 60)
            print(result.final_output)
            print("=" * 60)
            print()  # Add extra line for better separation
            
            # Log response to consolidated file
            consolidated_log_file.write(f"\nResponse:\n{result.final_output}\n")
            consolidated_log_file.flush()
            
            logger.info(f"✅ {agent_name} analysis completed")
            print(f"✅ {agent_name.replace('_', ' ').title()} Analysis completed")
            
        except Exception as e:
            error_msg = f"❌ {agent_name} analysis failed: {e}"
            print(error_msg)
            
            # Log error to consolidated file
            consolidated_log_file.write(f"\nERROR: {error_msg}\n")
            consolidated_log_file.flush()
            
            logger.error(error_msg)
            agent_responses[agent_name] = f"Error: {e}"
    
    return agent_responses

def _pick_default_client_id(dbm: EliteDatabaseManager) -> str:
    """Pick a valid existing client_id from core.client_context as fallback."""
    rows = dbm._execute_query("SELECT client_id FROM core.client_context ORDER BY client_id ASC LIMIT 1")
    return rows[0].get("client_id") if rows else ""


def main(client_id: str = None):
    """Main function to run Elite analysis with chain of thought
    
    Args:
        client_id (str, optional): Client ID to analyze. If None, will auto-pick from database.
    """
    print("🚀 EliteX - Elite Financial Strategy Framework with Chain of Thought")
    print("=" * 80)
    
    try:
        # Clear all existing log files
        print("🧹 Clearing existing log files...")
        for log_file in LOGS_DIR.glob("*.txt"):
            log_file.unlink()
        print("✅ All log files cleared")
        
        # Create agents
        agents = create_elite_agents()
        logger.info("✅ All Elite agents created successfully")
        
        # Handle client_id input - prioritize function argument, then command line, then env var
        if client_id is None:
            # Fallback to command line args if no function argument provided
            parser = argparse.ArgumentParser(description="Run EliteX analysis")
            parser.add_argument("--client", dest="client_id", default=os.getenv("CLIENT_ID", ""), help="Client ID to analyze")
            args, _ = parser.parse_known_args()
            client_id = args.client_id.strip()
        
        # Validate/resolve client id
        def _exists(cid: str) -> bool:
            res = db_manager._execute_query("SELECT 1 FROM core.client_context WHERE LOWER(client_id)=LOWER(%s) LIMIT 1", (cid,))
            return bool(res)

        if not client_id or not _exists(client_id):
            # Try prefix match based on first 2 characters if provided
            if client_id:
                prefix = client_id[:2]
                rows = db_manager._execute_query("SELECT client_id FROM core.client_context WHERE client_id ILIKE %s ORDER BY client_id ASC LIMIT 1", (prefix + '%',))
                if rows:
                    client_id = rows[0].get('client_id')
            # Fallback to first available
            if not client_id or not _exists(client_id):
                client_id = _pick_default_client_id(db_manager)
            if not client_id:
                raise RuntimeError("No client_id available in database to analyze")
        
        print(f"\n📊 Running Comprehensive Elite Analysis for client: {client_id}")
        print("=" * 60)
        
        # Create single consolidated log file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        consolidated_log_file_path = LOGS_DIR / f"elite_analysis_{client_id}_{timestamp}.txt"
        
        with open(consolidated_log_file_path, 'w', encoding='utf-8') as consolidated_log_file:
            # Write header to consolidated log
            consolidated_log_file.write(f"🚀 EliteX - Elite Financial Strategy Framework\n")
            consolidated_log_file.write(f"Client: {client_id}\n")
            consolidated_log_file.write(f"Timestamp: {datetime.now()}\n")
            consolidated_log_file.write(f"{'='*80}\n\n")
            consolidated_log_file.flush()
            
            # Step 1: Manager sets comprehensive context
            context_summary = run_manager_context_setting(agents, client_id, consolidated_log_file)
            
            # Step 2: Run specialized agents sequentially with context
            print("\n🔍 STEP 2-5: Sequential Specialized Agent Analysis")
            print("-" * 50)
            agent_responses = run_sequential_agent_analysis(agents, client_id, context_summary, consolidated_log_file)
            
            # Step 6: Final manager synthesis
            print("\n🎯 STEP 6: Final Manager Synthesis and Strategy Development")
            print("-" * 50)
            
            # Create comprehensive request for manager
            manager_request = f"""
            As the Elite Manager, provide final synthesis and strategy development for client {client_id} based on the comprehensive context and specialized agent analyses:
            
            INITIAL CONTEXT SUMMARY:
            {context_summary}
            
            SPECIALIZED AGENT ANALYSES:
            INVESTMENT ANALYSIS: {agent_responses.get('investment', 'Not available')}
            
            LOAN ANALYSIS: {agent_responses.get('loan', 'Not available')}
            
            BANKING CASA ANALYSIS: {agent_responses.get('banking_casa', 'Not available')}
            
            RISK COMPLIANCE ANALYSIS: {agent_responses.get('risk_compliance', 'Not available')}
            
            Please provide:
            1. **COMPREHENSIVE CLIENT OVERVIEW**: 
               - Updated client profile summary based on all analyses
               - Key financial metrics and portfolio status
               - Risk profile and relationship strength assessment
            
            2. **PRIORITIZED RECOMMENDATIONS**:
               - Chain of thought analysis prioritizing products based on:
                 * AEDB alerts (Example: if client has auto loan inquiry, prioritize auto loan products)
                 * Share of Potential (upsell opportunities) - focus on the specific product with highest potential
                 * Client behavior patterns (transaction analysis)
                 * CASA balance changes
                 * Risk appetite alignment
            
            3. **STRATEGIC ACTION PLAN**:
               - Final prioritized product recommendations with detailed reasoning
               - Focus on specific products from AEDB alerts and Share of Potential
               - Implementation timeline and priority order
            
            4. **RM CONVERSATION STRATEGY**:
               - Talking points for the specific product with highest potential
               - Upsell strategy development
               - Client engagement approach based on relationship strength
            
            5. **EXECUTION PLAN**:
               - Detailed action plan for the Relationship Manager
               - Follow-up schedule and monitoring requirements
               - Success metrics and review timeline
            """
            
            print("Running Manager synthesis...")
            print(f"Request: {manager_request}")
            print("-" * 80)
            
            # Log manager request to consolidated file (without repeating context)
            consolidated_log_file.write(f"\n{'='*80}\n")
            consolidated_log_file.write(f"=== Manager Synthesis for Client {client_id} ===\n")
            consolidated_log_file.write(f"Timestamp: {datetime.now()}\n")
            consolidated_log_file.write(f"Request: Provide final synthesis and strategy development based on comprehensive context and specialized agent analyses.\n")
            consolidated_log_file.write(f"{'='*80}\n")
            consolidated_log_file.flush()
            
            logger.info("Starting manager synthesis")
            
            manager_result = Runner.run_sync(
                starting_agent=agents["manager"],
                input=manager_request,
                max_turns=8
            )
            
            # Print manager response to console
            print(f"\n📋 Manager Synthesis Response:")
            print("=" * 60)
            print(manager_result.final_output)
            print("=" * 60)
            
            # Log manager response to consolidated file
            consolidated_log_file.write(f"\nManager Synthesis Response:\n{manager_result.final_output}\n")
            consolidated_log_file.write(f"\n{'='*80}\n")
            consolidated_log_file.write(f"Analysis completed at: {datetime.now()}\n")
            consolidated_log_file.flush()
            
            # Print final results
            print(f"\n📋 FINAL ELITE STRATEGY ANALYSIS")
            print("=" * 60)
            print(manager_result.final_output)
            
            logger.info(f"✅ Complete Elite Analysis completed with {len(manager_result.raw_responses)} manager responses")
            
            print(f"\n🎉 Elite Analysis completed successfully!")
            print(f"📁 All responses logged in single file: {consolidated_log_file_path}")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Parse command line arguments for direct script execution
    parser = argparse.ArgumentParser(description="Run EliteX analysis")
    parser.add_argument("--client", dest="client_id", default=os.getenv("CLIENT_ID", ""), help="Client ID to analyze")
    args = parser.parse_args()
    
    # Call main with client_id argument
    main(client_id='10GLPHG')

    # Clients with complete data presence (context + portfolio + holding) - sampled
    # Generated on 2025-10-05 for quick testing/reference:
    # ['10GLPHG', '10GRRXX', '10PKFPQ', '10QAXPK', '10QHKPA', '10QHLHP', '10QXGLF', '10QXRPX', '10RXAKP', '10XQKRF',
    #  '11AAPGR', '11ALFPK', '11FKLLH', '11FQLKK', '11FXHLQ', '11HXFGR', '11HXPLF', '11KPGQK', '11KQKXL', '11KQXAQ',
    #  '11LPKHH', '11QHRKF', '11QPPQG', '12AHQHL', '12APFQL', '12HAHQH', '12HAKFG', '12HHXGA', '12KRAPA', '12LFGLA',
    #  '12QQAHQ', '12XFGRP', '13HHAAX', '13KFXRF', '13KHGPQ', '13RXRXF', '14FPRPR', '14HFQAR', '14HPHKR', '14HPPQL',
    #  '14KAKGL', '14LHGPG', '14LRHXX', '14LXHLQ', '14QPXFK', '15GGGKP', '15GGRAH', '15GRGFK', '15GXHXR', '15HGRQA']
    
    # NOTE: None of the above clients have transaction history in the database.
    # Transaction data exists in data/transaction_history.xlsx for clients CLI_001-CLI_010,
    # but these clients don't exist in the current database.
    # 
    # To use clients with transaction history, either:
    # 1. Import transaction data using import_transaction_data.py, or
    # 2. Use the transaction clients directly: ['CLI_001', 'CLI_002', 'CLI_003', 'CLI_004', 'CLI_005', 'CLI_006', 'CLI_007', 'CLI_008', 'CLI_009', 'CLI_010']
