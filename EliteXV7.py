#!/usr/bin/env python3
"""
EliteXV7.py - Elite Financial Strategy Framework (V7) with Asset Allocation Agent

Enhanced V6 architecture with new Asset Allocation Agent for portfolio rebalancing recommendations.
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
    ELITE_ASSET_ALLOCATION_AGENT_PROMPT_V5,
    ELITE_MARKET_INTELLIGENCE_AGENT_PROMPT_V5,
    ELITE_RM_STRATEGY_AGENT_PROMPT_V5,
    ELITE_BANCASSURANCE_AGENT_PROMPT_V5,
)

# Import Pydantic Models for Structured Outputs
from models import (
    ManagerAgentOutput,
    RiskComplianceAgentOutput,
    AssetAllocationAgentOutput,
    InvestmentAgentOutput,
    LoanAgentOutput,
    BankingAgentOutput,
    BancassuranceAgentOutput,
    RMStrategyAgentOutput,
    MarketIntelligenceAgentOutput,
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
        # Convert income to float, handle None/empty values
        try:
            income = float(c.get('income') or 0)
        except (ValueError, TypeError):
            income = 0.0
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
            """SELECT id, client_id,
                       last_valuation_date, aum, investible_cash, deposits,
                       asset_distribution
                FROM core.client_portfolio WHERE client_id=:cid
                ORDER BY last_valuation_date DESC LIMIT 500""",
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
                 ORDER BY risk_level DESC LIMIT 700""",
            {"cid": client_id},
        )
        return self._json({"client_id": client_id, "risk_alerts": alerts})

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

        # Maturing products: read from core.productbalance using maturity_date per client
        maturity_rows: List[Dict[str, Any]] = []
        if self._table_exists("core", "productbalance"):
            try:
                pcols = set(self._columns("core", "productbalance"))
                # Identify column names (verified exact names in database)
                customer_col = "customer_number" if "customer_number" in pcols else None
                maturity_col = "maturity_date" if "maturity_date" in pcols else None
                lev1_col = "product_levl1_desc" if "product_levl1_desc" in pcols else None
                lev2_col = "product_levl2_desc" if "product_levl2_desc" in pcols else None
                lev3_col = "product_levl3_desc" if "product_levl3_desc" in pcols else None
                prod_desc_col = "product_description" if "product_description" in pcols else None
                if customer_col and maturity_col:
                    select_parts = []
                    if lev1_col: select_parts.append(f'"{lev1_col}" AS product_level1_desc')
                    if lev2_col: select_parts.append(f'"{lev2_col}" AS product_level2_desc')
                    if lev3_col: select_parts.append(f'"{lev3_col}" AS product_level3_desc')
                    if prod_desc_col: select_parts.append(f'"{prod_desc_col}" AS product_description')
                    select_parts.append(f'"{maturity_col}" AS maturity_date')
                    mq = (
                        "SELECT " + ", ".join(select_parts) +
                        " FROM core.productbalance "
                        f"WHERE LOWER(\"{customer_col}\") = LOWER(:cid) "
                        f"AND \"{maturity_col}\" IS NOT NULL "
                        f"ORDER BY \"{maturity_col}\" ASC NULLS LAST "
                        "LIMIT 200"
                    )
                    maturity_rows = self._execute_query(mq, {"cid": client_id})
            except Exception:
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
        # Select exact column names verified in database
        rows = self._execute_query(
            """SELECT 
                isin,
                issuer_name,
                security_ccy,
                bloomberg_rating,
                annual_coupon_payment,
                interest_interval,
                ytm,
                maturity_date,
                islamic_compliance,
                sub_asset_type_desc,
                geography
            FROM core.bonds 
            ORDER BY issuer_name 
            LIMIT 50"""
        )
        return self._json({"bonds": rows})

    def get_stocks_catalog(self) -> str:
        # Select exact column names verified in database
        rows = self._execute_query(
            """SELECT 
                isin,
                name,
                sector,
                geography,
                last_price,
                target_price,
                volatility,
                market_cap,
                currency,
                islamic_compliance
            FROM core.stocks 
            ORDER BY name 
            LIMIT 50"""
        )
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
        client_income = client_data.get('income') or 0
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
                "income_aed": client_income,
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
        # Query core.productbalance for products maturing in next 6 months
        items: List[Dict[str, Any]] = []

        if self._table_exists("core", "productbalance"):
            # Use exact verified column names
            items = self._execute_query(
                """SELECT 
                    product_levl1_desc AS product_level1_desc,
                    product_levl2_desc AS product_level2_desc,
                    product_levl3_desc AS product_level3_desc,
                    maturity_date
                FROM core.productbalance
                WHERE LOWER(customer_number) = LOWER(:cid)
                  AND maturity_date IS NOT NULL
                  AND maturity_date >= CURRENT_DATE
                  AND maturity_date < CURRENT_DATE + INTERVAL '6 months'
                  AND (product_levl1_desc ILIKE '%LEND%' 
                       OR product_levl1_desc ILIKE '%LOAN%' 
                       OR product_levl1_desc = 'LENDING_PRODUCT')
                ORDER BY maturity_date ASC""",
                {"cid": client_id}
            )

        return self._json({
            "client_id": client_id,
            "window": "next_6_months",
            "maturing_products": items,
            "data_source": "core.productbalance"
        })

    def get_kyc_expiring_within_6m(self, client_id: str) -> str:
        # Query app.client for KYC expiry date (exact column name verified)
        info: Dict[str, Any] | None = None
        expiry_within_6m = False
        
        if self._table_exists("app", "client"):
            r = self._execute_query(
                """SELECT client_id, kyc_expiry_date 
                   FROM app.client 
                   WHERE LOWER(client_id)=LOWER(:cid) 
                   LIMIT 1""",
                {"cid": client_id}
            )
            info = r[0] if r else None
        
        # Check if KYC expiry date is actually within 6 months from today
        if info and info.get("kyc_expiry_date"):
            from datetime import datetime, timedelta
            try:
                kyc_date = info.get("kyc_expiry_date")
                # Handle both datetime and string formats
                if isinstance(kyc_date, str):
                    expiry_date = datetime.strptime(kyc_date, "%Y-%m-%d").date()
                elif hasattr(kyc_date, 'date'):
                    expiry_date = kyc_date.date()
                else:
                    expiry_date = kyc_date
                
                today = datetime.now().date()
                days_until_expiry = (expiry_date - today).days
                
                # Only flag as expiring within 6 months (180 days)
                expiry_within_6m = 0 <= days_until_expiry <= 180
            except (ValueError, AttributeError, TypeError):
                # If date parsing fails, default to False
                expiry_within_6m = False
        
        return self._json({
            "client_id": client_id,
            "kyc": info,
            "expiry_within_6m": expiry_within_6m,
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
        # Credit-related transactions from core.client_transaction (exact column names verified)
        credit_txs: list[dict] = []
        try:
            credit_txs = self._execute_query(
                """SELECT 
                    transaction_id,
                    client_id,
                    transaction_type,
                    transaction_amount,
                    date,
                    currency,
                    booking_geography,
                    name
                FROM core.client_transaction
                WHERE client_id = :cid
                  AND LOWER(transaction_type) IN ('credit', 'loan', 'advance', 'loan payment')
                ORDER BY date DESC NULLS LAST
                LIMIT 200""",
                {"cid": client_id}
            )
        except Exception:
            pass
        
        # Loan payment transactions from debit (may include loan EMI payments)
        loan_payment_txs: list[dict] = []
        try:
            loan_payment_txs = self._execute_query(
                """SELECT transaction_type, mcc_desc, amount, currency,
                          narrative_1, narrative_2, txn_date, product_desc
                   FROM core.clienttransactiondebit 
                   WHERE customer_number=:cid 
                   AND (
                       LOWER(mcc_desc) LIKE '%loan%'
                       OR LOWER(mcc_desc) LIKE '%mortgage%'
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
            # Use exact verified column names from core.productbalance
            existing_loans = self._execute_query(
                """SELECT 
                    customer_number,
                    account_number,
                    product_description,
                    product_levl1_desc,
                    product_levl2_desc,
                    product_levl3_desc,
                    outstanding,
                    maturity_date,
                    banking_type
                FROM core.productbalance
                WHERE customer_number = :cid
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
                LIMIT 50""",
                {"cid": client_id}
            )

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
        })

    def get_elite_client_behavior_analysis(self, client_id: str) -> str:
        """
        Enhanced behavior analysis focusing on spending patterns:
        - Credit card transactions (from core.clienttransactioncredit)
        - Debit card transactions (from core.clienttransactiondebit)
        - Spending patterns by merchant category (mcc_desc)
        - Transaction amount analysis
        """
        # Credit card transactions with merchant categories
        credit_txs = []
        spending_by_category: Dict[str, Dict[str, float]] = {}
        try:
            credit_txs = self._execute_query(
                """SELECT product_desc, direction, destination_amount as amount, 
                          destination_currency as currency, merchant_name, 
                          mcc_desc, txn_date, merchant_city, merchant_country_code
                   FROM core.clienttransactioncredit 
                   WHERE customer_number=:cid 
                   ORDER BY txn_date DESC NULLS LAST 
                   LIMIT 500""",
                {"cid": client_id}
            )
            # Aggregate spending by merchant category for credit
            for tx in credit_txs:
                category = tx.get("mcc_desc") or "Uncategorized"
                amount = abs(float(tx.get("amount") or 0))
                if category not in spending_by_category:
                    spending_by_category[category] = {"total": 0, "count": 0, "avg": 0}
                spending_by_category[category]["total"] += amount
                spending_by_category[category]["count"] += 1
        except Exception:
            pass
        
        # Debit card transactions with merchant categories
        debit_txs = []
        try:
            debit_txs = self._execute_query(
                """SELECT mcc_desc, amount, currency, product_desc,
                          narrative_1, narrative_2, txn_date
                   FROM core.clienttransactiondebit 
                   WHERE customer_number=:cid 
                   ORDER BY txn_date DESC NULLS LAST 
                   LIMIT 500""",
                {"cid": client_id}
            )
            # Aggregate spending by merchant category for debit
            for tx in debit_txs:
                category = tx.get("mcc_desc") or "Uncategorized"
                amount = abs(float(tx.get("amount") or 0))
                if category not in spending_by_category:
                    spending_by_category[category] = {"total": 0, "count": 0, "avg": 0}
                spending_by_category[category]["total"] += amount
                spending_by_category[category]["count"] += 1
        except Exception:
            pass
        
        # Calculate averages for each category
        for category in spending_by_category:
            total = spending_by_category[category]["total"]
            count = spending_by_category[category]["count"]
            spending_by_category[category]["avg"] = total / count if count > 0 else 0
        
        # Calculate totals
        total_credit = len(credit_txs)
        total_debit = len(debit_txs)
        total_all = total_credit + total_debit
        
        total_credit_amount = sum(abs(float(tx.get("amount") or 0)) for tx in credit_txs)
        total_debit_amount = sum(abs(float(tx.get("amount") or 0)) for tx in debit_txs)
        total_spend = total_credit_amount + total_debit_amount
        
        # Top spending categories
        top_spending = sorted(
            [{"category": k, "total_spent": round(v["total"], 2), 
              "transaction_count": v["count"], "avg_transaction": round(v["avg"], 2)} 
             for k, v in spending_by_category.items()],
            key=lambda x: -x["total_spent"]
        )[:20]
        
        # Merchant category breakdown (mcc_desc as transaction types)
        category_types: Dict[str, int] = {}
        for tx in credit_txs:
            cat = tx.get("mcc_desc") or "Uncategorized"
            category_types[cat] = category_types.get(cat, 0) + 1
        for tx in debit_txs:
            cat = tx.get("mcc_desc") or "Uncategorized"
            category_types[cat] = category_types.get(cat, 0) + 1
        
        return self._json({
            "client_id": client_id,
            "transaction_summary": {
                "total_transactions": total_all,
                "credit_card_count": total_credit,
                "debit_card_count": total_debit,
                "total_spend_amount": round(total_spend, 2),
                "credit_spend_amount": round(total_credit_amount, 2),
                "debit_spend_amount": round(total_debit_amount, 2),
            },
            "top_20_spending_by_category": top_spending,
            "merchant_category_distribution": sorted(category_types.items(), key=lambda x: -x[1])[:20],
            "sample_credit_transactions": credit_txs[:10],
            "sample_debit_transactions": debit_txs[:10],
        })

   

    def get_elite_share_of_potential(self, client_id: str) -> str:
        """
        Retrieve upsell opportunities from app.upsellopportunity table.
        
        For each product category (from 'category' column):
        - Reports the upsell opportunity amount (from 'delta' column)
        - Provides recommendations for downstream agent usage (from 'insights' column)
        - Shows current vs potential value to demonstrate growth opportunity
        
        Returns JSON with all opportunities sorted by upsell amount (highest first).
        """
        # Check if table exists
        if not self._table_exists("app", "upsellopportunity"):
            return self._json({"client_id": client_id, "source": None, "opportunities": []})
        
        # Fetch all opportunities for the client
        try:
            rows = self._execute_query(
                """SELECT client_id, category, current_value, potential_value, delta, 
                          status, insights, creation_date, update_date
                   FROM app.upsellopportunity 
                   WHERE LOWER(client_id) = LOWER(:cid) 
                   ORDER BY delta DESC NULLS LAST""",
                {"cid": client_id},
            )
        except Exception:
            return self._json({"client_id": client_id, "source": "app.upsellopportunity", "opportunities": []})
        
        # Format opportunities
        opps = []
        total_upsell_amount = 0
        for r in rows:
            upsell_amount = float(r.get("delta") or 0)
            total_upsell_amount += upsell_amount
            
            opps.append({
                "product_category": r.get("category"),
                "upsell_opportunity_amount": upsell_amount,
                "current_value": float(r.get("current_value") or 0),
                "potential_value": float(r.get("potential_value") or 0),
                "status": r.get("status"),
                "recommendations_for_agent": r.get("insights") or [],
                "creation_date": str(r.get("creation_date")) if r.get("creation_date") else None,
                "update_date": str(r.get("update_date")) if r.get("update_date") else None,
            })
        
        return self._json({
            "client_id": client_id, 
            "source": "app.upsellopportunity", 
            "total_opportunities": len(opps),
            "total_upsell_opportunity_amount": round(total_upsell_amount, 2),
            "opportunities": opps
        })

    def get_elite_engagement_analysis(self, client_id: str) -> str:
        """
        Combined engagement and communication analysis from multiple sources:
        1. core.engagement_analysis - dedicated engagement metrics (if available)
        2. core.communication_log - structured communication records
        3. core.callreport - detailed call/meeting reports with transcripts
        
        Returns comprehensive engagement data with:
        - All communications sorted by date
        - Aggregated statistics by type, subtype, status, channel
        - Source tracking for each communication
        """
        all_communications = []
        params = {"cid": client_id}
        engagement_metrics = []
        
        # Source 1: engagement_analysis (pre-aggregated metrics if available)
        if self._table_exists("core", "engagement_analysis"):
            ecols = set(self._columns("core", "engagement_analysis"))
            id_where = []
            for col in ("client_id", "customer_id", "cif", "cif2"):
                if col in ecols:
                    id_where.append(f"LOWER({col})=LOWER(:cid)")
            order_col = "last_update" if "last_update" in ecols else next(iter(ecols), None)
            if id_where and order_col:
                sql = f"SELECT * FROM core.engagement_analysis WHERE (" + " OR ".join(id_where) + f") ORDER BY {order_col} DESC NULLS LAST LIMIT 200"
                try:
                    engagement_metrics = self._execute_query(sql, params)
                except Exception:
                    pass
        
        # Source 2: communication_log (structured communication records)
        if self._table_exists("core", "communication_log"):
            ccols = set(self._columns("core", "communication_log"))
            select_parts = ["'communication_log' as source"]
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
                    f"SELECT {', '.join(select_parts)} "
                    f"FROM core.communication_log WHERE ({' OR '.join(where_parts)}) "
                    + (f"ORDER BY {order_col} DESC NULLS LAST " if order_col else "")
                    + "LIMIT 200"
                )
                try:
                    comm_log_rows = self._execute_query(sql, params)
                    all_communications.extend(comm_log_rows)
                except Exception:
                    pass
        
        # Source 3: callreport (detailed call/meeting reports with transcripts)
        if self._table_exists("core", "callreport"):
            call_cols = set(self._columns("core", "callreport"))
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
            
            call_select.append("'completed' as status")
            
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
            
            # Add transcript preview if available
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
                    "LIMIT 200"
                )
                try:
                    call_rows = self._execute_query(sql, params)
                    all_communications.extend(call_rows)
                except Exception:
                    pass
        
        # Sort all communications by date (most recent first)
        all_communications.sort(
            key=lambda x: x.get('communication_date') or '', 
            reverse=True
        )
        
        # Aggregate statistics
        by_type: Dict[str, int] = {}
        by_subtype: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        by_channel: Dict[str, int] = {}
        by_source: Dict[str, int] = {}
        
        for comm in all_communications:
            # Type aggregation
            t = (comm.get("type") or "unknown").lower()
            by_type[t] = by_type.get(t, 0) + 1
            
            # Subtype aggregation
            st = (comm.get("subtype") or "unknown").lower()
            by_subtype[st] = by_subtype.get(st, 0) + 1
            
            # Status aggregation
            status = (comm.get("status") or "unknown").lower()
            by_status[status] = by_status.get(status, 0) + 1
            
            # Channel aggregation
            channel = (comm.get("channel") or "unknown").lower()
            by_channel[channel] = by_channel.get(channel, 0) + 1
            
            # Source aggregation
            source = comm.get("source") or "unknown"
            by_source[source] = by_source.get(source, 0) + 1
        
        return self._json({
            "client_id": client_id,
            "total_communications": len(all_communications),
            "sources": by_source,
            "engagement_summary": {
                "by_type": sorted(by_type.items(), key=lambda x: -x[1]),
                "by_subtype": sorted(by_subtype.items(), key=lambda x: -x[1]),
                "by_status": sorted(by_status.items(), key=lambda x: -x[1]),
                "by_channel": sorted(by_channel.items(), key=lambda x: -x[1]),
                "by_source": by_source,
            },
            "engagement_metrics": engagement_metrics,
            "recent_communications": all_communications[:50],  # Most recent 50
            "communications": all_communications[:200],  # Up to 200 total
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
        # Get unique mapped policy types (from policy_category)
        policy_types_mapped = list(set(h.get("policy_category") for h in holdings if h.get("policy_category")))
        
        return self._json({
            "client_id": client_id,
            "summary": {
                "total_policies": policy_count,
                "total_value_aed": total_value,
                "policy_types_held": policy_types_held,
                "policy_types_mapped": policy_types_mapped,
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
                "priority_gaps": priority_gaps[:50],  # Top 50 priority
                "other_opportunities": other_gaps[:50],  # Top 50 other
            },
            "current_holdings_count": len(held_policy_types),
            "ml_recommended_categories": recommended_categories,
            "recommendation": "HIGH OPPORTUNITY - No existing coverage" if not held_policy_types else "Cross-sell opportunities identified",
            "data_sources": ["core.bancaclientproduct", "core.bancapolicymapping", "core.prompt_ml_banca_full_potential"]
        })

    # ============================================================================
    # MARKET INTELLIGENCE TOOLS
    # ============================================================================
    
    def get_elite_market_data(self) -> str:
        """
        Get market data from Excel file including indices, stocks, and market trends.
        Returns comprehensive market data for analysis.
        """
        import pandas as pd
        
        try:
            # Read market data from Excel
            df = pd.read_excel("data/market_data.xlsx")
            
            # Convert to records and handle NaN values
            market_data = df.to_dict('records')
            for record in market_data:
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
                    elif hasattr(value, 'strftime'):
                        record[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            
            # Calculate summary statistics
            total_stocks = len(market_data)
            sectors = list(set(record.get('sector', 'Unknown') for record in market_data if record.get('sector')))
            
            # Top performers by price change
            top_performers = sorted(
                [r for r in market_data if r.get('price_change_percent') is not None],
                key=lambda x: float(x.get('price_change_percent', 0)),
                reverse=True
            )[:10]
            
            # Market cap analysis
            market_caps = [float(r.get('market_cap', 0)) for r in market_data if r.get('market_cap') is not None]
            avg_market_cap = sum(market_caps) / len(market_caps) if market_caps else 0
            
            return self._json({
                "total_stocks": total_stocks,
                "sectors_covered": len(sectors),
                "sectors": sectors,
                "top_performers": top_performers,
                "market_cap_analysis": {
                    "average_market_cap": avg_market_cap,
                    "total_companies": len(market_caps)
                },
                "market_data": market_data[:100],  # Limit to first 100 for performance
                "data_source": "data/market_data.xlsx"
            })
            
        except Exception as e:
            logging.warning(f"Could not load market data: {e}")
            return self._json({
                "error": str(e),
                "market_data": [],
                "total_stocks": 0,
                "data_source": "data/market_data.xlsx"
            })
    
    def get_elite_economic_indicators(self) -> str:
        """
        Get economic indicators from Excel file including GDP, inflation, unemployment, etc.
        Returns key economic indicators for market analysis.
        """
        import pandas as pd
        
        try:
            # Read economic indicators from Excel
            df = pd.read_excel("data/economic_indicators.xlsx")
            
            # Convert to records and handle NaN values
            indicators = df.to_dict('records')
            for record in indicators:
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
                    elif hasattr(value, 'strftime'):
                        record[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            
            # Categorize by unique values of the 'Indicator' column from the Excel
            unique_indicators = sorted({str(r.get('Indicator') or '').strip() for r in indicators if r.get('Indicator')})
            categorized = {}
            for name in unique_indicators:
                categorized[name] = [r for r in indicators if str(r.get('Indicator') or '').strip() == name]
            
            return self._json({
                "total_indicators": len(indicators),
                "indicator_categories": unique_indicators,
                "categorized_indicators": categorized,
                "all_indicators": indicators,
                "data_source": "data/economic_indicators.xlsx"
            })
            
        except Exception as e:
            logging.warning(f"Could not load economic indicators: {e}")
            return self._json({
                "error": str(e),
                "indicators": [],
                "total_indicators": 0,
                "data_source": "data/economic_indicators.xlsx"
            })
    
    def get_elite_risk_scenarios(self) -> str:
        """
        Get risk scenarios from Excel file including probability, impact, and mitigation strategies.
        Returns market risk scenarios for analysis.
        """
        import pandas as pd
        
        try:
            # Read risk scenarios from Excel
            df = pd.read_excel("data/risk_scenarios.xlsx")
            
            # Convert to records and handle NaN values
            scenarios = df.to_dict('records')
            for record in scenarios:
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
                    elif hasattr(value, 'strftime'):
                        record[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            
            # Categorize by risk level
            high_probability = [r for r in scenarios if r.get('probability', 0) and float(r.get('probability', 0)) > 0.7]
            high_impact = [r for r in scenarios if r.get('impact', 0) and float(r.get('impact', 0)) > 0.7]
            critical_risks = [r for r in scenarios if r.get('probability', 0) and r.get('impact', 0) and 
                            float(r.get('probability', 0)) > 0.6 and float(r.get('impact', 0)) > 0.6]
            
            return self._json({
                "total_scenarios": len(scenarios),
                "high_probability_risks": high_probability,
                "high_impact_risks": high_impact,
                "critical_risks": critical_risks,
                "all_scenarios": scenarios,
                "data_source": "data/risk_scenarios.xlsx"
            })
            
        except Exception as e:
            logging.warning(f"Could not load risk scenarios: {e}")
            return self._json({
                "error": str(e),
                "scenarios": [],
                "total_scenarios": 0,
                "data_source": "data/risk_scenarios.xlsx"
            })

    # ============================================================================
    # ASSET ALLOCATION TOOLS
    # ============================================================================
    
    def get_elite_asset_allocation_data(self, client_id: str) -> str:
        """
        Get comprehensive asset allocation data for the client including:
        - Current portfolio allocation by asset class
        - Target allocation based on risk profile and house view
        - Allocation deviation analysis
        - Rebalancing recommendations
        """
        # Get current portfolio allocation from client_investment
        current_allocation = {}
        total_aum = 0.0
        
        positions = self._execute_query(
            """
            SELECT 
                asset_class,
                SUM(market_value_aed) as total_value_aed
            FROM core.client_investment 
            WHERE client_id=:cid
            GROUP BY asset_class
            ORDER BY total_value_aed DESC
            """,
            {"cid": client_id}
        )
        
        for pos in positions:
            asset_class = pos.get("asset_class") or "Unknown"
            value = float(pos.get("total_value_aed") or 0)
            current_allocation[asset_class] = value
            total_aum += value
        
        # Calculate percentages
        current_allocation_pct = {}
        for asset_class, value in current_allocation.items():
            if total_aum > 0:
                current_allocation_pct[asset_class] = (value / total_aum) * 100
            else:
                current_allocation_pct[asset_class] = 0
        
        # Get client risk profile for target allocation
        client_data = self._execute_query(
            """
            SELECT risk_appetite, risk_level, customer_profile_banking_segment, age
            FROM core.client_context 
            WHERE client_id=:cid
            LIMIT 1
            """,
            {"cid": client_id}
        )
        
        # Resolve risk profile from client; fallback to policy default if missing
        risk_profile = None
        age: float | None = None
        if client_data:
            risk_profile = (client_data[0].get("risk_appetite") or "").strip() or None
            # Prefer explicit age; otherwise derive from dob
            age_val = client_data[0].get("age")
            if age_val is not None and str(age_val) != "":
                try:
                    age = float(age_val)
                except Exception:
                    age = None
            else:
                dob = client_data[0].get("dob")
                if dob:
                    try:
                        from datetime import date, datetime
                        if isinstance(dob, str):
                            # Try common formats
                            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
                                try:
                                    dob_dt = datetime.strptime(dob[:10], fmt).date()
                                    break
                                except Exception:
                                    dob_dt = None
                            if dob_dt is None:
                                dob_dt = datetime.fromisoformat(dob[:10]).date()
                        elif isinstance(dob, datetime):
                            dob_dt = dob.date()
                        else:
                            dob_dt = dob  # assume date
                        today = date.today()
                        age = (today.year - dob_dt.year) - ((today.month, today.day) < (dob_dt.month, dob_dt.day))
                        age = float(age)
                    except Exception:
                        age = None
        
        # Policy default for risk profile if still missing; use mid-risk if definition table absent
        if not risk_profile:
            try:
                defs = self._execute_query(
                    "SELECT name FROM core.risk_level_definition ORDER BY level ASC"
                ) or []
                # pick middle of ordered levels if available, else fallback to R3
                if defs:
                    mid = len(defs) // 2
                    risk_profile = defs[mid].get("name") or "R3"
                else:
                    risk_profile = "R3"
            except Exception:
                risk_profile = "R3"
        
        # If age missing, avoid skew: use None-safe handling by defaulting to 0 adjustment path
        if age is None:
            # Use a neutral age that causes minimal adjustment; choose 45
            age = 45.0
        
        # Get target allocation based on risk profile and age
        target_allocation = self._get_target_allocation(risk_profile, int(age))
        
        # Calculate allocation deviations
        allocation_deviations = {}
        for asset_class in set(list(current_allocation_pct.keys()) + list(target_allocation.keys())):
            current_pct = current_allocation_pct.get(asset_class, 0)
            target_pct = target_allocation.get(asset_class, 0)
            deviation = current_pct - target_pct
            allocation_deviations[asset_class] = {
                "current": current_pct,
                "target": target_pct,
                "deviation": deviation,
                "deviation_abs": abs(deviation)
            }
        
        # Removed house view lookup; target allocation already sourced from DB when available.
        
        # Calculate rebalancing recommendations
        rebalancing_recommendations = []
        for asset_class, data in allocation_deviations.items():
            if abs(data["deviation"]) > 5:  # Only recommend if deviation > 5%
                action_type = "SELL" if data["deviation"] > 0 else "BUY"
                amount_aed = (abs(data["deviation"]) / 100) * total_aum
                
                rebalancing_recommendations.append({
                    "asset_class": asset_class,
                    "action": action_type,
                    "current_allocation": data["current"],
                    "target_allocation": data["target"],
                    "deviation": data["deviation"],
                    "amount_aed": amount_aed,
                    "priority": "HIGH" if abs(data["deviation"]) > 10 else "MEDIUM"
                })
        
        # Sort by priority and deviation
        rebalancing_recommendations.sort(key=lambda x: (x["priority"] == "HIGH", abs(x["deviation"])), reverse=True)
        
        return self._json({
            "client_id": client_id,
            "total_aum_aed": total_aum,
            "current_allocation": current_allocation,
            "current_allocation_percentages": current_allocation_pct,
            "target_allocation": target_allocation,
            "allocation_deviations": allocation_deviations,
            "rebalancing_recommendations": rebalancing_recommendations,
            "risk_profile": risk_profile,
            "client_age": age,
            "data_sources": ["core.client_investment", "core.client_context", "core.asset_allocation"]
        })
    
    def _get_target_allocation(self, risk_profile: str, age: int) -> Dict[str, float]:
        """
        Get target asset allocation based on risk profile and age.
        Tries to read Strategic Asset Allocation (SAA) from core.asset_allocation
        using segment mapping from core.risk_level_definition. Falls back to
        internal defaults if not available. Then applies age-based adjustments.
        """
        # Attempt DB-driven allocation using segment mapping
        allocation: Dict[str, float] = {}
        allocation_source = "db"
        try:
            seg_rows = self._execute_query(
                """
                SELECT segment
                FROM core.risk_level_definition
                WHERE name=:rp
                ORDER BY last_updated DESC NULLS LAST
                LIMIT 1
                """,
                {"rp": risk_profile},
            )
            segment = seg_rows[0].get("segment") if seg_rows else None
            if segment:
                rows = self._execute_query(
                    """
                    SELECT category, saa
                    FROM core.asset_allocation
                    WHERE segment_name=:seg
                      AND report_date = (
                        SELECT MAX(report_date)
                        FROM core.asset_allocation
                        WHERE segment_name=:seg
                      )
                    """,
                    {"seg": segment},
                )
                # Map DB categories to UI-friendly keys
                category_map = {
                    "equity": "Equity",
                    "fixed_income": "Fixed Income",
                    "cash_money_markets": "Money Market",
                    "alternatives": "Alternatives",
                }
                for r in rows or []:
                    raw_cat = (r.get("category") or "").strip().lower()
                    key = category_map.get(raw_cat) or raw_cat.replace("_", " ").title()
                    try:
                        allocation[key] = float(r.get("saa") or 0)
                    except Exception:
                        allocation[key] = 0.0
                # Normalize if needed
                total = sum(allocation.values())
                if total and abs(total - 100.0) > 0.5:
                    allocation = {k: (v / total) * 100.0 for k, v in allocation.items()}
        except Exception:
            allocation = {}
            allocation_source = "db"

        # Fallback to internal defaults if DB not available/empty
        if not allocation:
            base_allocations = {
                "R1": {"Equity": 20, "Fixed Income": 60, "Money Market": 15, "Alternatives": 5},
                "R2": {"Equity": 30, "Fixed Income": 50, "Money Market": 15, "Alternatives": 5},
                "R3": {"Equity": 40, "Fixed Income": 40, "Money Market": 15, "Alternatives": 5},
                "R4": {"Equity": 60, "Fixed Income": 25, "Money Market": 10, "Alternatives": 5},
                "R5": {"Equity": 80, "Fixed Income": 10, "Money Market": 5, "Alternatives": 5},
            }
            allocation = base_allocations.get(risk_profile, base_allocations["R3"]).copy()
            allocation_source = "fallback"
        
        # Apply age-based adjustments ONLY when using fallback model
        if allocation_source == "fallback":
            if age >= 60:
                # Reduce equity by 1% per year over 60
                equity_reduction = min((age - 60) * 1, 20)  # Max 20% reduction
                allocation["Equity"] = max(allocation["Equity"] - equity_reduction, 20)
                allocation["Fixed Income"] += equity_reduction
            elif age <= 30:
                # Increase equity by 0.5% per year under 30
                equity_increase = min((30 - age) * 0.5, 10)  # Max 10% increase
                allocation["Equity"] = min(allocation["Equity"] + equity_increase, 90)
                allocation["Fixed Income"] = max(allocation["Fixed Income"] - equity_increase, 10)
        
        return allocation
    
    def get_elite_portfolio_risk_metrics(self, client_id: str) -> str:
        """
        Get comprehensive portfolio risk metrics including:
        - Concentration risk analysis
        - Diversification score
        - Volatility estimates
        - Risk-adjusted performance metrics
        """
        # Get detailed holdings for risk analysis
        holdings = self._execute_query(
            """
            SELECT 
                security_name,
                asset_class,
                market_value_aed,
                cost_value_aed,
                overall_portfolio_xirr_since_inception
            FROM core.client_investment 
            WHERE client_id=:cid
            ORDER BY market_value_aed DESC
            """,
            {"cid": client_id}
        )
        
        if not holdings:
            return self._json({
                "client_id": client_id,
                "error": "No holdings found",
                "risk_metrics": {}
            })
        
        total_aum = sum(float(h.get("market_value_aed") or 0) for h in holdings)
        
        # Calculate concentration metrics
        concentration_metrics = {}
        for holding in holdings:
            security_name = holding.get("security_name") or "Unknown"
            value = float(holding.get("market_value_aed") or 0)
            pct = (value / total_aum * 100) if total_aum > 0 else 0
            concentration_metrics[security_name] = pct
        
        # Top 10 holdings concentration
        top_holdings = sorted(concentration_metrics.items(), key=lambda x: x[1], reverse=True)[:10]
        top_10_concentration = sum(pct for _, pct in top_holdings)
        
        # Asset class concentration
        asset_class_concentration = {}
        for holding in holdings:
            asset_class = holding.get("asset_class") or "Unknown"
            value = float(holding.get("market_value_aed") or 0)
            if asset_class not in asset_class_concentration:
                asset_class_concentration[asset_class] = 0
            asset_class_concentration[asset_class] += value
        
        # Calculate diversification score (0-100, higher is better)
        diversification_score = 100
        if len(holdings) > 0:
            # Reduce score for high concentration
            if top_10_concentration > 80:
                diversification_score -= 30
            elif top_10_concentration > 60:
                diversification_score -= 20
            elif top_10_concentration > 40:
                diversification_score -= 10
            
            # Reduce score for single asset class dominance
            max_asset_class_pct = max((v / total_aum * 100) for v in asset_class_concentration.values()) if total_aum > 0 else 0
            if max_asset_class_pct > 80:
                diversification_score -= 25
            elif max_asset_class_pct > 60:
                diversification_score -= 15
            elif max_asset_class_pct > 40:
                diversification_score -= 5
            
            # Bonus for number of holdings
            if len(holdings) >= 20:
                diversification_score += 5
            elif len(holdings) >= 10:
                diversification_score += 2
        
        diversification_score = max(0, min(100, diversification_score))
        
        # Calculate concentration risk score (0-100, higher is worse)
        concentration_risk_score = 0
        if len(holdings) > 0:
            # High concentration in top holdings
            if top_10_concentration > 80:
                concentration_risk_score += 40
            elif top_10_concentration > 60:
                concentration_risk_score += 25
            elif top_10_concentration > 40:
                concentration_risk_score += 15
            
            # Single security concentration
            max_single_holding = max(concentration_metrics.values()) if concentration_metrics else 0
            if max_single_holding > 20:
                concentration_risk_score += 30
            elif max_single_holding > 10:
                concentration_risk_score += 20
            elif max_single_holding > 5:
                concentration_risk_score += 10
            
            # Asset class concentration
            if max_asset_class_pct > 80:
                concentration_risk_score += 20
            elif max_asset_class_pct > 60:
                concentration_risk_score += 15
            elif max_asset_class_pct > 40:
                concentration_risk_score += 10
        
        concentration_risk_score = min(100, concentration_risk_score)
        
        # Estimate volatility (simplified calculation)
        volatility_estimate = 12.0  # Default 12% annual volatility
        if len(holdings) > 0:
            # Adjust based on asset class mix
            equity_pct = (asset_class_concentration.get("Equity", 0) / total_aum * 100) if total_aum > 0 else 0
            fixed_income_pct = (asset_class_concentration.get("Fixed Income", 0) / total_aum * 100) if total_aum > 0 else 0
            
            # Rough volatility estimate based on allocation
            volatility_estimate = (equity_pct * 0.15 + fixed_income_pct * 0.05 + 
                                 (100 - equity_pct - fixed_income_pct) * 0.08)
            
            # Adjust for concentration
            if concentration_risk_score > 70:
                volatility_estimate *= 1.2
            elif concentration_risk_score > 50:
                volatility_estimate *= 1.1
        
        # Risk mitigation recommendations
        risk_mitigation = []
        if concentration_risk_score > 70:
            risk_mitigation.append("HIGH PRIORITY: Reduce concentration in top holdings")
        if max_single_holding > 10:
            risk_mitigation.append(f"Reduce position in {max(concentration_metrics.items(), key=lambda x: x[1])[0]} (currently {max_single_holding:.1f}%)")
        if max_asset_class_pct > 60:
            dominant_asset = max(asset_class_concentration.items(), key=lambda x: x[1])[0]
            risk_mitigation.append(f"Diversify away from {dominant_asset} (currently {max_asset_class_pct:.1f}%)")
        if len(holdings) < 10:
            risk_mitigation.append("Consider adding more holdings for better diversification")
        
        return self._json({
            "client_id": client_id,
            "total_aum_aed": total_aum,
            "total_holdings": len(holdings),
            "concentration_metrics": {
                "top_10_concentration": top_10_concentration,
                "max_single_holding": max(concentration_metrics.values()) if concentration_metrics else 0,
                "max_asset_class_concentration": max_asset_class_pct,
                "top_holdings": top_holdings[:5]  # Top 5 for brevity
            },
            "risk_scores": {
                "concentration_risk_score": concentration_risk_score,
                "diversification_score": diversification_score,
                "volatility_estimate": volatility_estimate
            },
            "risk_mitigation_recommendations": risk_mitigation,
            "data_sources": ["core.client_investment"]
        })

    def get_elite_communication_history(self, client_id: str) -> str:
        """
        Deprecated: consolidated into get_elite_engagement_analysis.
        Kept for backward compatibility and returns the combined engagement payload.
        """
        return self.get_elite_engagement_analysis(client_id)


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
def get_maturing_products_6m(client_id: str) -> str:
    return db.get_maturing_products_6m(client_id)

@function_tool
def get_kyc_expiring_within_6m(client_id: str) -> str:
    return db.get_kyc_expiring_within_6m(client_id)

@function_tool
def get_elite_market_data() -> str:
    """Get comprehensive market data including indices, stocks, and market trends."""
    return db.get_elite_market_data()

@function_tool
def get_elite_economic_indicators() -> str:
    """Get key economic indicators including GDP, inflation, unemployment, interest rates."""
    return db.get_elite_economic_indicators()

@function_tool
def get_elite_risk_scenarios() -> str:
    """Get market risk scenarios with probability, impact, and mitigation strategies."""
    return db.get_elite_risk_scenarios()

@function_tool
def get_elite_asset_allocation_data(client_id: str) -> str:
    """Get comprehensive asset allocation data including current vs target allocation and rebalancing recommendations."""
    return db.get_elite_asset_allocation_data(client_id)

@function_tool
def get_elite_portfolio_risk_metrics(client_id: str) -> str:
    """Get portfolio risk metrics including concentration risk, diversification score, and volatility estimates."""
    return db.get_elite_portfolio_risk_metrics(client_id)


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

    # Asset Allocation Agent - NEW: Portfolio rebalancing recommendations
    asset_allocation = Agent(
        name="Elite_Asset_Allocation_Expert_V6",
        instructions=ELITE_ASSET_ALLOCATION_AGENT_PROMPT_V5,
        tools=[
            get_elite_asset_allocation_data,
            get_elite_portfolio_risk_metrics,
            get_elite_client_data,
        ],
        model=model,
        # Allow non-strict JSON schema due to Dict fields in the model (additionalProperties)
        output_type=AgentOutputSchema(AssetAllocationAgentOutput, strict_json_schema=False),  # ✨ Structured Pydantic output
    )

    # Market Intelligence Agent - Market Context and Economic Insights
    market_intelligence = Agent(
        name="Elite_Market_Intelligence_Expert_V6",
        instructions=ELITE_MARKET_INTELLIGENCE_AGENT_PROMPT_V5,
        tools=[
            get_elite_market_data,  # Market indices and stock data
            get_elite_economic_indicators,  # Economic indicators
            get_elite_risk_scenarios,  # Market risk scenarios
        ],
        model=model,
        output_type=AgentOutputSchema(MarketIntelligenceAgentOutput, strict_json_schema=False),  # ✨ Structured Pydantic output
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
        "asset_allocation": asset_allocation,
        "market_intelligence": market_intelligence,
        "bancassurance": bancassurance,
        "rm_strategy": rm_strategy
    }


def main(client_id: str | None = None):
    """
    Main execution function - runs agents sequentially with structured outputs and timing.
    
    Execution Flow:
    1. Manager Agent
    2. Risk & Compliance Agent
    3. Asset Allocation Agent (Portfolio rebalancing recommendations)
    4. Market Intelligence Agent (NEW: Market context and economic insights)
    5. Investment Agent (receives asset allocation + market intelligence context)
    6. Loan Agent  
    7. Banking/CASA Agent
    8. Bancassurance Agent
    9. RM Strategy Agent (synthesizes all outputs)
    
    All agents run sequentially with comprehensive timing metrics.
    Clean, readable flow with utilities extracted to utils.py
    """
    # Print fancy header
    print("\n" + "="*100)
    print("🚀 ELITEX V7 - MULTI-AGENT FINANCIAL ANALYSIS SYSTEM".center(100))
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
    print("✅ All 9 agents initialized successfully\n")

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
    total_agents = 9
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
    print_progress_bar(completed_agents, total_agents, "Risk Agent Complete ✓")
        
    # ============================================================================
    # STEP 3: Asset Allocation Agent (NEW)
    # ============================================================================
    print("\n")
    completed_agents += 1
    print_progress_bar(completed_agents, total_agents, "Asset Allocation Agent Running...")
    
    asset_allocation_output, asset_allocation_time = _run_asset_allocation_agent(
        agents["asset_allocation"], client_id, manager_json, risk_json
    )
    agent_outputs["asset_allocation"] = asset_allocation_output
    execution_metrics["agent_timings"]["asset_allocation"] = asset_allocation_time
    
    # Save individual JSON
    with open(client_output_dir / "3_asset_allocation_agent.json", "w") as jf:
        jf.write(asset_allocation_output.model_dump_json(indent=2))
    print(f"💾 Saved: 3_asset_allocation_agent.json")
    
    asset_allocation_json = asset_allocation_output.model_dump_json(indent=2)
    print_progress_bar(completed_agents, total_agents, "Asset Allocation Agent Complete ✓")

    # ============================================================================
    # STEP 4: Market Intelligence Agent (NEW)
    # ============================================================================
    print("\n")
    completed_agents += 1
    print_progress_bar(completed_agents, total_agents, "Market Intelligence Agent Running...")

    market_intelligence_output, market_intelligence_time = _run_market_intelligence_agent(
        agents["market_intelligence"], client_id, manager_json, risk_json, asset_allocation_json
    )
    agent_outputs["market_intelligence"] = market_intelligence_output
    execution_metrics["agent_timings"]["market_intelligence"] = market_intelligence_time

    # Save individual JSON
    with open(client_output_dir / "4_market_intelligence_agent.json", "w") as jf:
        jf.write(market_intelligence_output.model_dump_json(indent=2))
    print(f"💾 Saved: 4_market_intelligence_agent.json")

    market_intelligence_json = market_intelligence_output.model_dump_json(indent=2)

    # Build combined context for specialist agents (now includes market intelligence)
    combined_context = f"MANAGER CONTEXT:\n{manager_json}\n\nRISK & COMPLIANCE CONTEXT:\n{risk_json}\n\nASSET ALLOCATION CONTEXT:\n{asset_allocation_json}\n\nMARKET INTELLIGENCE CONTEXT:\n{market_intelligence_json}\n"
    print_progress_bar(completed_agents, total_agents, "Market Intelligence Agent Complete ✓")

    # ============================================================================
    # STEP 5: Investment Agent
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
    with open(client_output_dir / "5_investment_agent.json", "w") as jf:
        jf.write(investment_output.model_dump_json(indent=2))
    print(f"💾 Saved: 5_investment_agent.json")
    print_progress_bar(completed_agents, total_agents, "Investment Agent Complete ✓")
        
    # ============================================================================
    # STEP 6: Loan Agent
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
    with open(client_output_dir / "6_loan_agent.json", "w") as jf:
        jf.write(loan_output.model_dump_json(indent=2))
    print(f"💾 Saved: 6_loan_agent.json")
    print_progress_bar(completed_agents, total_agents, "Loan Agent Complete ✓")
        
    # ============================================================================
    # STEP 7: Banking/CASA Agent
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
    with open(client_output_dir / "7_banking_casa_agent.json", "w") as jf:
        jf.write(banking_output.model_dump_json(indent=2))
    print(f"💾 Saved: 7_banking_casa_agent.json")
    print_progress_bar(completed_agents, total_agents, "Banking Agent Complete ✓")
        
    # ============================================================================
    # STEP 8: Bancassurance Agent
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
    with open(client_output_dir / "8_bancassurance_agent.json", "w") as jf:
        jf.write(bancassurance_output.model_dump_json(indent=2))
    print(f"💾 Saved: 8_bancassurance_agent.json")
    print_progress_bar(completed_agents, total_agents, "Bancassurance Agent Complete ✓")
        
    # ============================================================================
    # STEP 9: RM Strategy Agent (Final Synthesis)
    # ============================================================================
    print("\n")
    completed_agents += 1
    print_progress_bar(completed_agents, total_agents, "RM Strategy Agent Running...")
    
    rm_strategy_output, rm_strategy_time = _run_rm_strategy_agent(agents["rm_strategy"], client_id, agent_outputs)
    agent_outputs["rm_strategy"] = rm_strategy_output
    execution_metrics["agent_timings"]["rm_strategy"] = rm_strategy_time
    
    # Save individual JSON
    with open(client_output_dir / "9_rm_strategy_agent.json", "w") as jf:
        jf.write(rm_strategy_output.model_dump_json(indent=2))
    print(f"💾 Saved: 9_rm_strategy_agent.json")
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
        ("3. Asset Allocation Agent", execution_metrics['agent_timings']['asset_allocation']),
        ("4. Market Intelligence Agent", execution_metrics['agent_timings']['market_intelligence']),
        ("5. Investment Agent", execution_metrics['agent_timings']['investment']),
        ("6. Loan Agent", execution_metrics['agent_timings']['loan']),
        ("7. Banking Agent", execution_metrics['agent_timings']['banking']),
        ("8. Bancassurance Agent", execution_metrics['agent_timings']['bancassurance']),
        ("9. RM Strategy Agent", execution_metrics['agent_timings']['rm_strategy']),
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
    print(f"   ├─ 3_asset_allocation_agent.json")
    print(f"   ├─ 4_market_intelligence_agent.json")
    print(f"   ├─ 5_investment_agent.json")
    print(f"   ├─ 6_loan_agent.json")
    print(f"   ├─ 7_banking_casa_agent.json")
    print(f"   ├─ 8_bancassurance_agent.json")
    print(f"   └─ 9_rm_strategy_agent.json")
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


def _run_asset_allocation_agent(agent: Agent, client_id: str, manager_json: str, risk_json: str) -> tuple[AssetAllocationAgentOutput, float]:
    """Run Asset Allocation Agent and return structured output with execution time."""
    start_time = time.time()
    print(f"\n{'='*80}")
    print(f"📊 ASSET ALLOCATION AGENT - PORTFOLIO REBALANCING")
    print(f"{'='*80}")
    print(f"⏱️  Started at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"📋 Task: Portfolio allocation analysis, rebalancing recommendations, and risk assessment")
    print(f"🔄 Status: Running...")
    
    result = Runner.run_sync(
        starting_agent=agent,
        input=(
            f"Analyze asset allocation and provide rebalancing recommendations for client {client_id}. "
            f"Use the manager and risk context below to inform your analysis.\n\n"
            f"MANAGER CONTEXT:\n{manager_json}\n\n"
            f"RISK & COMPLIANCE CONTEXT:\n{risk_json}"
        ),
        max_turns=25,
    )
    
    execution_time = time.time() - start_time
    print(f"✅ Completed at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"⏱️  Execution Time: {execution_time:.2f} seconds ({execution_time/60:.1f} minutes)")
    print(f"{'='*80}\n")
    
    return result.final_output, execution_time


def _run_market_intelligence_agent(agent: Agent, client_id: str, manager_json: str, risk_json: str, asset_allocation_json: str) -> tuple[MarketIntelligenceAgentOutput, float]:
    """Run Market Intelligence Agent and return structured output with execution time."""
    start_time = time.time()
    print(f"\n{'='*80}")
    print(f"🌍 MARKET INTELLIGENCE AGENT - MARKET CONTEXT & ECONOMIC INSIGHTS")
    print(f"{'='*80}")
    print(f"⏱️  Started at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"📋 Task: Market analysis, economic indicators, risk scenarios, and investment themes")
    print(f"🔄 Status: Running...")
    
    result = Runner.run_sync(
        starting_agent=agent,
        input=(
            f"Provide comprehensive market intelligence analysis for client {client_id}. "
            f"Use the manager, risk, and asset allocation context below to inform your market insights.\n\n" 
            f"MANAGER CONTEXT:\n{manager_json}\n\nRISK & COMPLIANCE CONTEXT:\n{risk_json}\n\nASSET ALLOCATION CONTEXT:\n{asset_allocation_json}"
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
    print(f"🔄 Status: Processing outputs from 7 specialist agents...")
    
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
    ClientList=['10ALFHG', '10FPRKH', '10FXQPP', '10FARGP', '10AXRLF', '10AXGRL', '10FKQFL', '10APAAP', '10FRAQQ', '10FGALK', '10AGAHG', '10AFHHK', '10FPQQL', '10GAPPX', '10APALG', '10AGAHP', '10FLKRQ', '10FKRPQ', '10FKFRH', '10AFLQK', '10FHRGR', '10AAHAH', '10FHKPG', '10FHHQK', '10FHHPF']
    main(client_id='59QPQKX')

### 
# 56QPHKX
#59QPQKX
# 
# 
### 
# 
# ###

    
    
    
  

    


