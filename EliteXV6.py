#!/usr/bin/env python3
"""
EliteXV6.py - Elite Financial Strategy Framework (V6) with Structured Pydantic Outputs

Clean, modular architecture with utility functions extracted to utils.py
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from sqlalchemy import text
from dotenv import load_dotenv

import db_engine
from agents import Agent, Runner, function_tool  # type: ignore
from agents.agent_output import AgentOutputSchema  # type: ignore

# Enable Agency Swarm logging (set to WARNING to reduce HTTP noise)
os.environ["AGENCY_SWARM_LOG_LEVEL"] = "WARNING"

from ElitePromptV5 import (
    ELITE_MANAGER_AGENT_PROMPT_V5,
    ELITE_INVESTMENT_AGENT_PROMPT_V5,
    ELITE_LOAN_AGENT_PROMPT_V5,
    ELITE_BANKING_CASA_AGENT_PROMPT_V5,
    ELITE_RISK_COMPLIANCE_AGENT_PROMPT_V5,
    ELITE_RM_STRATEGY_AGENT_PROMPT_V5,
    ELITE_BANCASSURANCE_AGENT_PROMPT_V5,
)

# Import Pydantic Models for Structured Outputs
from models import (
    ManagerAgentOutput,
    RiskComplianceAgentOutput,
    InvestmentAgentOutput,
    LoanAgentOutput,
    BankingAgentOutput,
    BancassuranceAgentOutput,
    RMStrategyAgentOutput,
)

# Import Utility Functions
from utils import (
    write_file_header,
    write_agent_output,
    write_file_footer,
    export_structured_json,
    print_completion_summary,
    build_rm_strategy_input,
)


# Env
load_dotenv()
os.environ["AGENTS_TRACING_DISABLED"] = "1"


# Create Output directory for results
OUTPUT_DIR = Path("Output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Configure simple logging (WARNING level to reduce HTTP logs)
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


class EliteDatabaseManagerV6:
    def __init__(self):
        self.engine = db_engine.elite_engine

    def _execute_query(self, query: str, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        try:
            with self.engine.connect() as conn:
                res = conn.execute(text(query), params or {})
                return [dict(r._mapping) for r in res]
        except Exception as e:
            logging.error(f"❌ Query execution failed: {e}")
            logging.error(f"❌ Query: {query[:200]}...")
            logging.error(f"❌ Params: {params}")
            return []

    def _json(self, obj: Any) -> str:
        return json.dumps(obj, indent=2, default=str)

    # --- Introspection helpers ---
    def _table_exists(self, schema: str, table: str) -> bool:
        rows = self._execute_query(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema=:schema AND table_name=:table LIMIT 1
            """,
            {"schema": schema, "table": table},
        )
        return bool(rows)

    def _columns(self, schema: str, table: str) -> List[str]:
        rows = self._execute_query(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema=:schema AND table_name=:table
            ORDER BY ordinal_position
            """,
            {"schema": schema, "table": table},
        )
        return [r.get("column_name") for r in rows]

    # Reuse V4 core sources where stable (client, banking, risk, investments summary)
    # Pull directly from V4 for parity; to avoid import cycles, replicate key queries.

    def get_elite_client_data(self, client_id: str) -> str:
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
        WHERE LOWER(client_id) = LOWER(:cid)
        LIMIT 1
        """
        rows = self._execute_query(query, {"cid": client_id})
        if not rows:
            return self._json({"client_id": client_id, "error": "Client not found"})

        c = rows[0]
        full_name = f"{c.get('first_name','') or ''} {c.get('last_name','') or ''}".strip()
        age = float(c.get('age') or 0)
        income = float(c.get('income') or 0)
        tenure = float(c.get('tenure') or 0)
        banking_segment = c.get('customer_profile_banking_segment') or ''
        subsegment = c.get('customer_profile_subsegment') or ''
        risk_level = int(c.get('risk_level') or 0)

        life_stage = (
            "early_career" if age < 25 else
            "career_building" if age < 35 else
            "mid_career" if age < 50 else
            "pre_retirement" if age < 65 else
            "retirement"
        )
        if income > 2000000 or banking_segment == 'ULTRA_HIGH_NET_WORTH':
            risk_capacity = "very_high"
        elif income > 1000000 or banking_segment == 'HIGH_NET_WORTH' or subsegment == 'Private Banking':
            risk_capacity = "high"
        elif income > 500000 or banking_segment == 'AFFLUENT':
            risk_capacity = "medium"
        else:
            risk_capacity = "low"

        sophistication = (
            "sophisticated" if (c.get('professional_investor_flag') == 'Y' or banking_segment == 'WEALTH MANAGEMENT') else
            "intermediate" if (subsegment == 'Private Banking' or risk_level > 4) else
            "basic"
        )

        if banking_segment == 'ULTRA_HIGH_NET_WORTH' or income > 5000000:
            client_tier = "ultra_high_net_worth"
        elif banking_segment == 'HIGH_NET_WORTH' or subsegment == 'Private Banking' or income > 1000000:
            client_tier = "high_net_worth"
        elif banking_segment == 'AFFLUENT' or income > 500000:
            client_tier = "affluent"
        else:
            client_tier = "mass_market"

        relationship_strength = (
            "very_strong" if tenure > 10 else
            "strong" if tenure > 5 else
            "moderate" if tenure > 2 else
            "new"
        )

        out = dict(c)
        out.update({
            "full_name": full_name,
            "calculated_risk_capacity": risk_capacity,
            "calculated_life_stage": life_stage,
            "calculated_sophistication": sophistication,
            "calculated_client_tier": client_tier,
            "calculated_relationship_strength": relationship_strength,
            "data_source": "core.client_context@fab_elite"
        })
        return self._json(out)

    def get_elite_client_investments_summary(self, client_id: str) -> str:
        """
        Pull ONLY from core.client_investment and expose:
        - asset_class
        - cost_value_aed (Purchase Cost)
        - market_value_aed (Current Value)
        - overall_portfolio_xirr_since_inception
        - security_category
        - security_name
        """
        positions = self._execute_query(
            """
            SELECT 
                time_key,
                portfolio_id,
                security_name,
                asset_class,
                COALESCE(security_category, sub_asset_type_desc) AS security_category,
                cost_value_aed,
                market_value_aed,
                overall_portfolio_xirr_since_inception
            FROM core.client_investment 
            WHERE client_id=:cid
            ORDER BY time_key DESC NULLS LAST, market_value_aed DESC NULLS LAST
            LIMIT 500
            """,
            {"cid": client_id},
        )

        total_cost_value_aed = sum(float(p.get("cost_value_aed") or 0) for p in positions)
        total_market_value_aed = sum(float(p.get("market_value_aed") or 0) for p in positions)

        # Aggregate by asset class using market value
        asset_class_to_mv: Dict[str, float] = {}
        for p in positions:
            cls = p.get("asset_class") or "Unknown"
            mv = float(p.get("market_value_aed") or 0)
            asset_class_to_mv[cls] = asset_class_to_mv.get(cls, 0.0) + mv

        asset_classes = [
            {"asset_class": k, "market_value_aed": v}
            for k, v in sorted(asset_class_to_mv.items(), key=lambda kv: kv[1], reverse=True)
        ]

        # Provide a slimmed list for narrative convenience
        positions_brief = [
            {
                "security_name": p.get("security_name"),
                "security_category": p.get("security_category"),
                "asset_class": p.get("asset_class"),
                "cost_value_aed": p.get("cost_value_aed"),
                "market_value_aed": p.get("market_value_aed"),
                "overall_portfolio_xirr_since_inception": p.get("overall_portfolio_xirr_since_inception"),
            }
            for p in positions
        ]

        return self._json({
            "client_id": client_id,
            "current_holdings": [],  # intentionally empty; we rely solely on core.client_investment
            "investment_positions": positions,
            "positions_brief": positions_brief,
            "summary": {
                "positions_count": len(positions),
                "total_cost_value_aed": total_cost_value_aed,
                "total_market_value_aed": total_market_value_aed,
                "asset_classes": asset_classes,
            },
            "data_sources": ["core.client_investment"],
        })

    def get_elite_investment_products_not_held(self, client_id: str) -> str:
        """
        Return investment products (funds, bonds, stocks) that the client does NOT currently hold.
        This helps the investment agent recommend new products from unexplored opportunities.
        Uses case-insensitive matching between product names and client holdings.
        """
        # Get all products from funds, bonds, and stocks
        all_products = []
        
        # Funds
        if self._table_exists("core", "funds"):
            fund_cols = set(self._columns("core", "funds"))
            fund_select = ["'fund' as product_type"]
            
            # Add available columns
            for col in ["isin", "name", "investment_objective", "asset_class", "sub_asset_class",
                       "total_net_assets", "annualized_return_3y", "annualized_return_5y",
                       "morningstar_rating", "fund_domicile", "currency"]:
                if col in fund_cols:
                    fund_select.append(f"{col}")
            
            try:
                funds = self._execute_query(
                    f"SELECT {', '.join(fund_select)} FROM core.funds LIMIT 500"
                )
                all_products.extend(funds)
            except Exception:
                pass
        
        # Bonds
        if self._table_exists("core", "bonds"):
            bond_cols = set(self._columns("core", "bonds"))
            bond_select = ["'bond' as product_type"]
            
            for col in ["isin", "issuer_name", "security_ccy", "bloomberg_rating",
                       "coupon_percent", "ytm", "maturity_date", "islamic_compliance",
                       "sub_asset_type_desc", "security_domicile"]:
                if col in bond_cols:
                    bond_select.append(f"{col}")
            # Standardize name column
            if "issuer_name" in bond_cols:
                bond_select.append("issuer_name as name")
            
            try:
                bonds = self._execute_query(
                    f"SELECT {', '.join(bond_select)} FROM core.bonds LIMIT 500"
                )
                all_products.extend(bonds)
            except Exception:
                pass
        
        # Stocks
        if self._table_exists("core", "stocks"):
            stock_cols = set(self._columns("core", "stocks"))
            stock_select = ["'stock' as product_type"]
            
            for col in ["isin", "name", "sector_descriptions", "company_domicile",
                       "last_price", "target_price", "volatility", "market_cap"]:
                if col in stock_cols:
                    stock_select.append(f"{col}")
            
            try:
                stocks = self._execute_query(
                    f"SELECT {', '.join(stock_select)} FROM core.stocks LIMIT 500"
                )
                all_products.extend(stocks)
            except Exception:
                pass
        
        # Get what client currently holds (from both holdings and positions)
        held_names_set: set[str] = set()
        
        try:
            holdings = self._execute_query(
                """SELECT DISTINCT LOWER(TRIM(security_name)) as name
                   FROM core.client_holding 
                   WHERE client_id=:cid AND security_name IS NOT NULL""",
                {"cid": client_id}
            )
            for h in holdings:
                if h.get("name"):
                    held_names_set.add(self._normalize_name(h["name"]))
        except Exception:
            pass
        
        try:
            positions = self._execute_query(
                """SELECT DISTINCT LOWER(TRIM(security_name)) as name
                   FROM core.client_investment 
                   WHERE client_id=:cid AND security_name IS NOT NULL""",
                {"cid": client_id}
            )
            for p in positions:
                if p.get("name"):
                    held_names_set.add(self._normalize_name(p["name"]))
        except Exception:
            pass
        
        # Filter out products the client already holds
        not_held = []
        for product in all_products:
            product_name = product.get("name") or product.get("issuer_name") or ""
            if product_name:
                normalized = self._normalize_name(product_name)
                if normalized and normalized not in held_names_set:
                    not_held.append(product)
        
        # Group by product type for better organization
        by_type = {
            "funds": [p for p in not_held if p.get("product_type") == "fund"],
            "bonds": [p for p in not_held if p.get("product_type") == "bond"],
            "stocks": [p for p in not_held if p.get("product_type") == "stock"],
        }
        
        return self._json({
            "client_id": client_id,
            "total_products_available": len(all_products),
            "client_currently_holds_count": len(held_names_set),
            "products_not_held_count": len(not_held),
            "by_type": {
                "funds_not_held": len(by_type["funds"]),
                "bonds_not_held": len(by_type["bonds"]),
                "stocks_not_held": len(by_type["stocks"]),
            },
            "products_not_held": {
                "funds": by_type["funds"][:100],  # Limit to top 100 per type
                "bonds": by_type["bonds"][:100],
                "stocks": by_type["stocks"][:100],
            }
        })
    
    def _normalize_name(self, name: str) -> str:
        """Normalize product/security name for comparison."""
        return " ".join(str(name).lower().strip().split())

    def get_elite_banking_casa_data(self, client_id: str) -> str:
        """
        Enhanced CASA data including:
        - Portfolio summary from client_portfolio
        - Actual CASA account balances from productbalance
        - Current and Savings account details
        - Deposit trend analysis (current month vs 6-month average)
        - Product recommendation flag (Investment if increasing, Loan if decreasing)
        """
        portfolio = self._execute_query(
            """SELECT id, portfolio_id, client_id, portfolio_type, currency,
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
                FROM core.client_portfolio WHERE client_id=:cid
                ORDER BY last_valuation_date DESC LIMIT 5""",
            {"cid": client_id},
        )
        
        # Get actual CASA accounts from productbalance with historical data
        casa_accounts = []
        total_casa_balance = 0.0
        current_accounts = []
        savings_accounts = []
        
        # Get historical CASA balances for trend analysis (last 7 months)
        casa_history = []
        if self._table_exists("core", "productbalance"):
            try:
                # Current month balance
                casa_accounts = self._execute_query(
                    """SELECT product_description, product_levl1_desc, product_levl2_desc,
                              product_levl3_desc, outstanding, account_number, time_key
                       FROM core.productbalance 
                       WHERE customer_number=:cid 
                       AND product_levl1_desc='DEPOSIT PRODUCTS'
                       AND product_levl2_desc='CASA'
                       ORDER BY time_key DESC NULLS LAST, outstanding DESC NULLS LAST""",
                    {"cid": client_id}
                )
                
                # Categorize and sum current month
                for acc in casa_accounts:
                    balance = float(acc.get('outstanding') or 0)
                    total_casa_balance += balance
                    
                    levl3 = (acc.get('product_levl3_desc') or '').upper()
                    if 'CURRENT' in levl3:
                        current_accounts.append(acc)
                    elif 'SAVING' in levl3:
                        savings_accounts.append(acc)
                
                # Get historical balances from client_prod_balance_monthly (better source with actual history)
                if self._table_exists("core", "client_prod_balance_monthly"):
                    try:
                        casa_history = self._execute_query(
                            """SELECT year_cal, month_cal,
                                      CAST(closing_current_account_bal AS NUMERIC) + 
                                      CAST(closing_saving_account_bal AS NUMERIC) as total_balance
                               FROM core.client_prod_balance_monthly 
                               WHERE client_id=:cid 
                               ORDER BY CAST(year_cal AS INTEGER) DESC, CAST(month_cal AS INTEGER) DESC
                               LIMIT 7""",
                            {"cid": client_id}
                        )
                    except Exception:
                        # Fallback to productbalance if monthly table fails
                        casa_history = self._execute_query(
                            """SELECT time_key, SUM(outstanding) as total_balance
                               FROM core.productbalance 
                               WHERE customer_number=:cid 
                               AND product_levl1_desc='DEPOSIT PRODUCTS'
                               AND product_levl2_desc='CASA'
                               GROUP BY time_key
                               ORDER BY time_key DESC
                               LIMIT 7""",
                            {"cid": client_id}
                        )
                else:
                    # Fallback if monthly table doesn't exist
                    casa_history = self._execute_query(
                        """SELECT time_key, SUM(outstanding) as total_balance
                           FROM core.productbalance 
                           WHERE customer_number=:cid 
                           AND product_levl1_desc='DEPOSIT PRODUCTS'
                           AND product_levl2_desc='CASA'
                           GROUP BY time_key
                           ORDER BY time_key DESC
                           LIMIT 7""",
                        {"cid": client_id}
                    )
            except Exception:
                pass
        
        # Calculate deposit trend analysis
        current_month_deposit = total_casa_balance
        six_month_avg = 0.0
        deposit_trend = "stable"
        trend_percentage = 0.0
        recommendation_flag = "maintain"
        rm_recommendation = ""
        
        if len(casa_history) >= 2:
            # First entry is current month, next 6 are previous months
            historical_balances = [float(h.get('total_balance') or 0) for h in casa_history[1:7]]
            
            if historical_balances:
                six_month_avg = sum(historical_balances) / len(historical_balances)
                
                if six_month_avg > 0:
                    trend_percentage = ((current_month_deposit - six_month_avg) / six_month_avg) * 100
                    
                    # Determine trend and recommendation
                    if trend_percentage > 15:  # More than 15% increase
                        deposit_trend = "increasing_significantly"
                        recommendation_flag = "investment_products"
                        rm_recommendation = f"Client's CASA balance has increased by {trend_percentage:.1f}% (from AED {six_month_avg:,.2f} to AED {current_month_deposit:,.2f}). This indicates accumulated liquidity. RECOMMEND: Investment products (funds, bonds, structured deposits) to optimize returns on idle cash."
                    elif trend_percentage > 5:  # 5-15% increase
                        deposit_trend = "increasing"
                        recommendation_flag = "investment_products"
                        rm_recommendation = f"Client's CASA balance has increased by {trend_percentage:.1f}% (from AED {six_month_avg:,.2f} to AED {current_month_deposit:,.2f}). RECOMMEND: Discuss investment opportunities to enhance portfolio returns."
                    elif trend_percentage < -15:  # More than 15% decrease
                        deposit_trend = "decreasing_significantly"
                        recommendation_flag = "loan_products"
                        rm_recommendation = f"Client's CASA balance has decreased by {abs(trend_percentage):.1f}% (from AED {six_month_avg:,.2f} to AED {current_month_deposit:,.2f}). This may indicate liquidity needs or major expenditure. RECOMMEND: Discuss loan products (personal loan, credit line, overdraft facility) to maintain financial flexibility."
                    elif trend_percentage < -5:  # 5-15% decrease
                        deposit_trend = "decreasing"
                        recommendation_flag = "loan_products"
                        rm_recommendation = f"Client's CASA balance has decreased by {abs(trend_percentage):.1f}% (from AED {six_month_avg:,.2f} to AED {current_month_deposit:,.2f}). RECOMMEND: Proactively offer credit facilities to support cash flow needs."
                    else:  # Within ±5%
                        deposit_trend = "stable"
                        recommendation_flag = "maintain"
                        rm_recommendation = f"Client's CASA balance is stable (within ±5% range). Current: AED {current_month_deposit:,.2f}, 6-month avg: AED {six_month_avg:,.2f}. RECOMMEND: Maintain current banking relationship and review portfolio allocation."
        
        return self._json({
            "client_id": client_id,
            "portfolio_balances": portfolio,
            "casa_accounts": {
                "total_casa_balance": total_casa_balance,
                "current_accounts": current_accounts,
                "savings_accounts": savings_accounts,
                "all_casa_accounts": casa_accounts[:5],  # Limit to recent entries
            },
            "deposit_trend_analysis": {
                "current_month_deposit": current_month_deposit,
                "six_month_average": six_month_avg,
                "trend": deposit_trend,
                "trend_percentage": round(trend_percentage, 2),
                "recommendation_flag": recommendation_flag,
                "rm_recommendation": rm_recommendation,
                "historical_data": casa_history[:7],
            },
        })

    def get_elite_risk_compliance_data(self, client_id: str) -> str:
        alerts = self._execute_query(
            """SELECT client_id, risk_name, risk_level, match_diff_from_house_rec
                 FROM core.client_holdings_risk_level WHERE client_id=:cid
                 ORDER BY risk_level DESC LIMIT 20""",
            {"cid": client_id},
        )
        return self._json({"client_id": client_id, "all_aedb_alerts": alerts})

    # ------------------------------
    # NEW: Recommended Actions inputs
    # ------------------------------
    def get_elite_recommended_actions_data(self, client_id: str) -> str:
        # KYC / follow-up (handle alt column names)
        kyc: Dict[str, Any] | None = None
        if self._table_exists("app", "client"):
            cols = set(self._columns("app", "client"))
            kyc_cols = [
                "client_id",
                "kyc_expiry_date",
                "due_for_follow_up" if "due_for_follow_up" in cols else ("due_for_followup" if "due_for_followup" in cols else None),
                "follow_up_reasons" if "follow_up_reasons" in cols else ("followup_reasons" if "followup_reasons" in cols else None),
            ]
            kyc_cols = [c for c in kyc_cols if c]
            q = f"SELECT {', '.join(kyc_cols)} FROM app.client WHERE LOWER(client_id)=LOWER(:cid) LIMIT 1"
            k = self._execute_query(q, {"cid": client_id})
            kyc = (k[0] if k else None)

        # Maturing products in next 3 months (prefer client-specific maturity table)
        maturity_rows: List[Dict[str, Any]] = []
        maturity_table = None
        for cand in ("maturityopportunity", "maturity_opportunity"):
            if self._table_exists("app", cand):
                maturity_table = f"app.{cand}"
                break
        if maturity_table:
            mcols = set(self._columns("app", maturity_table.split(".")[1]))
            category_col = "category" if "category" in mcols else None
            product_col = "product" if "product" in mcols else ("product_name" if "product_name" in mcols else None)
            maturity_col = "maturity_date" if "maturity_date" in mcols else None
            if category_col and product_col and maturity_col and ("client_id" in mcols):
                mq = (
                    f"SELECT {category_col} AS category, {product_col} AS product, {maturity_col} AS maturity_date "
                    f"FROM {maturity_table} WHERE LOWER(client_id)=LOWER(:cid) AND {maturity_col} IS NOT NULL "
                    f"AND {maturity_col} >= CURRENT_DATE AND {maturity_col} < CURRENT_DATE + INTERVAL '3 months' "
                    f"ORDER BY {maturity_col} ASC"
                )
                maturity_rows = self._execute_query(mq, {"cid": client_id})
        else:
            # Fallback: master product catalogue (no client filter); return empty to avoid misleading data
            maturity_rows = []

        # Open service requests (active states list mirrored from prompts)
        service_rows: List[Dict[str, Any]] = []
        if self._table_exists("core", "rmclientservicerequests"):
            scols = set(self._columns("core", "rmclientservicerequests"))
            id_col = "client_id" if "client_id" in scols else ("customer_id" if "customer_id" in scols else ("cif" if "cif" in scols else None))
            subcat_col = "sub_category" if "sub_category" in scols else ("subcategory" if "subcategory" in scols else None)
            cat_col = "category" if "category" in scols else None
            status_col = "status" if "status" in scols else None
            created_col = None
            for cand in ("created_date", "created_ts", "creation_ts", "createdon"):
                if cand in scols:
                    created_col = cand
                    break
            if id_col and cat_col and status_col and created_col:
                sq = (
                    f"SELECT {subcat_col or 'NULL'} AS sub_category, {cat_col} AS category, {status_col} AS status, {created_col} AS created_date "
                    f"FROM core.rmclientservicerequests WHERE LOWER({id_col})=LOWER(:cid) AND {status_col} IN ("
                    "'BranchSupervisorVerification','ROPSMaker','AOPBOBKYCTeam','TellerSupervisorVerification',"
                    "'CopsMaker','CopsMakerPostCutOff','COPSMakerPreCutOffQueue','BranchSupervisor',"
                    "'JSBHFinancialApproverScenario3','CSDMaker','CSDAuthorizer','AmendRequestEntry'"
                    ") ORDER BY " + created_col + " ASC NULLS LAST"
                )
                service_rows = self._execute_query(sq, {"cid": client_id})

        # Portfolio allocation context (for a brief one-liner insight)
        portfolio_rows = self._execute_query(
            """
            SELECT client_id, asset_distribution, aum
            FROM core.client_portfolio
            WHERE client_id=:cid
            ORDER BY last_valuation_date DESC NULLS LAST LIMIT 1
            """,
            {"cid": client_id},
        )

        return self._json({
            "client_id": client_id,
            "kyc": kyc,
            "maturing_products": maturity_rows,
            "open_service_requests": service_rows,
            "portfolio_context": portfolio_rows[0] if portfolio_rows else None,
        })

    # ------------------------------
    # NEW: Product catalogs for proposals
    # ------------------------------
    def get_funds_catalog(self) -> str:
        rows = self._execute_query(
            """SELECT id, name, investment_objective, total_net_assets,
                       annualized_return_3y, annualized_return_5y, morningstar_rating
                 FROM core.funds ORDER BY name LIMIT 500"""
        )
        return self._json({"funds": rows})

    def get_bonds_catalog(self) -> str:
        # Dynamically select available columns to avoid UndefinedColumn errors
        cols = set(self._columns("core", "bonds"))
        wanted: list[tuple[str, list[str]]] = [
            ("isin", ["isin"]),
            ("issuer_name", ["issuer_name", "issuer", "issuer_full_name"]),
            ("security_ccy", ["security_ccy", "currency", "sec_ccy"]),
            ("bloomberg_rating", ["bloomberg_rating", "rating", "credit_rating"]),
            ("coupon_percent", ["coupon_percent", "coupon", "coupon_rate"]),
            ("interest_interval", ["interest_interval", "interest_freq", "coupon_frequency"]),
            ("ytm", ["ytm", "yield_to_maturity", "yield"]),
            ("maturity_date", ["maturity_date", "maturity", "mat_date"]),
            ("islamic_compliance", ["islamic_compliance", "shariah_compliance", "islamic"]),
            ("sub_asset_type_desc", ["sub_asset_type_desc", "sub_asset_type", "asset_subtype"]),
            ("security_domicile", ["security_domicile", "company_domicile", "domicile"]),
        ]
        select_parts: list[str] = []
        for alias, candidates in wanted:
            actual = next((c for c in candidates if c in cols), None)
            if actual:
                select_parts.append(f"{actual} AS {alias}")
        if not select_parts:
            return self._json({"bonds": []})
        order_col = "issuer_name" if "issuer_name" in cols else ("isin" if "isin" in cols else list(cols)[0])
        query = f"SELECT {', '.join(select_parts)} FROM core.bonds ORDER BY {order_col} LIMIT 50"
        rows = self._execute_query(query)
        return self._json({"bonds": rows})

    def get_stocks_catalog(self) -> str:
        # Dynamically select available columns to avoid UndefinedColumn errors
        cols = set(self._columns("core", "stocks"))
        wanted: list[tuple[str, list[str]]] = [
            ("isin", ["isin"]),
            ("name", ["name", "security_name", "stock_name"]),
            ("sector_descriptions", ["sector_descriptions", "sector_description", "sector", "industry"]),
            ("company_domicile", ["company_domicile", "security_domicile", "domicile"]),
            ("last_price", ["last_price", "last_trade_price", "price"]),
            ("target_price", ["target_price", "price_target", "tp"]),
            ("volatility", ["volatility", "price_volatility", "vol"]),
            ("market_cap", ["market_cap", "market_capitalization", "mkt_cap"]),
        ]
        select_parts: list[str] = []
        for alias, candidates in wanted:
            actual = next((c for c in candidates if c in cols), None)
            if actual:
                select_parts.append(f"{actual} AS {alias}")
        if not select_parts:
            return self._json({"stocks": []})
        order_col = "name" if "name" in cols else ("isin" if "isin" in cols else list(cols)[0])
        query = f"SELECT {', '.join(select_parts)} FROM core.stocks ORDER BY {order_col} LIMIT 50"
        rows = self._execute_query(query)
        return self._json({"stocks": rows})

    def get_loan_products_catalog(self) -> str:
        """
        Get comprehensive loan/credit products catalog.
        Reads from core_credit_products.xlsx file which contains product definitions.
        Returns all available loan products with eligibility, rates, terms, etc.
        """
        import pandas as pd
        
        products = []
        try:
            # Read from core_credit_products.xlsx (most comprehensive)
            df = pd.read_excel("data/core_credit_products.xlsx")
            products = df.to_dict('records')
            
            # Convert NaN to None for JSON serialization
            for product in products:
                for key, value in product.items():
                    if pd.isna(value):
                        product[key] = None
                    # Convert timestamps to strings
                    elif hasattr(value, 'strftime'):
                        product[key] = value.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logging.warning(f"Could not load credit products from Excel: {e}")
            # Return empty but valid structure
            return self._json({
                "error": str(e),
                "loan_products": [],
                "total_products": 0,
                "by_type": {}
            })
        
        # Group by product type for easier navigation
        by_type: Dict[str, List[Dict[str, Any]]] = {}
        for p in products:
            ptype = p.get('product_type', 'unknown')
            if ptype not in by_type:
                by_type[ptype] = []
            by_type[ptype].append(p)
        
        return self._json({
            "loan_products": products,
            "total_products": len(products),
            "by_type": by_type,
            "product_types": list(by_type.keys()),
        })

    def get_eligible_loan_products(self, client_id: str) -> str:
        """
        Get loan products that the client is ELIGIBLE for based on:
        - Client segment vs product target_segment
        - Annual income vs min/max loan amounts
        - Risk profile alignment
        - Current assets and AUM
        Returns filtered, ranked products with eligibility scores and reasons.
        """
        import pandas as pd
        
        # Get client profile
        client_data_json = self.get_elite_client_data(client_id)
        client_data = json.loads(client_data_json)
        
        # Get banking/portfolio data for AUM
        banking_data_json = self.get_elite_banking_casa_data(client_id)
        banking_data = json.loads(banking_data_json)
        
        # Extract key client attributes
        client_income = client_data.get('annual_income_usd') or 0
        client_age = client_data.get('age') or 0
        client_risk = client_data.get('risk_appetite') or 'R3'
        client_segment = client_data.get('client_segment') or 'mass_market'
        client_tier = client_data.get('tier') or 'standard'
        
        # Get AUM from portfolio
        aum = 0
        if banking_data.get('portfolio_summary'):
            aum = float(banking_data['portfolio_summary'][0].get('aum', 0))
        
        # Determine effective segment if not explicitly set
        if not client_data.get('client_segment'):
            # Infer from tier or AUM
            tier_lower = str(client_tier).lower()
            if 'elite' in tier_lower or 'premium' in tier_lower:
                if aum > 5000000:
                    client_segment = 'ultra_high_net_worth'
                elif aum > 1000000:
                    client_segment = 'high_net_worth'
                else:
                    client_segment = 'affluent'
            else:
                client_segment = 'mass_market'
        
        # Load loan products
        products = []
        try:
            df = pd.read_excel("data/core_credit_products.xlsx")
            products = df.to_dict('records')
            for product in products:
                for key, value in product.items():
                    if pd.isna(value):
                        product[key] = None
                    elif hasattr(value, 'strftime'):
                        product[key] = value.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logging.warning(f"Could not load credit products: {e}")
            return self._json({
                "error": str(e),
                "eligible_products": [],
                "ineligible_products": []
            })
        
        # Segment hierarchy for matching
        segment_hierarchy = {
            'ultra_high_net_worth': 4,
            'high_net_worth': 3,
            'affluent': 2,
            'mass_market': 1
        }
        
        # Risk level mapping (R1=conservative, R5=aggressive)
        risk_scores = {'R1': 1, 'R2': 2, 'R3': 3, 'R4': 4, 'R5': 5}
        client_risk_score = risk_scores.get(client_risk, 3)
        
        eligible_products = []
        ineligible_products = []
        
        for product in products:
            if not product.get('is_active'):
                continue
            
            eligibility_score = 0
            eligibility_reasons = []
            ineligibility_reasons = []
            
            # 1. Segment matching (40 points)
            product_segment = product.get('target_segment', 'mass_market')
            client_seg_level = segment_hierarchy.get(client_segment, 1)
            product_seg_level = segment_hierarchy.get(product_segment, 1)
            
            if client_seg_level >= product_seg_level:
                segment_points = 40
                eligibility_score += segment_points
                eligibility_reasons.append(f"Client segment ({client_segment}) matches product target ({product_segment})")
            else:
                ineligibility_reasons.append(f"Client segment ({client_segment}) below product target ({product_segment})")
            
            # 2. Income/Amount validation (30 points)
            min_amount = product.get('min_amount', 0)
            max_amount = product.get('max_amount', 0)
            
            # Conservative estimate: client can afford up to 5x annual income
            estimated_capacity = client_income * 5 if client_income > 0 else aum * 0.3
            
            if estimated_capacity >= min_amount:
                if estimated_capacity >= max_amount:
                    income_points = 30
                    eligibility_reasons.append(f"Income capacity (${estimated_capacity:,.0f}) exceeds product range")
                else:
                    income_points = 20
                    eligibility_reasons.append(f"Income capacity (${estimated_capacity:,.0f}) supports min amount")
                eligibility_score += income_points
            else:
                ineligibility_reasons.append(f"Estimated capacity (${estimated_capacity:,.0f}) below min amount (${min_amount:,.0f})")
            
            # 3. Risk alignment (20 points)
            product_risk = product.get('risk_level', 3)
            risk_diff = abs(client_risk_score - product_risk)
            
            if risk_diff == 0:
                risk_points = 20
                eligibility_reasons.append(f"Perfect risk match (Client {client_risk} / Product risk {product_risk})")
            elif risk_diff == 1:
                risk_points = 15
                eligibility_reasons.append(f"Good risk alignment (Client {client_risk} / Product risk {product_risk})")
            elif risk_diff == 2:
                risk_points = 10
                eligibility_reasons.append(f"Acceptable risk alignment (Client {client_risk} / Product risk {product_risk})")
            else:
                risk_points = 0
                ineligibility_reasons.append(f"Risk mismatch (Client {client_risk} / Product risk {product_risk})")
            
            eligibility_score += risk_points
            
            # 4. Collateral check (10 points)
            collateral_required = product.get('collateral_required', False)
            if collateral_required:
                if aum > 0:
                    collateral_points = 10
                    eligibility_reasons.append(f"Client has assets (${aum:,.0f}) for collateral")
                    eligibility_score += collateral_points
                else:
                    ineligibility_reasons.append("No assets available for required collateral")
            else:
                eligibility_score += 10
                eligibility_reasons.append("No collateral required")
            
            # Classify as eligible if score >= 60/100
            product_with_score = {
                **product,
                'eligibility_score': eligibility_score,
                'eligibility_percentage': round(eligibility_score, 1),
                'eligibility_reasons': eligibility_reasons,
                'ineligibility_reasons': ineligibility_reasons,
                'recommended_amount_range': {
                    'min': max(min_amount, estimated_capacity * 0.1),
                    'max': min(max_amount, estimated_capacity),
                    'suggested': min(max_amount, estimated_capacity * 0.5)
                }
            }
            
            if eligibility_score >= 60:
                eligible_products.append(product_with_score)
            else:
                ineligible_products.append(product_with_score)
        
        # Sort eligible products by score (highest first)
        eligible_products.sort(key=lambda x: x['eligibility_score'], reverse=True)
        ineligible_products.sort(key=lambda x: x['eligibility_score'], reverse=True)
        
        return self._json({
            "client_id": client_id,
            "client_profile": {
                "income_usd": client_income,
                "age": client_age,
                "risk_appetite": client_risk,
                "segment": client_segment,
                "aum": aum,
                "estimated_lending_capacity": client_income * 5 if client_income > 0 else aum * 0.3
            },
            "eligible_products": eligible_products,
            "ineligible_products": ineligible_products,
            "summary": {
                "total_products": len(products),
                "eligible_count": len(eligible_products),
                "ineligible_count": len(ineligible_products)
            }
        })

    # ------------------------------
    # NEW: Focused 6M maturity and KYC expiry tools
    # ------------------------------
    def get_maturing_products_6m(self, client_id: str) -> str:
        # Prefer core.product_balance using customer_number and product hierarchy columns
        items: List[Dict[str, Any]] = []

        def _find_col(candidates: List[str], cols: List[str]) -> str | None:
            lower_map = {c.lower(): c for c in cols}
            for cand in candidates:
                if cand.lower() in lower_map:
                    return lower_map[cand.lower()]
            # fuzzy: contains tokens
            for c in cols:
                lc = c.lower()
                if all(tok in lc for tok in [w for w in candidates[0].lower().replace('_', ' ').split() if w]):
                    return c
            return None

        if self._table_exists("core", "product_balance"):
            cols = self._columns("core", "product_balance")
            customer_col = _find_col(["customer_number", "cif", "customer_no", "client_id"], cols)
            lev1_col = _find_col(["ProductLev1Desc", "product_lev1_desc", "product level1 desc", "product level 1 desc"], cols)
            lev2_col = _find_col(["ProductLev2Desc", "product_lev2_desc", "product level2 desc", "product level 2 desc"], cols)
            lev3_col = _find_col(["ProductLev3Desc", "product_lev3_desc", "product level3 desc", "product level 3 description", "product level 3 desc"], cols)
            maturity_col = _find_col(["maturity_date", "maturitydate", "maturity"], cols)

            if customer_col and lev1_col and lev2_col and lev3_col and maturity_col:
                # Quote identifiers to handle spaces/mixed case
                q_customer = f'"{customer_col}"'
                q_lev1 = f'"{lev1_col}"'
                q_lev2 = f'"{lev2_col}"'
                q_lev3 = f'"{lev3_col}"'
                q_maturity = f'"{maturity_col}"'

                q = (
                    "SELECT "
                    f"  {q_lev1} AS product_level1_desc, "
                    f"  {q_lev2} AS product_level2_desc, "
                    f"  {q_lev3} AS product_level3_desc, "
                    f"  {q_maturity} AS maturity_date "
                    "FROM core.product_balance "
                    f"WHERE LOWER({q_customer}) = LOWER(:cid) "
                    f"  AND {q_maturity} IS NOT NULL "
                    f"  AND {q_maturity} >= CURRENT_DATE "
                    f"  AND {q_maturity} < CURRENT_DATE + INTERVAL '6 months' "
                    f"  AND ( {q_lev1} ILIKE '%LEND%' OR {q_lev1} ILIKE '%LOAN%' OR {q_lev1} = 'LENDING_PRODUCT' ) "
                    f"ORDER BY {q_maturity} ASC"
                )
                items = self._execute_query(q, {"cid": client_id})

        # Fallback to legacy app.maturityopportunity if core.product_balance not available
        if not items:
            maturity_table = None
            for cand in ("maturityopportunity", "maturity_opportunity"):
                if self._table_exists("app", cand):
                    maturity_table = f"app.{cand}"
                    break
            if maturity_table:
                tbl = maturity_table.split(".")[1]
                mcols = set(self._columns("app", tbl))
                category_col = "category" if "category" in mcols else None
                product_col = (
                    "product" if "product" in mcols else (
                        "product_name" if "product_name" in mcols else None
                    )
                )
                maturity_col = "maturity_date" if "maturity_date" in mcols else None
                if category_col and product_col and maturity_col and ("client_id" in mcols):
                    q = (
                        f"SELECT {category_col} AS product_level1_desc, {product_col} AS product_level2_desc, NULL::date AS maturity_date "
                        f"FROM {maturity_table} WHERE LOWER(client_id)=LOWER(:cid) AND {maturity_col} IS NOT NULL "
                        f"AND {maturity_col} >= CURRENT_DATE AND {maturity_col} < CURRENT_DATE + INTERVAL '6 months' "
                        f"ORDER BY {maturity_col} ASC"
                    )
                    items = self._execute_query(q, {"cid": client_id})

        return self._json({
            "client_id": client_id,
            "window": "next_6_months",
            "maturing_products": items,
            "data_source": "core.product_balance" if items else "app.maturityopportunity"
        })

    def get_kyc_expiring_within_6m(self, client_id: str) -> str:
        info: Dict[str, Any] | None = None
        if self._table_exists("app", "client"):
            cols = set(self._columns("app", "client"))
            kyc_col = "kyc_expiry_date" if "kyc_expiry_date" in cols else None
            if kyc_col:
                q = f"SELECT client_id, {kyc_col} AS kyc_expiry_date FROM app.client WHERE LOWER(client_id)=LOWER(:cid) LIMIT 1"
                r = self._execute_query(q, {"cid": client_id})
                info = r[0] if r else None
        return self._json({
            "client_id": client_id,
            "kyc": info,
            "expiry_within_6m": bool(info and info.get("kyc_expiry_date") is not None),
        })

    def get_elite_aecb_alerts(self, client_id: str) -> str:
        rows = self._execute_query(
            """
            SELECT *
            FROM core.aecbalerts
            WHERE LOWER(cif) = LOWER(:cid) OR LOWER(cif2) = LOWER(:cid)
            ORDER BY load_ts DESC NULLS LAST, load_date DESC NULLS LAST
            LIMIT 500
            """,
            {"cid": client_id},
        )
        summary_by_type: Dict[str, Dict[str, float | int]] = {}
        def fnum(v):
            try:
                return float(v)
            except Exception:
                return 0.0
        for a in rows:
            key_raw = (a.get("description_1") or a.get("description") or "").strip()
            key = key_raw or "Unspecified"
            entry = summary_by_type.setdefault(key, {
                "count": 0,
                "total_totalamount": 0.0,
                "total_overdueamount": 0.0,
                "total_billedamount": 0.0,
                "total_bouncedchequeamount": 0.0,
                "total_salarycreditedamount": 0.0,
                "total_directdebitamount": 0.0,
            })
            entry["count"] += 1
            entry["total_totalamount"] += fnum(a.get("totalamount"))
            entry["total_overdueamount"] += fnum(a.get("overdueamount"))
            entry["total_billedamount"] += fnum(a.get("billedamount"))
            entry["total_bouncedchequeamount"] += fnum(a.get("bouncedchequeamount"))
            entry["total_salarycreditedamount"] += fnum(a.get("salarycreditedamount"))
            entry["total_directdebitamount"] += fnum(a.get("directdebitamount"))
        return self._json({
            "client_id": client_id,
            "aecb_alerts": rows,
            "aecb_alerts_summary": summary_by_type,
            "source": "core.aecbalerts",
        })

    def get_elite_loan_data(self, client_id: str) -> str:
        """
        Enhanced loan data with segregated transaction types:
        - Existing loans (Auto, Mortgage, Personal, etc.) from productbalance
        - Loan payment transactions from various transaction tables
        - Credit card transactions and spending
        - AECB credit bureau alerts
        """
        # Credit-related transactions from core.client_transaction (dynamic columns)
        ct_cols = set(self._columns("core", "client_transaction"))
        tx_select = []
        for alias, candidates in [
            ("transaction_id", ["transaction_id", "id"]),
            ("client_id", ["client_id", "customer_id", "cif"]),
            ("transaction_type", ["transaction_type", "type"]),
            ("transaction_amount", ["transaction_amount", "amount", "amount_lcy"]),
            ("date", ["date", "txn_date", "booking_date", "transaction_date"]),
            ("currency", ["currency", "destination_currency", "currency_code"]),
            ("booking_geography", ["booking_geography", "dest_country", "country"]),
            ("name", ["name", "merchant_name", "category_desc"]),
        ]:
            actual = next((c for c in candidates if c in ct_cols), None)
            if actual:
                tx_select.append(f"{actual} AS {alias}")
        credit_txs: list[dict] = []
        if tx_select:
            type_col = "transaction_type" if "transaction_type" in ct_cols else next((c for c in ("type",) if c in ct_cols), None)
            if type_col:
                tx_sql = (
                    f"SELECT {', '.join(tx_select)} FROM core.client_transaction "
                    f"WHERE {('client_id' if 'client_id' in ct_cols else 'customer_id' if 'customer_id' in ct_cols else 'cif')} = :cid "
                    f"AND LOWER({type_col}) IN ('credit','loan','advance','loan payment') "
                    f"ORDER BY {('date' if 'date' in ct_cols else 'txn_date' if 'txn_date' in ct_cols else list(ct_cols)[0])} DESC NULLS LAST LIMIT 200"
                )
                credit_txs = self._execute_query(tx_sql, {"cid": client_id})
        
        # Loan payment transactions from debit (may include loan EMI payments)
        loan_payment_txs: list[dict] = []
        try:
            loan_payment_txs = self._execute_query(
                """SELECT transaction_type, transaction_type_desc, amount, currency,
                          narrative_1, narrative_2, txn_date, product_desc
                   FROM core.clienttransactiondebit 
                   WHERE customer_number=:cid 
                   AND (
                       LOWER(transaction_type_desc) LIKE '%loan%'
                       OR LOWER(transaction_type_desc) LIKE '%mortgage%'
                       OR LOWER(narrative_1) LIKE '%loan%'
                       OR LOWER(narrative_1) LIKE '%mortgage%'
                       OR LOWER(narrative_1) LIKE '%emi%'
                   )
                   ORDER BY txn_date DESC NULLS LAST 
                   LIMIT 100""",
                {"cid": client_id}
            )
        except Exception:
            pass
        
        # Credit card spending patterns
        credit_card_spending: list[dict] = []
        total_credit_spend = 0.0
        try:
            credit_card_txs = self._execute_query(
                """SELECT product_desc, destination_amount, destination_currency,
                          merchant_name, mcc_desc, txn_date
                   FROM core.clienttransactioncredit 
                   WHERE customer_number=:cid 
                   ORDER BY txn_date DESC NULLS LAST 
                   LIMIT 100""",
                {"cid": client_id}
            )
            for tx in credit_card_txs:
                amt = abs(float(tx.get("destination_amount") or 0))
                total_credit_spend += amt
            credit_card_spending = credit_card_txs
        except Exception:
            pass

        # Credit products catalog (try core.credit_products then app.credit_products)
        cat_rows: list[dict] = []
        source_schema = None
        for schema in ("core", "app"):
            tables = self._execute_query(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema=:schema AND table_name='credit_products'
                """,
                {"schema": schema},
            )
            if tables:
                source_schema = schema
                break
        if source_schema:
            ccols = set(self._columns(source_schema, "credit_products"))
            mapped = []
            for alias, candidates in [
                ("product_id", ["product_id", "id"]),
                ("product_name", ["product_name", "name", "product"]),
                ("product_type", ["product_type", "type"]),
                ("typical_rates_min", ["typical_rates_min", "rate_min", "interest_min"]),
                ("typical_rates_max", ["typical_rates_max", "rate_max", "interest_max"]),
                ("loan_amount_min", ["loan_amount_min", "min_amount", "amount_min"]),
                ("loan_amount_max", ["loan_amount_max", "max_amount", "amount_max"]),
                ("term_min_months", ["term_min_months", "term_min", "months_min"]),
                ("term_max_months", ["term_max_months", "term_max", "months_max"]),
                ("interest_type", ["interest_type", "rate_type"]),
                ("collateral_required", ["collateral_required", "collateral"]),
                ("target_segment", ["target_segment", "segment"]),
                ("risk_level", ["risk_level", "risk"]),
            ]:
                actual = next((c for c in candidates if c in ccols), None)
                if actual:
                    mapped.append(f"{actual} AS {alias}")
            if mapped:
                sql = f"SELECT {', '.join(mapped)} FROM {source_schema}.credit_products LIMIT 200"
                cat_rows = self._execute_query(sql)

        # AECB alerts leverage helper
        aecb = self._execute_query(
            """
            SELECT * FROM core.aecbalerts
            WHERE LOWER(cif)=LOWER(:cid) OR LOWER(cif2)=LOWER(:cid)
            ORDER BY load_ts DESC NULLS LAST, load_date DESC NULLS LAST LIMIT 200
            """,
            {"cid": client_id},
        )

        # Profile snippet for segment
        profile = self._execute_query(
            """SELECT customer_profile_banking_segment, risk_appetite, income
                FROM core.client_context WHERE client_id=:cid LIMIT 1""",
            {"cid": client_id},
        )
        segment = (profile[0].get('customer_profile_banking_segment') if profile else None) or 'mass_market'

        # Existing loans from productbalance (Auto Loan, Mortgage, Personal Loan, etc.)
        existing_loans: list[dict] = []
        if self._table_exists("core", "productbalance"):
            pb_cols = set(self._columns("core", "productbalance"))
            select_parts = []
            for alias, candidates in [
                ("customer_number", ["customer_number", "client_id", "customer_id"]),
                ("account_number", ["account_number", "account_no"]),
                ("product_description", ["product_description", "product_name", "product"]),
                ("product_levl1_desc", ["product_levl1_desc", "product_level1"]),
                ("product_levl2_desc", ["product_levl2_desc", "product_level2"]),
                ("product_levl3_desc", ["product_levl3_desc", "product_level3"]),
                ("outstanding", ["outstanding", "balance", "amount"]),
                ("maturity_date", ["maturity_date", "maturity"]),
                ("banking_type", ["banking_type", "type"]),
            ]:
                actual = next((c for c in candidates if c in pb_cols), None)
                if actual:
                    select_parts.append(f"{actual} AS {alias}")
            
            cust_col = "customer_number" if "customer_number" in pb_cols else "client_id" if "client_id" in pb_cols else "customer_id"
            if select_parts and cust_col in pb_cols:
                loan_sql = f"""
                    SELECT {', '.join(select_parts)} 
                    FROM core.productbalance 
                    WHERE {cust_col} = :cid 
                    AND (
                        LOWER(product_levl1_desc) LIKE '%loan%' 
                        OR LOWER(product_levl2_desc) LIKE '%loan%'
                        OR LOWER(product_levl3_desc) LIKE '%loan%'
                        OR LOWER(product_description) LIKE '%loan%'
                        OR LOWER(product_levl1_desc) LIKE '%credit%'
                        OR LOWER(product_levl2_desc) LIKE '%credit%'
                        OR LOWER(product_levl1_desc) LIKE '%lending%'
                    )
                    ORDER BY outstanding DESC NULLS LAST
                    LIMIT 50
                """
                existing_loans = self._execute_query(loan_sql, {"cid": client_id})

        # Categorize existing loans by type
        loans_by_type: Dict[str, list] = {
            "auto_loans": [],
            "mortgage_loans": [],
            "personal_loans": [],
            "credit_cards": [],
            "other_loans": [],
        }
        for loan in existing_loans:
            desc = (loan.get("product_description") or "").lower()
            levl2 = (loan.get("product_levl2_desc") or "").lower()
            if "auto" in desc or "vehicle" in desc or "auto" in levl2 or "vehicle" in levl2:
                loans_by_type["auto_loans"].append(loan)
            elif "mortgage" in desc or "home" in desc or "property" in desc or "mortgage" in levl2:
                loans_by_type["mortgage_loans"].append(loan)
            elif "personal" in desc or "personal" in levl2:
                loans_by_type["personal_loans"].append(loan)
            elif "credit card" in desc or "card" in desc:
                loans_by_type["credit_cards"].append(loan)
            else:
                loans_by_type["other_loans"].append(loan)
        
        return self._json({
            "client_id": client_id,
            "client_segment": segment,
            "existing_loans_summary": {
                "total_loans": len(existing_loans),
                "auto_loans": len(loans_by_type["auto_loans"]),
                "mortgage_loans": len(loans_by_type["mortgage_loans"]),
                "personal_loans": len(loans_by_type["personal_loans"]),
                "credit_cards": len(loans_by_type["credit_cards"]),
                "other_loans": len(loans_by_type["other_loans"]),
            },
            "existing_loans_by_type": loans_by_type,
            "loan_payment_transactions": loan_payment_txs,
            "credit_card_transactions": {
                "transactions": credit_card_spending[:20],
                "total_spend": total_credit_spend,
                "transaction_count": len(credit_card_spending),
            },
            "credit_transactions": credit_txs,
            "aecb_alerts": aecb,
            "credit_products_catalog": cat_rows,
        })

    def get_elite_client_behavior_analysis(self, client_id: str) -> str:
        """
        Enhanced behavior analysis with transaction segregation by category:
        - Trading/Investment transactions (equity, bonds, funds)
        - Loan/Credit transactions (loan payments, credit card)
        - Banking/CASA transactions (deposits, withdrawals, transfers)
        - Spending patterns by merchant category
        """
        # Investment/Trading transactions from client_transaction
        trading_txs = []
        try:
            trading_txs = self._execute_query(
                """SELECT transaction_type, transaction_amount, security_id, name, date
                   FROM core.client_transaction 
                   WHERE client_id=:cid 
                   ORDER BY date DESC NULLS LAST 
                   LIMIT 200""",
                {"cid": client_id}
            )
        except Exception:
            pass
        
        # Banking/Account transactions (handle different date column names)
        banking_txs = []
        if self._table_exists("core", "clienttransactionaccount"):
            try:
                acc_cols = set(self._columns("core", "clienttransactionaccount"))
                date_col = next((c for c in ("txn_date", "transaction_date", "date", "time_key") if c in acc_cols), None)
                order_clause = f"ORDER BY {date_col} DESC NULLS LAST" if date_col else ""
                banking_txs = self._execute_query(
                    f"""SELECT transaction_type, amount_lcy FROM core.clienttransactionaccount 
                       WHERE customer_id=:cid 
                       {order_clause}
                       LIMIT 200""",
                    {"cid": client_id}
                )
            except Exception:
                pass
        
        # Credit card transactions with merchant categories
        credit_txs = []
        try:
            credit_txs = self._execute_query(
                """SELECT product_desc, direction, destination_amount, destination_currency,
                          merchant_name, mcc_desc, txn_date
                   FROM core.clienttransactioncredit 
                   WHERE customer_number=:cid 
                   ORDER BY txn_date DESC NULLS LAST 
                   LIMIT 200""",
                {"cid": client_id}
            )
        except Exception:
            pass
        
        # Debit card transactions with merchant categories
        debit_txs = []
        spending_by_category: Dict[str, Dict[str, float]] = {}
        try:
            debit_txs = self._execute_query(
                """SELECT transaction_type, amount, currency, mcc_desc, 
                          narrative_1, txn_date, product_desc
                   FROM core.clienttransactiondebit 
                   WHERE customer_number=:cid 
                   ORDER BY txn_date DESC NULLS LAST 
                   LIMIT 200""",
                {"cid": client_id}
            )
            # Aggregate spending by merchant category
            for tx in debit_txs:
                category = tx.get("mcc_desc") or "Uncategorized"
                amount = abs(float(tx.get("amount") or 0))
                if category not in spending_by_category:
                    spending_by_category[category] = {"total": 0, "count": 0}
                spending_by_category[category]["total"] += amount
                spending_by_category[category]["count"] += 1
        except Exception:
            pass
        
        # Calculate totals
        total_trading = len(trading_txs)
        total_banking = len(banking_txs)
        total_credit = len(credit_txs)
        total_debit = len(debit_txs)
        total_all = total_trading + total_banking + total_credit + total_debit
        
        # Top spending categories
        top_spending = sorted(
            [{"category": k, "total": v["total"], "count": v["count"]} 
             for k, v in spending_by_category.items()],
            key=lambda x: -x["total"]
        )[:10]
        
        # Transaction type breakdown
        by_type: Dict[str, int] = {}
        for tx in trading_txs:
            t = (tx.get("transaction_type") or "unknown").lower()
            by_type[t] = by_type.get(t, 0) + 1
        for tx in banking_txs:
            t = (tx.get("transaction_type") or "unknown").lower()
            by_type[t] = by_type.get(t, 0) + 1
        for tx in debit_txs:
            t = (tx.get("transaction_type") or "unknown").lower()
            by_type[t] = by_type.get(t, 0) + 1
        
        return self._json({
            "client_id": client_id,
            "transaction_summary": {
                "total_transactions": total_all,
                "trading_investment_count": total_trading,
                "banking_account_count": total_banking,
                "credit_card_count": total_credit,
                "debit_card_count": total_debit,
            },
            "spending_by_merchant_category": top_spending,
            "transaction_types": sorted(by_type.items(), key=lambda x: -x[1])[:10],
            "sample_trading_transactions": trading_txs[:5],
            "sample_debit_transactions": debit_txs[:5],
        })

    # ---------------------------------
    # NEW: Tools required by V5 prompts
    # ---------------------------------

    def get_elite_share_of_potential(self, client_id: str) -> str:
        # dynamic resolve of upsell table
        tables = self._execute_query(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='app' AND table_name IN
                  ('upsellopportunity','upselloppurtunity','upselloppurtunities')
            """
        )
        tset = {r.get('table_name') for r in tables}
        chosen = None
        for cand in ('upsellopportunity','upselloppurtunity','upselloppurtunities'):
            if cand in tset:
                chosen = cand; break
        if not chosen:
            return self._json({"client_id": client_id, "source": None, "opportunities": []})
        rows = self._execute_query(
            f"SELECT client_id, category, delta FROM app.{chosen} WHERE LOWER(client_id)=LOWER(:cid) ORDER BY delta DESC NULLS LAST",
            {"cid": client_id},
        )
        opps = []
        for r in rows:
            opps.append({"product": r.get("category") or r.get("product"), "delta": r.get("delta")})
        return self._json({"client_id": client_id, "source": f"app.{chosen}", "opportunities": opps})

    def get_elite_engagement_analysis(self, client_id: str) -> str:
        # Try a dedicated engagement table if present; else fallback to communication_log stats
        rows: List[Dict[str, Any]] = []
        if self._table_exists("core", "engagement_analysis"):
            ecols = set(self._columns("core", "engagement_analysis"))
            id_where = []
            params = {"cid": client_id}
            for col in ("client_id", "customer_id", "cif", "cif2"):
                if col in ecols:
                    id_where.append(f"LOWER({col})=LOWER(:cid)")
            order_col = "last_update" if "last_update" in ecols else next(iter(ecols), None)
            if id_where and order_col:
                sql = f"SELECT * FROM core.engagement_analysis WHERE (" + " OR ".join(id_where) + f") ORDER BY {order_col} DESC NULLS LAST LIMIT 200"
                rows = self._execute_query(sql, params)
        if not rows and self._table_exists("core", "communication_log"):
            ccols = set(self._columns("core", "communication_log"))
            where = []
            params = {"cid": client_id}
            for col in ("client_id", "customer_id", "cif", "cif2"):
                if col in ccols:
                    where.append(f"LOWER({col})=LOWER(:cid)")
            select_parts = []
            for alias, candidates in [
                ("type", ["type"]),
                ("subtype", ["subtype"]),
                ("status", ["status"]),
                ("communication_date", ["communication_date", "date", "created_ts"]),
            ]:
                actual = next((c for c in candidates if c in ccols), None)
                if actual:
                    select_parts.append(f"{actual} AS {alias}")
            order_col = next((c for c in ("communication_date", "date", "created_ts") if c in ccols), None)
            if where and select_parts:
                sql = (
                    f"SELECT {', '.join(select_parts)} FROM core.communication_log WHERE (" + " OR ".join(where) + ") "
                    + (f"ORDER BY {order_col} DESC NULLS LAST " if order_col else "")
                    + "LIMIT 500"
                )
                rows = self._execute_query(sql, params)
        by_type: Dict[str,int] = {}
        for r in rows:
            t = (r.get("type") or "").lower()
            by_type[t] = by_type.get(t,0)+1
        return self._json({"client_id": client_id, "engagement_events": rows, "by_type": by_type})

    def get_elite_communication_history(self, client_id: str) -> str:
        """
        Fetch comprehensive communication history from multiple sources:
        1. core.communication_log - structured communication records
        2. core.callreport - detailed call/meeting reports with transcripts
        """
        all_communications = []
        params = {"cid": client_id}
        
        # Source 1: communication_log
        if self._table_exists("core", "communication_log"):
            ccols = set(self._columns("core", "communication_log"))
            select_parts = []
            for alias, candidates in [
                ("comm_log_id", ["comm_log_id", "id"]),
                ("type", ["type"]),
                ("subtype", ["subtype"]),
                ("description", ["description", "notes", "details"]),
                ("status", ["status"]),
                ("communication_date", ["communication_date", "date", "created_ts"]),
                ("channel", ["channel", "meeting_channel", "meeting_type"]),
            ]:
                actual = next((c for c in candidates if c in ccols), None)
                if actual:
                    select_parts.append(f"{actual} AS {alias}")
            where_parts = []
            for col in ("client_id", "customer_id", "cif", "cif2"):
                if col in ccols:
                    where_parts.append(f"LOWER({col})=LOWER(:cid)")
            order_col = next((c for c in ("communication_date", "date", "created_ts") if c in ccols), None)
            if select_parts and where_parts:
                sql = (
                    f"SELECT 'communication_log' as source, {', '.join(select_parts)} "
                    f"FROM core.communication_log WHERE ({' OR '.join(where_parts)}) "
                    + (f"ORDER BY {order_col} DESC NULLS LAST " if order_col else "")
                    + "LIMIT 100"
                )
                comm_log_rows = self._execute_query(sql, params)
                all_communications.extend(comm_log_rows)
        
        # Source 2: callreport (detailed call/meeting reports)
        if self._table_exists("core", "callreport"):
            call_cols = set(self._columns("core", "callreport"))
            # Build dynamic select for callreport
            call_select = ["'callreport' as source"]
            
            # Map callreport columns to standardized names
            if "call_report_id" in call_cols:
                call_select.append("call_report_id as comm_log_id")
            if "purpose" in call_cols:
                call_select.append("purpose as type")
            if "meeting_type" in call_cols:
                call_select.append("meeting_type as subtype")
            
            # Description: combine multiple fields
            desc_parts = []
            if "points_discussed" in call_cols:
                desc_parts.append("points_discussed")
            if "background_meeting_objective" in call_cols:
                desc_parts.append("background_meeting_objective")
            if "areas_of_opportunities" in call_cols:
                desc_parts.append("areas_of_opportunities")
            
            if desc_parts:
                call_select.append(f"CONCAT_WS(' | ', {', '.join(desc_parts)}) as description")
            else:
                call_select.append("NULL as description")
            
            call_select.append("'completed' as status")  # Default status for calls
            
            # Date
            if "call_ts" in call_cols:
                call_select.append("call_ts as communication_date")
            elif "date_id" in call_cols:
                call_select.append("date_id as communication_date")
            
            # Channel
            if "meeting_channel" in call_cols:
                call_select.append("meeting_channel as channel")
            else:
                call_select.append("NULL as channel")
            
            # Add transcript if available
            if "call_transcript" in call_cols:
                call_select.append("SUBSTRING(call_transcript, 1, 500) as transcript_preview")
            
            # Find client ID column
            client_col = None
            for col in ("client_id", "customer_id", "cif", "cif2"):
                if col in call_cols:
                    client_col = col
                    break
            
            if client_col:
                sql = (
                    f"SELECT {', '.join(call_select)} "
                    f"FROM core.callreport "
                    f"WHERE LOWER({client_col})=LOWER(:cid) "
                    f"ORDER BY {('call_ts' if 'call_ts' in call_cols else 'date_id')} DESC NULLS LAST "
                    "LIMIT 100"
                )
                call_rows = self._execute_query(sql, params)
                all_communications.extend(call_rows)
        
        # Sort all communications by date (most recent first)
        all_communications.sort(
            key=lambda x: x.get('communication_date') or '', 
            reverse=True
        )
        
        return self._json({
            "client_id": client_id, 
            "total_communications": len(all_communications),
            "sources": {
                "communication_log": sum(1 for c in all_communications if c.get('source') == 'communication_log'),
                "callreport": sum(1 for c in all_communications if c.get('source') == 'callreport'),
            },
            "communications": all_communications[:200]  # Limit to 200 most recent
        })

    def get_rm_details(self, client_id: str) -> str:
        """
        Dedicated function to fetch RM ID and details for a client.
        Checks multiple tables to find the RM assignment.
        """
        rm_id = None
        rm_name = None
        relation_type = None
        
        # Primary source: user_join_client_context (correct table name)
        if self._table_exists("core", "user_join_client_context"):
            result = self._execute_query(
                """
                SELECT rm_id, relation_type 
                FROM core.user_join_client_context 
                WHERE LOWER(client_id)=LOWER(:cid) 
                LIMIT 1
                """,
                {"cid": client_id},
            )
            if result:
                rm_id = result[0].get("rm_id")
                relation_type = result[0].get("relation_type")
        
        # If RM ID found, get RM details from users or rm_portfolio
        if rm_id:
            if self._table_exists("core", "users"):
                rm_info = self._execute_query(
                    "SELECT rm_id, first_name, last_name FROM core.users WHERE rm_id=:rmid LIMIT 1",
                    {"rmid": rm_id},
                )
                if rm_info:
                    rm_name = f"{rm_info[0].get('first_name', '')} {rm_info[0].get('last_name', '')}".strip()
            
            # If not in users, try rm_portfolio
            if not rm_name and self._table_exists("core", "rm_portfolio"):
                rm_info = self._execute_query(
                    "SELECT rm_id, first_name, last_name FROM core.rm_portfolio WHERE rm_id=:rmid LIMIT 1",
                    {"rmid": rm_id},
                )
                if rm_info:
                    rm_name = f"{rm_info[0].get('first_name', '')} {rm_info[0].get('last_name', '')}".strip()
        
        return self._json({
            "client_id": client_id,
            "rm_id": rm_id,
            "rm_name": rm_name,
            "relation_type": relation_type,
            "source": "core.user_join_client_context" if rm_id else None,
        })

    def get_elite_rm_strategy(self, client_id: str) -> str:
        # Try to identify RM and summarize client AUM + recent communications
        rm_id = None
        rm_name = None
        
        # Use the correct table name: user_join_client_context (not user_client_join_client_context)
        if self._table_exists("core", "user_join_client_context"):
            result = self._execute_query(
                "SELECT rm_id FROM core.user_join_client_context WHERE LOWER(client_id)=LOWER(:cid) LIMIT 1",
                {"cid": client_id},
            )
            if result:
                rm_id = result[0].get("rm_id")
                
                # Get RM name from users table
                if rm_id and self._table_exists("core", "users"):
                    rm_info = self._execute_query(
                        "SELECT first_name, last_name FROM core.users WHERE rm_id=:rmid LIMIT 1",
                        {"rmid": rm_id},
                    )
                    if rm_info:
                        rm_name = f"{rm_info[0].get('first_name', '')} {rm_info[0].get('last_name', '')}".strip()
        
        aum_row = self._execute_query(
            "SELECT aum FROM core.client_portfolio WHERE client_id=:cid ORDER BY last_valuation_date DESC NULLS LAST LIMIT 1",
            {"cid": client_id},
        )
        comms = self._execute_query(
            "SELECT type, status, communication_date FROM core.communication_log WHERE client_id=:cid ORDER BY communication_date DESC NULLS LAST LIMIT 50",
            {"cid": client_id},
        )
        return self._json({
            "client_id": client_id,
            "rm_id": rm_id,
            "rm_name": rm_name,
            "client_aum": (aum_row[0].get("aum") if aum_row else None),
            "recent_comms": comms,
        })

    # ============================================================================
    # BANCASSURANCE TOOLS
    # ============================================================================
    
    def get_elite_bancassurance_holdings(self, client_id: str) -> str:
        """
        Get client's existing bancassurance policies from core.bancaclientproduct.
        Returns current policy holdings with values and types.
        """
        if not self._table_exists("core", "bancaclientproduct"):
            return self._json({
                "client_id": client_id,
                "error": "bancaclientproduct table not found",
                "holdings": []
            })
        
        # Get client's existing policies
        holdings = self._execute_query(
            """
            SELECT 
                client_id,
                policy_number,
                policy_type,
                mkt_val_aed,
                time_key
            FROM core.bancaclientproduct
            WHERE LOWER(client_id) = LOWER(:cid)
            ORDER BY mkt_val_aed DESC NULLS LAST
            """,
            {"cid": client_id}
        )
        
        # Get policy type mapping for categorization
        policy_mapping = {}
        if self._table_exists("core", "bancapolicymapping"):
            mappings = self._execute_query(
                """
                SELECT policy_type, policy_type_mapped 
                FROM core.bancapolicymapping
                """
            )
            policy_mapping = {m.get("policy_type"): m.get("policy_type_mapped") for m in mappings}
        
        # Enrich holdings with mapped categories
        for holding in holdings:
            policy_type = holding.get("policy_type")
            holding["policy_category"] = policy_mapping.get(policy_type, "Other")
        
        # Calculate summary statistics
        total_value = sum(h.get("mkt_val_aed", 0) or 0 for h in holdings)
        policy_count = len(holdings)
        
        # Get unique policy types held
        policy_types_held = list(set(h.get("policy_type") for h in holdings if h.get("policy_type")))
        
        return self._json({
            "client_id": client_id,
            "summary": {
                "total_policies": policy_count,
                "total_value_aed": total_value,
                "policy_types_held": policy_types_held,
            },
            "holdings": holdings,
            "data_source": "core.bancaclientproduct"
        })
    
    def get_elite_bancassurance_ml_propensity(self, client_id: str) -> str:
        """
        Get ML-generated bancassurance propensity and need indicators from 
        core.prompt_ml_banca_full_potential.
        Returns insurance needs and triggers for product recommendations.
        """
        if not self._table_exists("core", "prompt_ml_banca_full_potential"):
            return self._json({
                "client_id": client_id,
                "error": "prompt_ml_banca_full_potential table not found",
                "needs": {}
            })
        
        # Get ML propensity data
        propensity_data = self._execute_query(
            """
            SELECT *
            FROM core.prompt_ml_banca_full_potential
            WHERE LOWER(client_id) = LOWER(:cid)
            LIMIT 1
            """,
            {"cid": client_id}
        )
        
        if not propensity_data:
            return self._json({
                "client_id": client_id,
                "has_propensity_data": False,
                "message": "No ML propensity data available for this client",
                "needs": {}
            })
        
        data = propensity_data[0]
        
        # Extract need indicators
        needs = {
            "funds_accumulation": data.get("funds_accumulation", 0),
            "financial_protection": data.get("financial_protection", 0),
            "house_purchase_planning": data.get("house_purchase_planning", 0),
            "kids_future_planning": data.get("kids_future_planning", 0),
            "early_retirement_planning": data.get("early_retirement_planning", 0),
            "wealth_growth": data.get("wealth_growth", 0),
            "retirement_planning": data.get("retirement_planning", 0),
            "health_prevention": data.get("health_prevention", 0),
            "wealth_preservation": data.get("wealth_preservation", 0),
            "legacy_planning": data.get("legacy_planning", 0),
        }
        
        # Identify active needs (value = 1)
        active_needs = [need_name for need_name, value in needs.items() if value == 1]
        
        # Map needs to product categories
        need_to_product_map = {
            "wealth_growth": ["Investment-Linked", "ULIP"],
            "financial_protection": ["Term Life", "Protection", "Whole Life"],
            "retirement_planning": ["Pension", "Endowment", "Retirement"],
            "health_prevention": ["Health", "Critical Illness", "Medical"],
            "wealth_preservation": ["Whole Life", "Endowment"],
            "legacy_planning": ["Whole Life", "Estate Planning"],
            "funds_accumulation": ["Savings", "Investment-Linked"],
            "kids_future_planning": ["Child Plans", "Education"],
            "house_purchase_planning": ["Mortgage Protection"],
            "early_retirement_planning": ["Pension", "Early Retirement"],
        }
        
        recommended_categories = []
        for need in active_needs:
            recommended_categories.extend(need_to_product_map.get(need, []))
        recommended_categories = list(set(recommended_categories))  # Remove duplicates
        
        return self._json({
            "client_id": client_id,
            "has_propensity_data": True,
            "age_segment": data.get("age_segment"),
            "potential_insurance_client": bool(data.get("potential_insurance_clients")),
            "needs": needs,
            "active_needs": active_needs,
            "active_needs_count": len(active_needs),
            "recommended_product_categories": recommended_categories,
            "data_source": "core.prompt_ml_banca_full_potential (ML-generated)"
        })
    
    def get_elite_bancassurance_lifecycle_triggers(self, client_id: str) -> str:
        """
        Analyze client lifecycle events and patterns that trigger bancassurance needs.
        Includes: birthday proximity, age milestones, spending patterns, life events.
        """
        from datetime import datetime, timedelta
        
        # Get client basic data
        client_data = self._execute_query(
            """
            SELECT 
                client_id, first_name, last_name, dob, age, gender,
                family, income, customer_profile_banking_segment,
                customer_profile_subsegment
            FROM core.client_context
            WHERE LOWER(client_id) = LOWER(:cid)
            LIMIT 1
            """,
            {"cid": client_id}
        )
        
        if not client_data:
            return self._json({
                "client_id": client_id,
                "error": "Client data not found",
                "triggers": []
            })
        
        client = client_data[0]
        triggers = []
        
        # 1. Birthday Proximity Trigger
        dob = client.get("dob")
        if dob:
            try:
                if isinstance(dob, str):
                    dob = datetime.strptime(dob, "%Y-%m-%d")
                
                today = datetime.now()
                # Get next birthday
                this_year_birthday = dob.replace(year=today.year)
                if this_year_birthday < today:
                    next_birthday = dob.replace(year=today.year + 1)
                else:
                    next_birthday = this_year_birthday
                
                days_to_birthday = (next_birthday - today).days
                
                if days_to_birthday <= 60:
                    triggers.append({
                        "trigger_type": "Birthday Proximity",
                        "priority": "HIGH",
                        "days_to_event": days_to_birthday,
                        "description": f"Birthday in {days_to_birthday} days - ideal time for life insurance discussion",
                        "recommended_products": ["Life Insurance", "Protection Plans", "Health Insurance"],
                        "talking_point": f"With your birthday approaching, it's a perfect time to review your life insurance coverage."
                    })
            except:
                pass
        
        # 2. Age Milestone Triggers
        age = client.get("age")
        if age:
            age_triggers = []
            if 40 <= age <= 42:
                age_triggers.append({
                    "trigger_type": "Age Milestone",
                    "priority": "HIGH",
                    "milestone": "Age 40+",
                    "description": "Critical age for health insurance and life protection",
                    "recommended_products": ["Critical Illness Insurance", "Health Insurance", "Life Insurance"],
                    "talking_point": "At your age, health insurance becomes increasingly important for comprehensive protection."
                })
            if 45 <= age <= 47:
                age_triggers.append({
                    "trigger_type": "Age Milestone",
                    "priority": "MEDIUM",
                    "milestone": "Mid-40s (Empty Nesters approaching)",
                    "description": "Transition to wealth preservation and retirement planning",
                    "recommended_products": ["Retirement Plans", "Wealth Preservation Products"],
                    "talking_point": "As you approach your empty-nester years, let's ensure your wealth is working for your retirement."
                })
            if 50 <= age <= 52:
                age_triggers.append({
                    "trigger_type": "Age Milestone",
                    "priority": "HIGH",
                    "milestone": "Age 50+",
                    "description": "Critical retirement planning window",
                    "recommended_products": ["Pension Plans", "Retirement Savings", "Legacy Planning"],
                    "talking_point": "With retirement on the horizon, now is the time to maximize your pension and savings plans."
                })
            if age >= 55:
                age_triggers.append({
                    "trigger_type": "Age Milestone",
                    "priority": "HIGH",
                    "milestone": "Pre-Retirement",
                    "description": "Retirement imminent - focus on income generation and legacy",
                    "recommended_products": ["Annuities", "Legacy Planning", "Wealth Transfer"],
                    "talking_point": "Let's ensure your retirement income and legacy plans are optimized."
                })
            
            triggers.extend(age_triggers)
        
        # 3. Family Status Triggers
        family = client.get("family")
        if family:
            if "married" in str(family).lower():
                triggers.append({
                    "trigger_type": "Family Status",
                    "priority": "MEDIUM",
                    "status": "Married",
                    "description": "Family protection needs",
                    "recommended_products": ["Life Insurance", "Family Protection", "Joint Cover"],
                    "talking_point": "Protecting your family's financial future is essential."
                })
            if "child" in str(family).lower() or "kid" in str(family).lower():
                triggers.append({
                    "trigger_type": "Family Status",
                    "priority": "HIGH",
                    "status": "Has Children",
                    "description": "Children's future and education planning",
                    "recommended_products": ["Education Plans", "Child Insurance", "Life Protection"],
                    "talking_point": "Secure your children's education and future with dedicated insurance plans."
                })
        
        # 4. Income Level Triggers
        income = client.get("income")
        if income:
            if income >= 200000:  # High income
                triggers.append({
                    "trigger_type": "Income Level",
                    "priority": "HIGH",
                    "income_bracket": "High Income (AED 200K+)",
                    "description": "Eligible for premium insurance products",
                    "recommended_products": ["Investment-Linked Insurance", "Premium Protection", "Wealth Accumulation"],
                    "talking_point": "Your income profile qualifies you for our premium insurance products with enhanced benefits."
                })
        
        # 5. Banking Segment Triggers
        segment = client.get("customer_profile_banking_segment")
        if segment:
            if "wealth" in str(segment).lower() or "priority" in str(segment).lower():
                triggers.append({
                    "trigger_type": "Banking Segment",
                    "priority": "HIGH",
                    "segment": segment,
                    "description": "Premium segment - comprehensive insurance suite needed",
                    "recommended_products": ["Full Insurance Portfolio", "Investment-Linked", "Legacy Planning"],
                    "talking_point": "As a wealth client, a comprehensive insurance portfolio complements your financial strategy."
                })
        
        # 6. No Existing Bancassurance (Gap Trigger)
        existing_policies = self._execute_query(
            """
            SELECT COUNT(*) as policy_count
            FROM core.bancaclientproduct
            WHERE LOWER(client_id) = LOWER(:cid)
            """,
            {"cid": client_id}
        )
        
        if existing_policies and existing_policies[0].get("policy_count", 0) == 0:
            triggers.append({
                "trigger_type": "Coverage Gap",
                "priority": "HIGH",
                "gap": "No Existing Insurance",
                "description": "Client has no bancassurance coverage - major opportunity",
                "recommended_products": ["Core Protection Package", "Life Insurance", "Investment-Linked"],
                "talking_point": "You currently don't have any insurance protection with us. Let me show you comprehensive solutions."
            })
        
        return self._json({
            "client_id": client_id,
            "client_name": f"{client.get('first_name', '')} {client.get('last_name', '')}".strip(),
            "age": age,
            "lifecycle_triggers": triggers,
            "total_triggers": len(triggers),
            "high_priority_count": sum(1 for t in triggers if t.get("priority") == "HIGH"),
            "data_sources": ["core.client_context", "core.client_transaction", "core.bancaclientproduct"]
        })
    
    def get_elite_bancassurance_gap_analysis(self, client_id: str) -> str:
        """
        Comprehensive gap analysis: identifies bancassurance products client does NOT hold
        vs. what they should have based on ML propensity and lifecycle stage.
        """
        # Get existing holdings
        holdings_raw = self.get_elite_bancassurance_holdings(client_id)
        holdings_data = json.loads(holdings_raw)
        
        # Get ML propensity
        propensity_raw = self.get_elite_bancassurance_ml_propensity(client_id)
        propensity_data = json.loads(propensity_raw)
        
        # Get all available policy types from database
        all_policy_types = []
        if self._table_exists("core", "bancapolicymapping"):
            policy_types_data = self._execute_query(
                """
                SELECT DISTINCT policy_type, policy_type_mapped 
                FROM core.bancapolicymapping
                ORDER BY policy_type_mapped, policy_type
                """
            )
            all_policy_types = policy_types_data
        
        # Get what client already has
        held_policy_types = set(holdings_data.get("summary", {}).get("policy_types_held", []))
        
        # Get recommended categories from ML
        recommended_categories = propensity_data.get("recommended_product_categories", [])
        
        # Identify gaps: policy types client doesn't have but are recommended
        gaps = []
        for policy_data in all_policy_types:
            policy_type = policy_data.get("policy_type")
            policy_category = policy_data.get("policy_type_mapped", "Other")
            
            # Check if client doesn't have this policy type
            if policy_type not in held_policy_types:
                # Check if this category is recommended
                is_recommended = any(rec_cat.lower() in policy_category.lower() 
                                    for rec_cat in recommended_categories)
                
                if is_recommended or not held_policy_types:  # Show all if no holdings
                    gaps.append({
                        "policy_type": policy_type,
                        "policy_category": policy_category,
                        "recommended_by_ml": is_recommended,
                        "status": "Not Held"
                    })
        
        # Prioritize gaps
        priority_gaps = [g for g in gaps if g.get("recommended_by_ml")]
        other_gaps = [g for g in gaps if not g.get("recommended_by_ml")]
        
        return self._json({
            "client_id": client_id,
            "gap_analysis": {
                "total_gaps": len(gaps),
                "priority_gaps_count": len(priority_gaps),
                "priority_gaps": priority_gaps[:10],  # Top 10 priority
                "other_opportunities": other_gaps[:10],  # Top 10 other
            },
            "current_holdings_count": len(held_policy_types),
            "ml_recommended_categories": recommended_categories,
            "recommendation": "HIGH OPPORTUNITY - No existing coverage" if not held_policy_types else "Cross-sell opportunities identified",
            "data_sources": ["core.bancaclientproduct", "core.bancapolicymapping", "core.prompt_ml_banca_full_potential"]
        })


db = EliteDatabaseManagerV6()


# Tools
@function_tool
def get_elite_client_data(client_id: str) -> str:
    return db.get_elite_client_data(client_id)


@function_tool
def get_elite_client_investments_summary(client_id: str) -> str:
    return db.get_elite_client_investments_summary(client_id)


@function_tool
def get_elite_investment_products_not_held(client_id: str) -> str:
    """Get list of investment products (funds, bonds, stocks) that client does NOT currently hold."""
    return db.get_elite_investment_products_not_held(client_id)


@function_tool
def get_elite_banking_casa_data(client_id: str) -> str:
    return db.get_elite_banking_casa_data(client_id)


@function_tool
def get_elite_risk_compliance_data(client_id: str) -> str:
    return db.get_elite_risk_compliance_data(client_id)


@function_tool
def get_elite_recommended_actions_data(client_id: str) -> str:
    return db.get_elite_recommended_actions_data(client_id)


@function_tool
def get_funds_catalog() -> str:
    return db.get_funds_catalog()


@function_tool
def get_bonds_catalog() -> str:
    return db.get_bonds_catalog()


@function_tool
def get_stocks_catalog() -> str:
    return db.get_stocks_catalog()


@function_tool
def get_loan_products_catalog() -> str:
    """Get comprehensive catalog of all available loan/credit products."""
    return db.get_loan_products_catalog()


@function_tool
def get_eligible_loan_products(client_id: str) -> str:
    """Get loan products that client is ELIGIBLE for with eligibility scores and reasons."""
    return db.get_eligible_loan_products(client_id)


@function_tool
def get_elite_aecb_alerts(client_id: str) -> str:
    return db.get_elite_aecb_alerts(client_id)

@function_tool
def get_elite_loan_data(client_id: str) -> str:
    return db.get_elite_loan_data(client_id)

@function_tool
def get_elite_client_behavior_analysis(client_id: str) -> str:
    return db.get_elite_client_behavior_analysis(client_id)

@function_tool
def get_elite_share_of_potential(client_id: str) -> str:
    return db.get_elite_share_of_potential(client_id)

@function_tool
def get_elite_bancassurance_holdings(client_id: str) -> str:
    """Get client's existing bancassurance policies with values and types."""
    return db.get_elite_bancassurance_holdings(client_id)

@function_tool
def get_elite_bancassurance_ml_propensity(client_id: str) -> str:
    """Get ML-generated insurance needs and propensity triggers."""
    return db.get_elite_bancassurance_ml_propensity(client_id)

@function_tool
def get_elite_bancassurance_lifecycle_triggers(client_id: str) -> str:
    """Analyze lifecycle events: birthday, age milestones, spending patterns, life events."""
    return db.get_elite_bancassurance_lifecycle_triggers(client_id)

@function_tool
def get_elite_bancassurance_gap_analysis(client_id: str) -> str:
    """Identify bancassurance products client doesn't hold vs. what they should have."""
    return db.get_elite_bancassurance_gap_analysis(client_id)

@function_tool
def get_elite_engagement_analysis(client_id: str) -> str:
    return db.get_elite_engagement_analysis(client_id)

@function_tool
def get_elite_communication_history(client_id: str) -> str:
    return db.get_elite_communication_history(client_id)

@function_tool
def get_rm_details(client_id: str) -> str:
    """Get RM ID, name and relationship details for a client."""
    return db.get_rm_details(client_id)

@function_tool
def get_elite_rm_strategy(client_id: str) -> str:
    return db.get_elite_rm_strategy(client_id)

@function_tool
def get_maturing_products_6m(client_id: str) -> str:
    return db.get_maturing_products_6m(client_id)

@function_tool
def get_kyc_expiring_within_6m(client_id: str) -> str:
    return db.get_kyc_expiring_within_6m(client_id)


def create_elite_agents() -> Dict[str, Agent]:
    # Use GPT-5 as requested
    model = "gpt-5"

    manager = Agent(
        name="Elite_Manager_V6",
        instructions=ELITE_MANAGER_AGENT_PROMPT_V5,
        tools=[
            get_elite_client_data,
            get_rm_details,  # Get RM ID and details
            get_elite_share_of_potential,
            get_elite_client_behavior_analysis,
            get_elite_banking_casa_data,
            get_elite_engagement_analysis,
            get_elite_communication_history,
            get_elite_client_investments_summary,
            get_elite_bancassurance_holdings,  # Bancassurance holdings summary
            get_elite_recommended_actions_data,
            get_elite_aecb_alerts,
            get_maturing_products_6m,
            get_kyc_expiring_within_6m,
        ],
        model=model,
        output_type=ManagerAgentOutput,  # ✨ Structured Pydantic output
    )

    investment = Agent(
        name="Elite_Investment_Expert_V6",
        instructions=ELITE_INVESTMENT_AGENT_PROMPT_V5,
        tools=[
            get_elite_client_data,
            get_elite_client_investments_summary,  # Consolidated function with ALL investment data
            get_elite_investment_products_not_held,  # Products client has NOT invested in
            get_elite_share_of_potential,  # Share of potential / upsell opportunities
            get_funds_catalog,
            get_bonds_catalog,
            get_stocks_catalog,
        ],
        model=model,
        output_type=InvestmentAgentOutput,  # ✨ Structured Pydantic output
    )

    loan = Agent(
        name="Elite_Loan_Expert_V6",
        instructions=ELITE_LOAN_AGENT_PROMPT_V5,
        tools=[
            get_elite_loan_data,
            get_elite_client_data,
            get_elite_client_behavior_analysis,
            get_elite_risk_compliance_data,
            get_elite_banking_casa_data,
            get_eligible_loan_products,  # ✅ ELIGIBILITY-FILTERED products (replaces catalog)
            get_loan_products_catalog,  # Full catalog for reference if needed
        ],
        model=model,
        output_type=LoanAgentOutput,  # ✨ Structured Pydantic output
    )

    banking = Agent(
        name="Elite_BankingCASA_Expert_V6",
        instructions=ELITE_BANKING_CASA_AGENT_PROMPT_V5,
        tools=[get_elite_banking_casa_data, get_elite_client_data],
        model=model,
        output_type=BankingAgentOutput,  # ✨ Structured Pydantic output
    )

    risk = Agent(
        name="Elite_Risk_Compliance_Expert_V6",
        instructions=ELITE_RISK_COMPLIANCE_AGENT_PROMPT_V5,
        tools=[get_elite_risk_compliance_data, get_elite_client_data],
        model=model,
        output_type=RiskComplianceAgentOutput,  # ✨ Structured Pydantic output
    )

    # Bancassurance Agent - Lifecycle + Gap Analysis
    bancassurance = Agent(
        name="Elite_Bancassurance_Expert_V6",
        instructions=ELITE_BANCASSURANCE_AGENT_PROMPT_V5,
        tools=[
            get_elite_bancassurance_holdings,  # Current policies
            get_elite_bancassurance_ml_propensity,  # ML needs
            get_elite_bancassurance_lifecycle_triggers,  # Time-sensitive triggers
            get_elite_bancassurance_gap_analysis,  # Gap: has vs should have
        ],
        model=model,
        # Disable strict JSON schema for this agent to allow additional properties from model output
        output_type=AgentOutputSchema(BancassuranceAgentOutput, strict_json_schema=False),  # ✨ Structured Pydantic output
    )

    # RM Strategy Agent - NO TOOLS, receives output from all other agents
    rm_strategy = Agent(
        name="Elite_RM_Strategy_Advisor_V6",
        instructions=ELITE_RM_STRATEGY_AGENT_PROMPT_V5,
        tools=[],  # NO TOOLS - works only with agent outputs
        model=model,
        output_type=RMStrategyAgentOutput,  # ✨ Structured Pydantic output
    )

    return {
        "manager": manager, 
        "investment": investment, 
        "loan": loan, 
        "banking": banking, 
        "risk": risk,
        "bancassurance": bancassurance,
        "rm_strategy": rm_strategy
    }


def main(client_id: str | None = None):
    """
    Main execution function - runs agents sequentially with structured outputs and timing.
    
    Execution Flow:
    1. Manager Agent
    2. Risk & Compliance Agent
    3. Investment Agent
    4. Loan Agent  
    5. Banking/CASA Agent
    6. Bancassurance Agent
    7. RM Strategy Agent (synthesizes all outputs)
    
    All agents run sequentially with comprehensive timing metrics.
    Clean, readable flow with utilities extracted to utils.py
    """
    # Print fancy header
    print("\n" + "="*100)
    print("🚀 ELITEX V6 - MULTI-AGENT FINANCIAL ANALYSIS SYSTEM".center(100))
    print("="*100)
    print(f"⏰ Analysis Started: {datetime.now().strftime('%B %d, %Y at %I:%M:%S %p')}")
    print("="*100 + "\n")
    
    # Start overall timer
    overall_start_time = time.time()
    execution_metrics = {
        "start_time": datetime.now().isoformat(),
        "agent_timings": {},
    }
    
    # Step 1: Create all agents
    print("🔧 Initializing AI Agents...")
    agents = create_elite_agents()
    print("✅ All 7 agents initialized successfully\n")

    # Step 2: Resolve and validate client
    print("🔍 Resolving client information...")
    client_id = _resolve_client_id(client_id)
    print(f"✅ Client {client_id} validated\n")
    
    # Step 3: Setup output paths
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create client-specific output folder
    client_output_dir = OUTPUT_DIR / f"client_{client_id}_{timestamp}"
    client_output_dir.mkdir(exist_ok=True)
    print(f"📁 Output folder created: {client_output_dir}\n")
    
    # Setup file paths
    readable_output_path = client_output_dir / f"Elite_Analysis_Report.txt"
    combined_json_path = client_output_dir / f"all_agents_combined.json"
    
    # Step 4: Progress Bar Setup
    total_agents = 7
    completed_agents = 0
    
    def print_progress_bar(current, total, agent_name="", bar_length=50):
        """Print a fancy progress bar"""
        percent = float(current) / total
        filled_length = int(bar_length * percent)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        print(f"\r📊 Overall Progress: |{bar}| {current}/{total} agents ({percent*100:.0f}%) - {agent_name}", end='', flush=True)
    
    print("\n" + "="*100)
    print("🔄 STARTING AGENT EXECUTION PIPELINE".center(100))
    print("="*100)
    print_progress_bar(completed_agents, total_agents, "Initializing...")
    
    # Step 5: Execute all agents and write outputs
    agent_outputs = {}
        
    # ============================================================================
    # STEP 1: Manager Agent
    # ============================================================================
    print("\n")
    completed_agents += 1
    print_progress_bar(completed_agents, total_agents, "Manager Agent Running...")
    
    manager_output, manager_time = _run_manager_agent(agents["manager"], client_id)
    agent_outputs["manager"] = manager_output
    execution_metrics["agent_timings"]["manager"] = manager_time
    
    # Save individual JSON
    with open(client_output_dir / "1_manager_agent.json", "w") as jf:
        jf.write(manager_output.model_dump_json(indent=2))
    print(f"💾 Saved: 1_manager_agent.json")
    
    manager_json = manager_output.model_dump_json(indent=2)
    print_progress_bar(completed_agents, total_agents, "Manager Agent Complete ✓")
        
    # ============================================================================
    # STEP 2: Risk & Compliance Agent
    # ============================================================================
    print("\n")
    completed_agents += 1
    print_progress_bar(completed_agents, total_agents, "Risk Agent Running...")
    
    risk_output, risk_time = _run_risk_agent(agents["risk"], client_id, manager_json)
    agent_outputs["risk"] = risk_output
    execution_metrics["agent_timings"]["risk"] = risk_time
    
    # Save individual JSON
    with open(client_output_dir / "2_risk_compliance_agent.json", "w") as jf:
        jf.write(risk_output.model_dump_json(indent=2))
    print(f"💾 Saved: 2_risk_compliance_agent.json")
    
    risk_json = risk_output.model_dump_json(indent=2)
    
    # Build combined context for specialist agents
    combined_context = f"MANAGER CONTEXT:\n{manager_json}\n\nRISK & COMPLIANCE CONTEXT:\n{risk_json}\n"
    print_progress_bar(completed_agents, total_agents, "Risk Agent Complete ✓")
        
    # ============================================================================
    # STEP 3: Investment Agent
    # ============================================================================
    print("\n")
    completed_agents += 1
    print_progress_bar(completed_agents, total_agents, "Investment Agent Running...")
    
    investment_output, investment_time = _run_specialist_agent(
        agents["investment"], "Investment", client_id, combined_context,
        task_description="Portfolio analysis, asset allocation review, and investment product recommendations",
        emoji="📈"
    )
    agent_outputs["investment"] = investment_output
    execution_metrics["agent_timings"]["investment"] = investment_time
    
    # Save individual JSON
    with open(client_output_dir / "3_investment_agent.json", "w") as jf:
        jf.write(investment_output.model_dump_json(indent=2))
    print(f"💾 Saved: 3_investment_agent.json")
    print_progress_bar(completed_agents, total_agents, "Investment Agent Complete ✓")
        
    # ============================================================================
    # STEP 4: Loan Agent
    # ============================================================================
    print("\n")
    completed_agents += 1
    print_progress_bar(completed_agents, total_agents, "Loan Agent Running...")
    
    loan_output, loan_time = _run_specialist_agent(
        agents["loan"], "Loan & Credit", client_id, combined_context,
        task_description="Credit capacity assessment, AECB analysis, and loan product recommendations",
        emoji="💳"
    )
    agent_outputs["loan"] = loan_output
    execution_metrics["agent_timings"]["loan"] = loan_time
    
    # Save individual JSON
    with open(client_output_dir / "4_loan_agent.json", "w") as jf:
        jf.write(loan_output.model_dump_json(indent=2))
    print(f"💾 Saved: 4_loan_agent.json")
    print_progress_bar(completed_agents, total_agents, "Loan Agent Complete ✓")
        
    # ============================================================================
    # STEP 5: Banking/CASA Agent
    # ============================================================================
    print("\n")
    completed_agents += 1
    print_progress_bar(completed_agents, total_agents, "Banking Agent Running...")
    
    banking_output, banking_time = _run_specialist_agent(
        agents["banking"], "Banking & CASA", client_id, combined_context,
        task_description="CASA analysis, deposit trends, and banking product recommendations",
        emoji="🏦"
    )
    agent_outputs["banking"] = banking_output
    execution_metrics["agent_timings"]["banking"] = banking_time
    
    # Save individual JSON
    with open(client_output_dir / "5_banking_casa_agent.json", "w") as jf:
        jf.write(banking_output.model_dump_json(indent=2))
    print(f"💾 Saved: 5_banking_casa_agent.json")
    print_progress_bar(completed_agents, total_agents, "Banking Agent Complete ✓")
        
    # ============================================================================
    # STEP 5B: Bancassurance Agent
    # ============================================================================
    print("\n")
    completed_agents += 1
    print_progress_bar(completed_agents, total_agents, "Bancassurance Agent Running...")
    
    bancassurance_output, bancassurance_time = _run_specialist_agent(
        agents["bancassurance"], "Bancassurance", client_id, combined_context,
        task_description="Insurance gap analysis, lifecycle triggers, and protection product recommendations",
        emoji="🛡️"
    )
    agent_outputs["bancassurance"] = bancassurance_output
    execution_metrics["agent_timings"]["bancassurance"] = bancassurance_time
    
    # Save individual JSON
    with open(client_output_dir / "6_bancassurance_agent.json", "w") as jf:
        jf.write(bancassurance_output.model_dump_json(indent=2))
    print(f"💾 Saved: 6_bancassurance_agent.json")
    print_progress_bar(completed_agents, total_agents, "Bancassurance Agent Complete ✓")
        
    # ============================================================================
    # STEP 6: RM Strategy Agent (Final Synthesis)
    # ============================================================================
    print("\n")
    completed_agents += 1
    print_progress_bar(completed_agents, total_agents, "RM Strategy Agent Running...")
    
    rm_strategy_output, rm_strategy_time = _run_rm_strategy_agent(agents["rm_strategy"], client_id, agent_outputs)
    agent_outputs["rm_strategy"] = rm_strategy_output
    execution_metrics["agent_timings"]["rm_strategy"] = rm_strategy_time
    
    # Save individual JSON
    with open(client_output_dir / "7_rm_strategy_agent.json", "w") as jf:
        jf.write(rm_strategy_output.model_dump_json(indent=2))
    print(f"💾 Saved: 7_rm_strategy_agent.json")
    print_progress_bar(completed_agents, total_agents, "All Agents Complete! ✓")
    print("\n")
    
    # Calculate total execution time
    overall_execution_time = time.time() - overall_start_time
    execution_metrics["total_time"] = overall_execution_time
    execution_metrics["end_time"] = datetime.now().isoformat()
    
    # Step 5: Create beautifully formatted readable output file
    print("\n" + "="*100)
    print("📝 GENERATING OUTPUT FILES".center(100))
    print("="*100)
    print("🔄 Creating readable analysis report...")
    from utils_readable import create_readable_report
    create_readable_report(
        client_id=client_id,
        agent_outputs=agent_outputs,
        execution_metrics=execution_metrics,
        output_path=readable_output_path
    )
    
    # Step 6: Export combined structured JSON (with execution metrics)
    print("🔄 Exporting combined JSON file...")
    outputs_for_export = {k: v for k, v in agent_outputs.items()}
    export_structured_json(outputs_for_export, combined_json_path)
    
    # Add execution metrics to the JSON file manually
    with open(combined_json_path, "r") as f:
        combined_data = json.load(f)
    combined_data["_execution_metrics"] = execution_metrics
    with open(combined_json_path, "w") as f:
        json.dump(combined_data, f, indent=2, default=str)
    print("✅ All output files generated successfully!\n")
    
    # Step 7: Print completion summary with timing
    print("="*100)
    print("⏱️  EXECUTION PERFORMANCE SUMMARY".center(100))
    print("="*100)
    total_time = execution_metrics['total_time']
    print(f"\n🎯 Total Execution Time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)\n")
    print("Agent Performance Breakdown:")
    print("-" * 100)
    print(f"  {'Agent':<30} {'Time (seconds)':<20} {'Time (minutes)':<20} {'% of Total':<15}")
    print("-" * 100)
    
    agents_data = [
        ("1. Manager Agent", execution_metrics['agent_timings']['manager']),
        ("2. Risk & Compliance", execution_metrics['agent_timings']['risk']),
        ("3. Investment Agent", execution_metrics['agent_timings']['investment']),
        ("4. Loan Agent", execution_metrics['agent_timings']['loan']),
        ("5. Banking Agent", execution_metrics['agent_timings']['banking']),
        ("6. Bancassurance Agent", execution_metrics['agent_timings']['bancassurance']),
        ("7. RM Strategy Agent", execution_metrics['agent_timings']['rm_strategy']),
    ]
    
    for agent_name, agent_time in agents_data:
        percent = (agent_time / total_time * 100) if total_time > 0 else 0
        print(f"  {agent_name:<30} {agent_time:>18.2f}s {agent_time/60:>18.1f}m {percent:>13.1f}%")
    
    print("-" * 100)
    print(f"  {'TOTAL':<30} {total_time:>18.2f}s {total_time/60:>18.1f}m {'100.0%':>13}")
    print("="*100 + "\n")
    
    print("="*100)
    print("📁 OUTPUT FILES GENERATED".center(100))
    print("="*100)
    print(f"\n📄 Readable Report:")
    print(f"   └─ {readable_output_path}")
    print(f"\n📦 Combined JSON:")
    print(f"   └─ {combined_json_path}")
    print(f"\n📂 Individual Agent JSONs ({client_output_dir}/):")
    print(f"   ├─ 1_manager_agent.json")
    print(f"   ├─ 2_risk_compliance_agent.json")
    print(f"   ├─ 3_investment_agent.json")
    print(f"   ├─ 4_loan_agent.json")
    print(f"   ├─ 5_banking_casa_agent.json")
    print(f"   ├─ 6_bancassurance_agent.json")
    print(f"   └─ 7_rm_strategy_agent.json")
    print("\n" + "="*100)
    print("✅ ANALYSIS COMPLETE! All outputs saved successfully.".center(100))
    print("="*100 + "\n")


# ============================================================================
# Helper Functions for Agent Execution
# ============================================================================

def _resolve_client_id(client_id: str | None) -> str:
    """Resolve and validate client ID."""
    def _exists(cid: str) -> bool:
        rows = db._execute_query(
            "SELECT 1 FROM core.client_context WHERE client_id=:cid LIMIT 1",
            {"cid": cid}
        )
        return bool(rows)
    
    if not client_id:
        rows = db._execute_query(
            "SELECT client_id FROM core.client_context ORDER BY client_id ASC LIMIT 1"
        )
        client_id = rows[0].get("client_id") if rows else None
    
    if not client_id or not _exists(client_id):
        raise RuntimeError("Client not found")
    
    return client_id


def _run_manager_agent(agent: Agent, client_id: str) -> tuple[ManagerAgentOutput, float]:
    """Run Manager Agent and return structured output with execution time."""
    start_time = time.time()
    print(f"\n{'='*80}")
    print(f"🎯 MANAGER AGENT - CLIENT CONTEXT SETTING")
    print(f"{'='*80}")
    print(f"⏱️  Started at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"📋 Task: Comprehensive client profiling, portfolio analysis, and opportunity identification")
    print(f"🔄 Status: Running...")
    
    result = Runner.run_sync(
        starting_agent=agent,
        input=(
            f"Provide a succinct, to-the-point manager context for client {client_id}. "
            f"Keep it concise while remaining fully data-driven."
        ),
        max_turns=25,
    )
    
    execution_time = time.time() - start_time
    print(f"✅ Completed at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"⏱️  Execution Time: {execution_time:.2f} seconds ({execution_time/60:.1f} minutes)")
    print(f"{'='*80}\n")
    
    return result.final_output, execution_time


def _run_risk_agent(agent: Agent, client_id: str, manager_json: str) -> tuple[RiskComplianceAgentOutput, float]:
    """Run Risk & Compliance Agent and return structured output with execution time."""
    start_time = time.time()
    print(f"\n{'='*80}")
    print(f"🛡️  RISK & COMPLIANCE AGENT - RISK ASSESSMENT")
    print(f"{'='*80}")
    print(f"⏱️  Started at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"📋 Task: Risk profile evaluation, compliance guidelines, and regulatory alignment")
    print(f"🔄 Status: Running...")
    
    result = Runner.run_sync(
        starting_agent=agent,
        input=(
            f"Provide a succinct, to-the-point risk & compliance context for client {client_id}. "
            f"Keep it concise while remaining fully data-driven. Use the manager context below.\n\n" 
            + manager_json
        ),
        max_turns=25,
    )
    
    execution_time = time.time() - start_time
    print(f"✅ Completed at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"⏱️  Execution Time: {execution_time:.2f} seconds ({execution_time/60:.1f} minutes)")
    print(f"{'='*80}\n")
    
    return result.final_output, execution_time


def _run_specialist_agent(agent: Agent, agent_name: str, client_id: str, combined_context: str, task_description: str = "", emoji: str = "📊") -> tuple[Any, float]:
    """Run a specialist agent and return structured output with execution time."""
    start_time = time.time()
    print(f"\n{'='*80}")
    print(f"{emoji} {agent_name.upper()} AGENT")
    print(f"{'='*80}")
    print(f"⏱️  Started at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"📋 Task: {task_description}")
    print(f"🔄 Status: Running...")
    
    result = Runner.run_sync(
        starting_agent=agent,
        input=f"Use this combined context for client {client_id}:\n\n{combined_context}",
        max_turns=25,
    )
    
    execution_time = time.time() - start_time
    print(f"✅ Completed at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"⏱️  Execution Time: {execution_time:.2f} seconds ({execution_time/60:.1f} minutes)")
    print(f"{'='*80}\n")
    
    return result.final_output, execution_time


def _run_rm_strategy_agent(agent: Agent, client_id: str, agent_outputs: Dict) -> tuple[RMStrategyAgentOutput, float]:
    """Run RM Strategy Agent with all other agent outputs and return structured output with execution time."""
    start_time = time.time()
    print(f"\n{'='*80}")
    print(f"🎯 RM STRATEGY AGENT - FINAL SYNTHESIS")
    print(f"{'='*80}")
    print(f"⏱️  Started at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"📋 Task: Synthesizing all agent outputs into actionable RM strategy")
    print(f"🔄 Status: Processing outputs from 6 specialist agents...")
    
    # Convert all agent outputs to JSON strings
    agent_outputs_json = {
        name: output.model_dump_json(indent=2)
        for name, output in agent_outputs.items()
    }
    
    # Build RM Strategy input prompt
    rm_strategy_input = build_rm_strategy_input(client_id, agent_outputs_json)
    
    # Run RM Strategy Agent
    result = Runner.run_sync(
        starting_agent=agent,
            input=rm_strategy_input,
        max_turns=25,
    )
    
    execution_time = time.time() - start_time
    print(f"✅ Completed at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"⏱️  Execution Time: {execution_time:.2f} seconds ({execution_time/60:.1f} minutes)")
    print(f"{'='*80}\n")
    
    return result.final_output, execution_time


if __name__ == "__main__":
    # BEST CLIENT FOR COMPREHENSIVE TESTING: 19RAFLH
    # ✅ Share of Potential: 3 opportunities ($3.35M assets, $499K investments, $170K banca)
    # ✅ AECB Alerts: 5 records (car loan, credit card, mortgage)
    # ✅ KYC Data: Expires 2025-06-30 (time-sensitive!)
    # ✅ Profile: R4, Wealth Management, 8.19 years tenure
    # ⚠️ No current holdings (demonstrates opportunity identification)
    # Alternative: 61PRFKK (has fixed income investments but no share of potential)
    main(client_id='19RAFLH')

    # Suggested client IDs with full data (context + holdings/portfolio + transactions + risk/comms):
    # [
    #  '61XQKGA', '61QQQAA', '61PRHKK', '61PRFKK', '60XLXPF', '60RRQGP', '60KLFGH', '60FPPHQ', '60ARHFL', '60AFRAR',
    #  '59XRXKR', '59XRQAR', '59XPQGR', '59XLXRP', '59XHQGP', '59XFQGP', '59RXKGG', '59RQHHA', '59RLQAG', '59RLKFH',
    #  '59RKPKR', '59RKPGP', '59QXLRX', '59QPQKX', '59QKXAR', '59QKRPF', '59QKPFR', '59QKGKP', '59PRQGK', '59PHXGX',
    #  '59KLAKF', '59HKPPR', '59GRQKH', '59GPQKQ', '59GKQLK', '59GHLLX', '59FGPPH', '59FFQQG', '59FAFHR', '58XQGKL',
    #  '58XKGKK', '58XHQAL', '58XFQLG', '58RHKPF', '58PQLGG', '58PPQKQ', '58PGKQK', '58LRQGK', '58LRLLP', '58LRHHG'
    # ]
    # Of these, clients with positive upsell delta and both transactions and AECB alerts: 37
    # [
    #  '10QXPHG', '11XLALK', '12AGRXF', '15FAKLF', '16PFKQA', '16PKLRG', '16PQAPF',
    #  '17QPQRH', '17RLGQG', '19PLGKG', '19RAFLH', '19RQHFR', '20RFRLL', '38LQQHP',
    #  '40GKRFH', '46AAFGX', '46KFLPF', '46QLXGH', '46RFRFK', '47FHFHH', '47PFFAP',
    #  '47PXPPX', '47QRQLQ', '56AFAKQ', '56FHQHL', '56HQFRA', '57KGRHX', '57KQFQQ',
    #  '57QXPHG', '57XLFXG', '58FQPGA', '58LXXKR', '58XAALG', '59XGGFH', '60HKPHA',
    #  '60QHXRF', '60RHLRQ'
    # ]

    # Run by passing a client_id directly to main():
    # Example:
    # main(client_id='61XQKGA')

    #main(client_id='11XLALK')


