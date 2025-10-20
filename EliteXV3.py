#!/usr/bin/env python3
"""
EliteX.pyV3 - Elite Financial Strategy Framework (fab_elite integration)

Changes vs V2:
- All database access now uses the Elite Engine from db_engine.py (fab_elite DB)
- Existing tools continue to work, now backed by the new engine
- Added an extended data tool to surface additional tables present in fab_elite
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import argparse

import pandas as pd
from sqlalchemy import text

# Engines
import db_engine  # uses elite_engine -> postgresql://.../fab_elite
from dotenv import load_dotenv

# Load environment (.env) so OPENAI_API_KEY and others are available
load_dotenv()

# Disable Agents SDK tracing before importing agents
os.environ["AGENTS_TRACING_DISABLED"] = "1"
from agents import Agent, Runner, function_tool  # type: ignore

# Prompts (reuse from V2)
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

logger = logging.getLogger("elite_agentsdk_v3")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(LOGS_DIR / "agent_conversations_elite_v3.log")
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
# Database Manager V3 (SQLAlchemy elite_engine)
# ----------------------------
class EliteDatabaseManagerV3:
    def __init__(self):
        self.engine = db_engine.elite_engine

    def _execute_query(self, query: str, params: tuple | List | Dict | None = None) -> List[Dict[str, Any]]:
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                rows = [dict(r._mapping) for r in result]
                return rows
        except Exception as e:
            logger.error(f"❌ Query execution failed: {e}")
            logger.error(f"❌ Query: {query[:200]}...")
            logger.error(f"❌ Params: {params}")
            return []

    def _json(self, obj: Any) -> str:
        return json.dumps(obj, indent=2, default=str)

    # --- Existing data methods (ported to SQLAlchemy) ---
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

        # Derived
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

    def get_elite_investment_data(self, client_id: str) -> str:
        holdings_q = """
        SELECT client_id, asset_class, product_type, security_name, 
               investment_value_usd, current_price
        FROM core.client_holding WHERE client_id = :cid LIMIT 200
        """
        funds_q = """
        SELECT id, name, investment_objective, total_net_assets,
               annualized_return_3y, annualized_return_5y, morningstar_rating
        FROM core.funds ORDER BY name LIMIT 50
        """
        client_investment_q = """
        SELECT time_key, portfolio_id, security_name, asset_class, sub_asset_type_desc,
               market_value_aed, market_price, quantity
        FROM core.client_investment
        WHERE client_id = :cid
        ORDER BY time_key DESC NULLS LAST
        LIMIT 100
        """
        holdings = self._execute_query(holdings_q, {"cid": client_id})
        funds = self._execute_query(funds_q)
        client_investment = self._execute_query(client_investment_q, {"cid": client_id})
        total_value = sum(float(h.get('investment_value_usd') or 0) for h in holdings)
        total_investment_aed = sum(float(x.get('market_value_aed') or 0) for x in client_investment)
        return self._json({
            "client_id": client_id,
            "current_holdings": holdings,
            "available_funds": funds,
            "client_investment_positions": client_investment,
            "client_investment_total_aed": total_investment_aed,
            "total_holdings_value": total_value,
            "holdings_count": len(holdings)
        })

    def get_elite_loan_data(self, client_id: str) -> str:
        tx_q = """
        SELECT transaction_id, client_id, transaction_type, transaction_amount, 
               date, currency, booking_geography, name
        FROM core.client_transaction 
        WHERE client_id = :cid AND transaction_type IN ('credit','loan','advance','Loan Payment')
        ORDER BY date DESC LIMIT 200
        """
        aedb_q = """
        SELECT risk_name, risk_level, match_diff_from_house_rec
        FROM core.client_holdings_risk_level 
        WHERE client_id = :cid
        ORDER BY risk_level DESC LIMIT 50
        """
        profile_q = """
        SELECT customer_profile_banking_segment, risk_appetite, income
        FROM core.client_context WHERE client_id = :cid LIMIT 1
        """
        transactions = self._execute_query(tx_q, {"cid": client_id})
        aedb_alerts = self._execute_query(aedb_q, {"cid": client_id})
        profile = self._execute_query(profile_q, {"cid": client_id})
        target_segment = (profile[0].get('customer_profile_banking_segment') if profile else 'mass_market') or 'mass_market'
        return self._json({
            "client_id": client_id,
            "client_segment": target_segment,
            "credit_transactions": transactions,
            "aedb_alerts": aedb_alerts,
            "products_count": 0
        })

    def get_elite_banking_casa_data(self, client_id: str) -> str:
        portfolio_q = """
        SELECT id, portfolio_id, client_id, portfolio_type, currency,
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
        FROM core.client_portfolio WHERE client_id = :cid
        ORDER BY last_valuation_date DESC LIMIT 5
        """
        tx_q = """
        SELECT transaction_id, client_id, transaction_type, transaction_amount, 
               date, currency, booking_geography, name
        FROM core.client_transaction 
        WHERE client_id = :cid AND transaction_type IN ('deposit','withdrawal','transfer','Deposit','Withdrawal','Transfer')
        AND date >= CURRENT_DATE - INTERVAL '6 months'
        ORDER BY date DESC LIMIT 200
        """
        productbalance_q = """
        SELECT load_ts, banking_type, product_description, product_levl1_desc,
               product_levl2_desc, product_levl3_desc, outstanding
        FROM core.productbalance
        WHERE customer_number = :cid
        ORDER BY load_ts DESC NULLS LAST
        LIMIT 200
        """
        portfolio = self._execute_query(portfolio_q, {"cid": client_id})
        transactions = self._execute_query(tx_q, {"cid": client_id})
        product_balances = self._execute_query(productbalance_q, {"cid": client_id})
        total_balance = sum(float(p.get('aum') or 0) for p in portfolio)
        return self._json({
            "client_id": client_id,
            "portfolio_balances": portfolio,
            "banking_transactions": transactions,
            "product_balances": product_balances,
            "total_balance": total_balance,
            "accounts_count": len(portfolio)
        })

    def get_elite_risk_compliance_data(self, client_id: str) -> str:
        risk_q = """
        SELECT client_id, risk_name, risk_level, match_diff_from_house_rec
        FROM core.client_holdings_risk_level WHERE client_id = :cid
        ORDER BY risk_level DESC LIMIT 20
        """
        commlog_complaints_q = """
        SELECT comm_log_id, client_id, type, subtype, description, status, communication_date
        FROM core.communication_log WHERE client_id = :cid AND type = 'complaint'
        ORDER BY communication_date DESC LIMIT 10
        """
        core_complaints_q = """
        SELECT ticket_id, date_id, ticket_ts, complaint_type, complaint_subtype, status
        FROM core.complaint WHERE client_id = :cid
        ORDER BY date_id DESC NULLS LAST, ticket_ts DESC NULLS LAST
        LIMIT 20
        """
        callreports_q = """
        SELECT call_report_id, date_id, purpose, meeting_type, meeting_channel
        FROM core.callreport WHERE client_id = :cid
        ORDER BY date_id DESC NULLS LAST, call_ts DESC NULLS LAST
        LIMIT 20
        """
        definitions_q = """
        SELECT name, level, segment, last_updated FROM core.risk_level_definition ORDER BY level
        """
        ai_insights_q = """
        SELECT title, description, last_update
        FROM core.ai_client_insights WHERE client_id = :cid
        ORDER BY last_update DESC NULLS LAST
        LIMIT 20
        """
        ai_summaries_q = """
        SELECT risk_level_summary, investment_goals_summary, last_updated
        FROM core.ai_client_summaries WHERE client_id = :cid
        ORDER BY last_updated DESC NULLS LAST
        LIMIT 5
        """
        declared_risk_q = """
        SELECT risk_appetite, risk_level, risk_segment
        FROM core.client_context WHERE client_id = :cid LIMIT 1
        """
        risk_alerts = self._execute_query(risk_q, {"cid": client_id})
        commlog_complaints = self._execute_query(commlog_complaints_q, {"cid": client_id})
        core_complaints = self._execute_query(core_complaints_q, {"cid": client_id})
        callreports = self._execute_query(callreports_q, {"cid": client_id})
        definitions = self._execute_query(definitions_q)
        ai_insights = self._execute_query(ai_insights_q, {"cid": client_id})
        ai_summaries = self._execute_query(ai_summaries_q, {"cid": client_id})
        declared_risk = self._execute_query(declared_risk_q, {"cid": client_id})
        top_alert = risk_alerts[0] if risk_alerts else None

        # Prepare labeled risk fields
        declared = {
            "appetite_code": (declared_risk[0].get("risk_appetite") if declared_risk else None),
            "level": (declared_risk[0].get("risk_level") if declared_risk else None),
            "segment": (declared_risk[0].get("risk_segment") if declared_risk else None),
            "meaning": "Client-declared risk preference/profile from core.client_context",
            "source": "core.client_context"
        }
        exposure = {
            "risk_name": (top_alert.get("risk_name") if top_alert else None),
            "level": (top_alert.get("risk_level") if top_alert else None),
            "meaning": "Portfolio/alert-based current risk exposure (top alert) from core.client_holdings_risk_level",
            "source": "core.client_holdings_risk_level"
        }
        try:
            gap = None
            if declared.get("level") is not None and exposure.get("level") is not None:
                gap = int(declared["level"]) - int(exposure["level"])  # positive means appetite > exposure
        except Exception:
            gap = None
        return self._json({
            "client_id": client_id,
            "focus_alert": top_alert,
            "all_aedb_alerts": risk_alerts,
            "communication_log_complaints": commlog_complaints,
            "core_complaints": core_complaints,
            "callreports": callreports,
            "risk_definitions": definitions,
            "ai_client_insights": ai_insights,
            "ai_client_summaries": ai_summaries,
            "declared_risk_profile": declared,
            "current_risk_exposure": exposure,
            "risk_gap_explanation": "risk_gap = declared_risk_profile.level - current_risk_exposure.level (positive => appetite above exposure)",
            "risk_gap": gap,
            "total_alerts": len(risk_alerts),
            "active_complaints": len(commlog_complaints) + len(core_complaints)
        })

    # --- Extended data (new tables in fab_elite) ---
    def get_elite_extended_data(self, client_id: str) -> str:
        """Aggregate insights from additional fab_elite tables for the client.
        This function adapts to column differences across tables.
        """
        out: Dict[str, Any] = {"client_id": client_id}

        # client_investment: has client_id and time_key
        out["client_investment"] = self._execute_query(
            "SELECT * FROM core.client_investment WHERE client_id = :cid ORDER BY time_key DESC LIMIT 50",
            {"cid": client_id},
        )

        # clienttransactionaccount: filter by customer_id if possible, else return latest records
        rows = self._execute_query(
            "SELECT * FROM core.clienttransactionaccount WHERE customer_id = :cid ORDER BY booking_date DESC NULLS LAST LIMIT 50",
            {"cid": client_id},
        )
        if not rows:
            rows = self._execute_query(
                "SELECT * FROM core.clienttransactionaccount ORDER BY booking_date DESC NULLS LAST LIMIT 20",
            )
        out["clienttransactionaccount"] = rows

        # clienttransactioncredit: filter by customer_number and order by txn_date
        rows = self._execute_query(
            "SELECT * FROM core.clienttransactioncredit WHERE customer_number = :cid ORDER BY txn_date DESC NULLS LAST LIMIT 50",
            {"cid": client_id},
        )
        if not rows:
            rows = self._execute_query(
                "SELECT * FROM core.clienttransactioncredit ORDER BY txn_date DESC NULLS LAST LIMIT 20",
            )
        out["clienttransactioncredit"] = rows

        # clienttransactiondebit: filter by customer_number and order by txn_date
        rows = self._execute_query(
            "SELECT * FROM core.clienttransactiondebit WHERE customer_number = :cid ORDER BY txn_date DESC NULLS LAST LIMIT 50",
            {"cid": client_id},
        )
        if not rows:
            rows = self._execute_query(
                "SELECT * FROM core.clienttransactiondebit ORDER BY txn_date DESC NULLS LAST LIMIT 20",
            )
        out["clienttransactiondebit"] = rows

        # complaint: client_id, with date_id and ticket_ts for ordering
        out["complaint"] = self._execute_query(
            "SELECT * FROM core.complaint WHERE client_id = :cid ORDER BY date_id DESC NULLS LAST, ticket_ts DESC NULLS LAST LIMIT 20",
            {"cid": client_id},
        )

        # callreport: has client_id and date_id
        out["callreport"] = self._execute_query(
            "SELECT * FROM core.callreport WHERE client_id = :cid ORDER BY date_id DESC NULLS LAST LIMIT 20",
            {"cid": client_id},
        )

        # ai_client_* have client_id
        out["ai_client_insights"] = self._execute_query(
            "SELECT * FROM core.ai_client_insights WHERE client_id = :cid ORDER BY last_update DESC NULLS LAST LIMIT 20",
            {"cid": client_id},
        )
        out["ai_client_summaries"] = self._execute_query(
            "SELECT * FROM core.ai_client_summaries WHERE client_id = :cid ORDER BY last_updated DESC NULLS LAST LIMIT 5",
            {"cid": client_id},
        )

        # productbalance: filter by customer_number; order by load_ts
        rows = self._execute_query(
            "SELECT * FROM core.productbalance WHERE customer_number = :cid ORDER BY load_ts DESC NULLS LAST LIMIT 20",
            {"cid": client_id},
        )
        if not rows:
            rows = self._execute_query(
                "SELECT * FROM core.productbalance ORDER BY load_ts DESC NULLS LAST LIMIT 20",
            )
        out["productbalance"] = rows

        return self._json(out)

    def get_elite_upsell_potential(self, client_id: str) -> str:
        """Fetch upsell opportunities for the given client.
        Uses column delta as the upsell potential value for (client_id, category).
        No computation/subtraction performed here; values are read as-is.
        Detects available table name to avoid error logs.
        """
        # Detect available upsell table name to avoid querying non-existent tables
        tables = self._execute_query(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='app' AND table_name IN (
                'upsellopportunity','upselloppurtunity','upselloppurtunities'
            )
            """
        )
        table_names = {t.get("table_name") for t in tables}
        source = None
        chosen = None
        for cand in ("upsellopportunity", "upselloppurtunity", "upselloppurtunities"):
            if cand in table_names:
                chosen = cand
                source = f"app.{cand}"
                break
        if not chosen:
            return self._json({
                "client_id": client_id,
                "source": None,
                "opportunities": []
            })

        rows = self._execute_query(
            f"""
            SELECT client_id, category, delta
            FROM app.{chosen}
            WHERE LOWER(client_id) = LOWER(:cid)
            ORDER BY delta DESC NULLS LAST
            """,
            {"cid": client_id},
        )

        # Normalize to a simple structure: product + upsell_potential
        opportunities: List[Dict[str, Any]] = []
        for r in rows:
            product = r.get("category") or r.get("product")
            delta = r.get("delta")
            try:
                delta = float(delta) if delta is not None else None
            except Exception:
                pass
            if product is None:
                continue
            opportunities.append({
                "product": product,
                "upsell_potential": delta,
            })
        return self._json({
            "client_id": client_id,
            "source": source,
            "opportunities": opportunities
        })

    def get_elite_spend_analytics_unified(self, client_id: str) -> str:
        """Aggregate a unified transaction feed across core.client_transaction,
        core.clienttransactionaccount, core.clienttransactioncredit, core.clienttransactiondebit.
        Returns a feed and grouped summary suitable for Manager context spend analytics.
        """
        feed: List[Dict[str, Any]] = []

        # 1) Banking/loan direct transactions
        ct_rows = self._execute_query(
            """
            SELECT date, transaction_type, transaction_amount AS amount, currency, booking_geography, name
            FROM core.client_transaction
            WHERE client_id = :cid
            ORDER BY date DESC LIMIT 500
            """,
            {"cid": client_id},
        )
        for r in ct_rows:
            ttype = (r.get("transaction_type") or "").lower()
            if any(x in ttype for x in ["deposit"]):
                cat = "deposit"
            elif any(x in ttype for x in ["withdrawal"]):
                cat = "withdrawal"
            elif any(x in ttype for x in ["transfer"]):
                cat = "transfer"
            elif any(x in ttype for x in ["loan", "credit"]):
                cat = "loan/credit"
            else:
                cat = "bank_tx_other"
            feed.append({
                "date": r.get("date"),
                "amount": float(r.get("amount") or 0),
                "currency": r.get("currency"),
                "source": "core.client_transaction",
                "category": cat,
                "subtype": r.get("transaction_type"),
                "description": r.get("name"),
                "geography": r.get("booking_geography"),
            })

        # 2) Account postings
        cta_rows = self._execute_query(
            """
            SELECT booking_date, amount_lcy AS amount, currency, transaction_type, category_desc, channel_identifier
            FROM core.clienttransactionaccount
            WHERE customer_id = :cid
            ORDER BY booking_date DESC NULLS LAST LIMIT 500
            """,
            {"cid": client_id},
        )
        for r in cta_rows:
            feed.append({
                "date": r.get("booking_date"),
                "amount": float(r.get("amount") or 0),
                "currency": r.get("currency"),
                "source": "core.clienttransactionaccount",
                "category": "account_posting",
                "subtype": r.get("transaction_type") or r.get("category_desc"),
                "description": r.get("category_desc"),
                "channel": r.get("channel_identifier"),
            })

        # 3) Credit card
        ctc_rows = self._execute_query(
            """
            SELECT txn_date, destination_amount AS amount, destination_currency AS currency,
                   merchant_name, mcc_code, mcc_desc, direction
            FROM core.clienttransactioncredit
            WHERE customer_number = :cid
            ORDER BY txn_date DESC NULLS LAST LIMIT 500
            """,
            {"cid": client_id},
        )
        for r in ctc_rows:
            feed.append({
                "date": r.get("txn_date"),
                "amount": float(r.get("amount") or 0),
                "currency": r.get("currency"),
                "source": "core.clienttransactioncredit",
                "category": "card_credit",
                "subtype": r.get("direction"),
                "description": r.get("merchant_name") or r.get("mcc_desc"),
                "mcc": r.get("mcc_code"),
            })

        # 4) Debit card
        ctd_rows = self._execute_query(
            """
            SELECT txn_date, amount, currency, transaction_type, transaction_type_desc, dest_country, merch_categ, mcc_desc
            FROM core.clienttransactiondebit
            WHERE customer_number = :cid
            ORDER BY txn_date DESC NULLS LAST LIMIT 500
            """,
            {"cid": client_id},
        )
        for r in ctd_rows:
            feed.append({
                "date": r.get("txn_date"),
                "amount": float(r.get("amount") or 0),
                "currency": r.get("currency"),
                "source": "core.clienttransactiondebit",
                "category": "card_debit",
                "subtype": r.get("transaction_type") or r.get("transaction_type_desc"),
                "description": r.get("mcc_desc"),
                "country": r.get("dest_country"),
            })

        # Build grouped summary
        by_category: Dict[str, Dict[str, Any]] = {}
        total_amount = 0.0
        for item in feed:
            cat = item.get("category") or "unknown"
            amt = float(item.get("amount") or 0)
            total_amount += amt
            grp = by_category.setdefault(cat, {"count": 0, "total_amount": 0.0})
            grp["count"] += 1
            grp["total_amount"] += amt

        # Sort feed by date desc and trim
        def sort_key(x):
            return (str(x.get("date")), )
        feed_sorted = sorted(feed, key=sort_key, reverse=True)[:200]

        return self._json({
            "client_id": client_id,
            "unified_feed": feed_sorted,
            "summary": {
                "by_category": by_category,
                "total_count": len(feed),
                "total_amount": total_amount,
            },
            "sources": [
                "core.client_transaction",
                "core.clienttransactionaccount",
                "core.clienttransactioncredit",
                "core.clienttransactiondebit",
            ]
        })

    def get_elite_aecb_alerts_for_manager(self, client_id: str) -> str:
        """Fetch AECB alerts tied to this client (by cif/cif2) for Manager prioritization.
        Returns raw rows plus a summary grouped by description/description_1.
        """
        aecb_alerts_q = """
        SELECT id, cif, cif2, role, balance, number1, category, opendate, recordid,
               load_date, cbsubjectid, cbtriggerid, creditlimit, description, subjectrole,
               totalamount, warning_msg, billedamount, contracttype, dateofreturn, providercode,
               description_1, overdueamount, extractdatetime, directdebitamount, contractstatusdate,
               bouncedchequeamount, salarycreditedamount, suspiciousactivityflagdate, file_source,
               creation_ts, load_ts, last_updated
        FROM core.aecbalerts
        WHERE LOWER(cif) = LOWER(:cid) OR LOWER(cif2) = LOWER(:cid)
        ORDER BY load_ts DESC NULLS LAST, load_date DESC NULLS LAST
        LIMIT 200
        """
        rows = self._execute_query(aecb_alerts_q, {"cid": client_id})
        summary_by_type: Dict[str, Dict[str, Any]] = {}
        def f(x):
            try:
                return float(x)
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
            entry["total_totalamount"] += f(a.get("totalamount"))
            entry["total_overdueamount"] += f(a.get("overdueamount"))
            entry["total_billedamount"] += f(a.get("billedamount"))
            entry["total_bouncedchequeamount"] += f(a.get("bouncedchequeamount"))
            entry["total_salarycreditedamount"] += f(a.get("salarycreditedamount"))
            entry["total_directdebitamount"] += f(a.get("directdebitamount"))
        return self._json({
            "client_id": client_id,
            "aecb_alerts": rows,
            "aecb_alerts_summary": summary_by_type,
            "source": "core.aecbalerts"
        })


