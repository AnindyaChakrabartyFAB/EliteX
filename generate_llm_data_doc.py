#!/usr/bin/env python3
"""
Generate LLM Data Documentation
Creates a comprehensive markdown document showing all JSON data fed into each agent
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Import the data manager
from EliteXV5 import EliteDatabaseManagerV5

def format_json_for_display(json_str: str, max_records: int = 3) -> dict:
    """Parse JSON and optionally truncate large arrays for display"""
    try:
        data = json.loads(json_str)
        
        # For arrays with many records, show only first few
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list) and len(value) > max_records:
                    data[key] = value[:max_records] + [f"... ({len(value) - max_records} more records)"]
        
        return data
    except:
        return {"raw": json_str}

def get_table_info(function_name: str) -> dict:
    """Return metadata about each data function"""
    info = {
        "get_elite_client_data": {
            "tables": ["core.client_context"],
            "description": "Comprehensive client profile including demographics, risk profile, banking segment, and relationship details",
            "transformations": [
                "Calculate life stage based on age",
                "Calculate risk capacity from income and banking segment",
                "Calculate sophistication level from investor flag and segment",
                "Calculate client tier from segment and income",
                "Calculate relationship strength from tenure"
            ]
        },
        "get_elite_client_investments_summary": {
            "tables": ["core.client_holding", "core.client_investment"],
            "description": "Complete investment portfolio including current holdings, positions, performance metrics, and asset allocation",
            "transformations": [
                "Calculate total holdings value in USD",
                "Calculate total positions value in AED",
                "Group holdings by asset class",
                "Calculate asset allocation percentages",
                "Aggregate holdings and positions count"
            ]
        },
        "get_elite_investment_products_not_held": {
            "tables": ["core.funds", "core.bonds", "core.stocks", "core.client_holding", "core.client_investment"],
            "description": "Investment products (funds, bonds, stocks) that client does NOT currently hold - opportunities for new investments",
            "transformations": [
                "Normalize product names for case-insensitive comparison",
                "Filter products by checking against client holdings",
                "Group by product type (funds, bonds, stocks)",
                "Limit to top 100 per product type"
            ]
        },
        "get_elite_banking_casa_data": {
            "tables": ["core.client_portfolio", "core.productbalance", "core.client_prod_balance_monthly"],
            "description": "Banking relationship data including portfolio summary, CASA accounts, and deposit trend analysis",
            "transformations": [
                "Sum total CASA balance from all accounts",
                "Categorize accounts into Current and Savings",
                "Calculate 6-month average deposit balance",
                "Calculate deposit trend percentage",
                "Generate recommendation flag (investment/loan/maintain) based on trend",
                "Generate RM recommendation text based on deposit pattern"
            ]
        },
        "get_elite_risk_compliance_data": {
            "tables": ["core.client_holdings_risk_level"],
            "description": "Risk alerts and compliance flags for client holdings",
            "transformations": [
                "Sort by risk level (highest first)",
                "Limit to top 20 alerts"
            ]
        },
        "get_elite_recommended_actions_data": {
            "tables": ["app.client", "app.maturityopportunity", "core.rmclientservicerequests", "core.client_portfolio"],
            "description": "Actionable items including KYC expiry, maturing products, open service requests, and portfolio context",
            "transformations": [
                "Handle alternative column names (due_for_follow_up vs due_for_followup)",
                "Filter maturing products to next 3 months",
                "Filter service requests by active status codes",
                "Select most recent portfolio record"
            ]
        },
        "get_elite_aecb_alerts": {
            "tables": ["core.aecbalerts"],
            "description": "Credit bureau alerts from AECB (Al Etihad Credit Bureau) showing credit inquiries and behavior",
            "transformations": [
                "Match by CIF or CIF2",
                "Sort by load timestamp (most recent first)",
                "Aggregate alerts by description type",
                "Sum amounts by alert category (total, overdue, billed, bounced cheque, salary, direct debit)"
            ]
        },
        "get_elite_loan_data": {
            "tables": ["core.client_transaction", "core.clienttransactiondebit", "core.clienttransactioncredit", "core.productbalance", "core.aecbalerts", "core.client_context", "core.credit_products"],
            "description": "Comprehensive loan and credit data including existing loans, payments, credit card transactions, and product catalog",
            "transformations": [
                "Filter credit transactions by type (credit, loan, advance, loan payment)",
                "Filter debit transactions for loan-related narratives",
                "Categorize existing loans by type (auto, mortgage, personal, credit card, other)",
                "Calculate total credit card spend",
                "Dynamic column mapping to handle schema variations"
            ]
        },
        "get_elite_client_behavior_analysis": {
            "tables": ["core.client_transaction", "core.clienttransactionaccount", "core.clienttransactioncredit", "core.clienttransactiondebit"],
            "description": "Behavioral analysis with transaction segregation by category (trading/investment, loan/credit, banking/CASA, spending patterns)",
            "transformations": [
                "Segregate transactions by type (trading, banking, credit, debit)",
                "Aggregate spending by merchant category (MCC codes)",
                "Count transaction types",
                "Calculate top 10 spending categories",
                "Calculate transaction summary totals"
            ]
        },
        "get_elite_share_of_potential": {
            "tables": ["app.upsellopportunity (or variants: upselloppurtunity, upselloppurtunities)"],
            "description": "Upsell opportunities based on share-of-wallet analysis showing potential revenue by product category",
            "transformations": [
                "Handle alternative table names",
                "Sort by delta (highest potential first)",
                "Map category/product fields"
            ]
        },
        "get_elite_engagement_analysis": {
            "tables": ["core.engagement_analysis", "core.communication_log (fallback)"],
            "description": "Client engagement metrics and communication interaction patterns",
            "transformations": [
                "Try engagement_analysis table first",
                "Fallback to communication_log if engagement table not available",
                "Aggregate by communication type",
                "Dynamic column mapping for client ID variations"
            ]
        },
        "get_elite_communication_history": {
            "tables": ["core.communication_log", "core.callreport"],
            "description": "Comprehensive communication history from structured logs and detailed call/meeting reports with transcripts",
            "transformations": [
                "Combine data from multiple communication sources",
                "Standardize column names across sources",
                "Concatenate call report fields (points_discussed, background, opportunities)",
                "Preview transcripts (first 500 chars)",
                "Sort all communications by date (most recent first)",
                "Limit to 200 most recent communications"
            ]
        },
        "get_rm_details": {
            "tables": ["core.user_join_client_context", "core.users", "core.rm_portfolio"],
            "description": "Relationship Manager assignment and details for the client",
            "transformations": [
                "Look up RM ID from client context",
                "Join RM name from users or rm_portfolio table",
                "Extract relation type"
            ]
        },
        "get_elite_rm_strategy": {
            "tables": ["core.user_join_client_context", "core.users", "core.client_portfolio", "core.communication_log"],
            "description": "RM strategy context including RM details, client AUM, and recent communications",
            "transformations": [
                "Look up RM ID and name",
                "Get most recent AUM from portfolio",
                "Get last 50 communications sorted by date"
            ]
        },
        "get_maturing_products_6m": {
            "tables": ["app.maturityopportunity (or maturity_opportunity)"],
            "description": "Products maturing within next 6 months requiring client follow-up",
            "transformations": [
                "Filter by maturity date between today and +6 months",
                "Sort by maturity date ascending",
                "Dynamic column name mapping"
            ]
        },
        "get_kyc_expiring_within_6m": {
            "tables": ["app.client"],
            "description": "KYC expiry information for compliance tracking",
            "transformations": [
                "Check if KYC expiry date exists and falls within 6 months"
            ]
        },
        "get_funds_catalog": {
            "tables": ["core.funds"],
            "description": "Investment funds catalog with performance metrics and ratings",
            "transformations": [
                "Limit to 500 funds",
                "Sort by name"
            ]
        },
        "get_bonds_catalog": {
            "tables": ["core.bonds"],
            "description": "Bond products catalog with ratings, yields, and terms",
            "transformations": [
                "Dynamic column mapping for schema variations",
                "Standardize column aliases",
                "Limit to 50 bonds"
            ]
        },
        "get_stocks_catalog": {
            "tables": ["core.stocks"],
            "description": "Stock/equity catalog with sector, prices, and volatility metrics",
            "transformations": [
                "Dynamic column mapping for schema variations",
                "Standardize column aliases",
                "Limit to 50 stocks"
            ]
        },
        "get_loan_products_catalog": {
            "tables": ["data/core_credit_products.xlsx (Excel file)"],
            "description": "Comprehensive loan and credit products catalog with eligibility criteria, rates, and terms",
            "transformations": [
                "Read from Excel file",
                "Convert NaN to None for JSON serialization",
                "Convert timestamps to strings",
                "Group products by product type"
            ]
        },
        "get_eligible_loan_products": {
            "tables": ["data/core_credit_products.xlsx (Excel file)", "core.client_context", "core.client_portfolio"],
            "description": "Filtered loan products that client is ELIGIBLE for with scoring and reasoning",
            "transformations": [
                "Calculate eligibility score (0-100) based on 4 factors:",
                "  - Segment matching (40 points)",
                "  - Income/Amount validation (30 points)",
                "  - Risk alignment (20 points)",
                "  - Collateral availability (10 points)",
                "Estimate lending capacity (5x income or 30% of AUM)",
                "Calculate recommended amount range",
                "Sort by eligibility score",
                "Separate eligible (>=60) from ineligible products"
            ]
        }
    }
    
    return info.get(function_name, {
        "tables": ["Unknown"],
        "description": "No description available",
        "transformations": []
    })

def generate_markdown_doc(client_id: str, output_file: str):
    """Generate comprehensive markdown documentation for all agent data"""
    
    print(f"🔍 Generating LLM data documentation for client: {client_id}")
    
    db = EliteDatabaseManagerV5()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    md_content = []
    md_content.append(f"# LLM Agent Data Documentation")
    md_content.append(f"\n**Client ID:** `{client_id}`")
    md_content.append(f"\n**Generated:** {timestamp}")
    md_content.append(f"\n**Purpose:** This document shows all JSON data fed into each AI agent for analysis and recommendations.")
    md_content.append("\n---\n")
    
    # Table of Contents
    md_content.append("## Table of Contents\n")
    md_content.append("1. [Section 1: Manager Agent](#section-1-manager-agent)")
    md_content.append("2. [Section 2: Investment Agent](#section-2-investment-agent)")
    md_content.append("3. [Section 3: Loan Agent](#section-3-loan-agent)")
    md_content.append("4. [Section 4: Banking/CASA Agent](#section-4-bankingcasa-agent)")
    md_content.append("5. [Section 5: Risk & Compliance Agent](#section-5-risk--compliance-agent)")
    md_content.append("\n---\n")
    
    # Define agent tools mapping
    agent_tools = {
        "Manager Agent": [
            "get_elite_client_data",
            "get_rm_details",
            "get_elite_share_of_potential",
            "get_elite_client_behavior_analysis",
            "get_elite_banking_casa_data",
            "get_elite_engagement_analysis",
            "get_elite_communication_history",
            "get_elite_rm_strategy",
            "get_elite_client_investments_summary",
            "get_elite_recommended_actions_data",
            "get_elite_aecb_alerts",
            "get_maturing_products_6m",
            "get_kyc_expiring_within_6m"
        ],
        "Investment Agent": [
            "get_elite_client_data",
            "get_elite_client_investments_summary",
            "get_elite_investment_products_not_held",
            "get_elite_share_of_potential",
            "get_funds_catalog",
            "get_bonds_catalog",
            "get_stocks_catalog"
        ],
        "Loan Agent": [
            "get_elite_loan_data",
            "get_elite_client_data",
            "get_elite_client_behavior_analysis",
            "get_elite_risk_compliance_data",
            "get_elite_banking_casa_data",
            "get_eligible_loan_products",
            "get_loan_products_catalog"
        ],
        "Banking/CASA Agent": [
            "get_elite_banking_casa_data",
            "get_elite_client_data"
        ],
        "Risk & Compliance Agent": [
            "get_elite_risk_compliance_data",
            "get_elite_client_data"
        ]
    }
    
    # Generate sections for each agent
    section_num = 1
    for agent_name, tool_functions in agent_tools.items():
        md_content.append(f"\n## Section {section_num}: {agent_name}\n")
        md_content.append(f"**Description:** This section shows all data sources available to the {agent_name}.\n")
        md_content.append(f"**Number of Tools:** {len(tool_functions)}\n")
        
        # Process each tool function
        for idx, func_name in enumerate(tool_functions, 1):
            md_content.append(f"\n### {section_num}.{idx} `{func_name}`\n")
            
            # Get metadata
            info = get_table_info(func_name)
            
            # Add table information
            md_content.append(f"**Source Tables/Files:**")
            for table in info['tables']:
                md_content.append(f"- `{table}`")
            
            md_content.append(f"\n**Description:** {info['description']}\n")
            
            # Add transformations
            if info['transformations']:
                md_content.append(f"**Transformations Applied:**")
                for transform in info['transformations']:
                    md_content.append(f"- {transform}")
                md_content.append("")
            
            # Fetch actual data
            try:
                print(f"  Fetching {func_name}...")
                
                # Call the appropriate function
                method = getattr(db, func_name, None)
                if method:
                    if func_name in ['get_funds_catalog', 'get_bonds_catalog', 'get_stocks_catalog', 'get_loan_products_catalog']:
                        # No client_id parameter
                        json_data = method()
                    else:
                        # Requires client_id
                        json_data = method(client_id)
                    
                    # Parse and format JSON
                    data_dict = json.loads(json_data)
                    
                    # Add metadata summary
                    md_content.append("**Data Summary:**")
                    for key, value in data_dict.items():
                        if isinstance(value, list):
                            md_content.append(f"- `{key}`: {len(value)} records")
                        elif isinstance(value, dict):
                            md_content.append(f"- `{key}`: {len(value)} fields")
                        else:
                            md_content.append(f"- `{key}`: {type(value).__name__}")
                    md_content.append("")
                    
                    # Add FULL actual JSON data (no truncation)
                    md_content.append("**Complete JSON Output (All Records):**\n")
                    md_content.append("```json")
                    md_content.append(json.dumps(data_dict, indent=2, default=str))
                    md_content.append("```\n")
                    
                else:
                    md_content.append(f"**Note:** Function not found in database manager\n")
                    
            except Exception as e:
                md_content.append(f"**Error fetching data:** {str(e)}\n")
        
        section_num += 1
        md_content.append("\n---\n")
    
    # Write to file
    output_path = Path(output_file)
    output_path.write_text("\n".join(md_content), encoding='utf-8')
    
    print(f"✅ Documentation generated: {output_path}")
    print(f"📄 File size: {output_path.stat().st_size / 1024:.2f} KB")
    
    return output_path

if __name__ == "__main__":
    # Get client ID from command line or use default
    client_id = sys.argv[1] if len(sys.argv) > 1 else "19RAFLH"
    
    # Generate output filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"/Users/anindyachakrabarty/Desktop/Application/Client Room/LLM_DATA_DOCUMENTATION_{client_id}_{timestamp}.md"
    
    # Generate documentation
    generate_markdown_doc(client_id, output_file)