# ----------------------------
# Initialize DB Manager V3
# ----------------------------
db_manager = EliteDatabaseManagerV3()


# ----------------------------
# Tools
# ----------------------------
@function_tool
def get_elite_client_data(client_id: str) -> str:
    return db_manager.get_elite_client_data(client_id)

@function_tool
def get_elite_investment_data(client_id: str) -> str:
    return db_manager.get_elite_investment_data(client_id)

@function_tool
def get_elite_loan_data(client_id: str) -> str:
    return db_manager.get_elite_loan_data(client_id)

@function_tool
def get_elite_banking_casa_data(client_id: str) -> str:
    return db_manager.get_elite_banking_casa_data(client_id)

@function_tool
def get_elite_risk_compliance_data(client_id: str) -> str:
    return db_manager.get_elite_risk_compliance_data(client_id)

@function_tool
def get_elite_extended_data(client_id: str) -> str:
    """Deprecated shim - extended data merged into investment/banking/risk calls."""
    return json.dumps({
        "warning": "get_elite_extended_data merged into core tools in V3",
        "investment_extra": json.loads(db_manager.get_elite_investment_data(client_id)).get("client_investment_positions"),
        "banking_extra": json.loads(db_manager.get_elite_banking_casa_data(client_id)).get("product_balances"),
        "risk_extra": {
            "callreports": json.loads(db_manager.get_elite_risk_compliance_data(client_id)).get("callreports")
        }
    }, indent=2)

@function_tool
def get_elite_upsell_potential(client_id: str) -> str:
    return db_manager.get_elite_upsell_potential(client_id)

@function_tool
def get_elite_spend_analytics_unified(client_id: str) -> str:
    return db_manager.get_elite_spend_analytics_unified(client_id)

@function_tool
def get_elite_aecb_alerts_for_manager(client_id: str) -> str:
    return db_manager.get_elite_aecb_alerts_for_manager(client_id)


# ----------------------------
# Agents
# ----------------------------
def create_elite_agents() -> Dict[str, Agent]:
    model = os.getenv("OPENAI_MODEL", "gpt-4o")

    manager = Agent(
        name="Elite_Manager_V3",
        instructions=ELITE_MANAGER_AGENT_PROMPT,
        tools=[
            get_elite_client_data,
            get_elite_extended_data,  # shim; core tools now include extended content
            get_elite_banking_casa_data,
            get_elite_aecb_alerts_for_manager,  # prioritize alerts for product recommendation
            get_elite_upsell_potential,  # upsell computation for context
            get_elite_spend_analytics_unified,  # unified spend analytics
        ],
        model=model,
    )

    investment = Agent(
        name="Elite_Investment_Expert_V3",
        instructions=ELITE_INVESTMENT_AGENT_PROMPT_UPDATED,
        tools=[get_elite_investment_data, get_elite_client_data, get_elite_extended_data],
        model=model,
    )

    loan = Agent(
        name="Elite_Loan_Expert_V3",
        instructions=ELITE_LOAN_AGENT_PROMPT_UPDATED,
        tools=[get_elite_loan_data, get_elite_client_data, get_elite_extended_data, get_elite_risk_compliance_data],
        model=model,
    )

    banking_casa = Agent(
        name="Elite_BankingCASA_Expert_V3",
        instructions=ELITE_BANKING_CASA_AGENT_PROMPT_UPDATED,
        tools=[get_elite_banking_casa_data, get_elite_client_data, get_elite_extended_data],
        model=model,
    )

    risk_compliance = Agent(
        name="Elite_Risk_Compliance_Expert_V3",
        instructions=ELITE_RISK_COMPLIANCE_AGENT_PROMPT_UPDATED,
        tools=[get_elite_risk_compliance_data, get_elite_client_data, get_elite_extended_data],
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
# Orchestrated run: Manager -> Risk/Compliance -> Combined context to others
# ----------------------------
def main(client_id: str | None = None):
    print("🚀 EliteX V3 - fab_elite integration")
    print("=" * 80)
    agents = create_elite_agents()

    # Resolve client id
    def _exists(cid: str) -> bool:
        rows = db_manager._execute_query("SELECT 1 FROM core.client_context WHERE client_id = :cid LIMIT 1", {"cid": cid})
        return bool(rows)

    if not client_id:
        rows = db_manager._execute_query("SELECT client_id FROM core.client_context ORDER BY client_id ASC LIMIT 1")
        client_id = rows[0].get("client_id") if rows else None
    if not client_id or not _exists(client_id):
        raise RuntimeError("Client not found")

    # Log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    consolidated_log_file_path = LOGS_DIR / f"elite_analysis_v3_{client_id}_{timestamp}.txt"
    with open(consolidated_log_file_path, 'w', encoding='utf-8') as consolidated_log_file:
        consolidated_log_file.write(f"🚀 EliteX V3 - fab_elite integration\nClient: {client_id}\nTimestamp: {datetime.now()}\n{'='*80}\n\n")
        consolidated_log_file.flush()

        # STEP 1: Manager context
        print("\n🎯 STEP 1: Manager Context Setting")
        manager_res = Runner.run_sync(
            starting_agent=agents["manager"],
            input=f"Set context for client {client_id}",
            max_turns=5,
        )
        manager_context = manager_res.final_output
        print(manager_context)
        consolidated_log_file.write(f"Manager Context:\n{manager_context}\n")
        consolidated_log_file.flush()

        # STEP 2: Risk & Compliance assessment (after Manager)
        print("\n🛡️ STEP 2: Risk & Compliance Assessment")
        risk_input = (
            f"Assess risk & compliance for client {client_id}. "
            f"Use the INITIAL MANAGER CONTEXT below to inform your assessment.\n\n" \
            f"INITIAL MANAGER CONTEXT:\n{manager_context}\n"
        )
        risk_res = Runner.run_sync(
            starting_agent=agents["risk_compliance"],
            input=risk_input,
            max_turns=5,
        )
        risk_context = risk_res.final_output
        print(risk_context)
        consolidated_log_file.write(f"\nRisk & Compliance Context:\n{risk_context}\n")
        consolidated_log_file.flush()

        # STEP 3: Build COMBINED CONTEXT (Manager + Risk/Compliance)
        combined_context = (
            f"MANAGER CONTEXT:\n{manager_context}\n\n"
            f"RISK & COMPLIANCE CONTEXT:\n{risk_context}\n"
        )
        consolidated_log_file.write("\nCombined Context prepared for downstream agents.\n")
        consolidated_log_file.flush()

        # STEP 4: Specialized agents consume COMBINED CONTEXT
        for name, title in [
            ("investment", "Investment"),
            ("loan", "Loan"),
            ("banking_casa", "Banking_CASA"),
        ]:
            print(f"\n🔍 {title} Analysis (using COMBINED CONTEXT)...")
            specialized_input = (
                f"Use the COMBINED CONTEXT (Manager + Risk & Compliance) below to analyze {title} for client {client_id}.\n\n"
                f"MANDATORY: If AECB alerts/leads are present in Manager context, explicitly action them first in an 'AECB Lead Actions' section, or state N/A with a reason.\n\n"
                f"COMBINED CONTEXT:\n{combined_context}"
            )
            res = Runner.run_sync(starting_agent=agents[name], input=specialized_input, max_turns=5)
            print(res.final_output)
            consolidated_log_file.write(f"\n{title} Response:\n{res.final_output}\n")
            consolidated_log_file.flush()

        print(f"\n🎉 V3 analysis completed. Log: {consolidated_log_file_path}")


if __name__ == "__main__":
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

    main(client_id='11XLALK')


