"""
Simplified utility functions for creating readable reports from EliteX V8 output
Compatible with simplified Pydantic models
"""

import json
from pathlib import Path
from decimal import Decimal


def create_readable_report(agent_outputs, output_folder, execution_metrics):
    """
    Create a simplified readable text report from all agent outputs
    
    Args:
        agent_outputs: Dictionary containing all agent outputs
        output_folder: Path to output folder
        execution_metrics: Dictionary with timing metrics
    """
    
    report_file = Path(output_folder) / "COMPLETE_ANALYSIS_REPORT.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("="*100 + "\n")
        f.write("ELITEX V8 - COMPLETE CLIENT ANALYSIS REPORT (SIMPLIFIED)\n")
        f.write("="*100 + "\n\n")
        
        f.write(f"Analysis Date: {execution_metrics.get('start_time', 'N/A')}\n")
        f.write(f"Total Execution Time: {execution_metrics['total_time']:.1f} seconds ({execution_metrics['total_time']/60:.1f} minutes)\n\n")
        
        # SECTION 1: Manager Agent - Client Overview
        f.write("\n" + "#"*100 + "\n")
        f.write(f"# SECTION 1: CLIENT OVERVIEW & CONTEXT\n")
        f.write("#"*100 + "\n\n")
        
        manager = agent_outputs["manager"]
        
        # Client Basic Info
        f.write("CLIENT INFORMATION\n")
        f.write("-" * 100 + "\n")
        f.write(f"Client ID: {manager.client_id}\n")
        f.write(f"Name: {manager.client_name}\n")
        f.write(f"Age: {manager.age} years\n")
        f.write(f"Risk Appetite: {manager.risk_appetite}\n")
        f.write(f"Segment: {manager.segment} - {manager.subsegment}\n")
        f.write(f"Relationship Tenure: {manager.relationship_tenure_years:.1f} years\n")
        f.write(f"KYC Expiry: {manager.kyc_expiry_date or 'N/A'}\n")
        f.write("\n")
        
        # Financial Overview
        f.write("FINANCIAL METRICS\n")
        f.write("-" * 100 + "\n")
        f.write(f"Annual Income: AED {manager.annual_income_aed:,.2f}\n")
        f.write(f"AUM: AED {manager.aum_aed:,.2f}\n")
        f.write(f"CASA Balance: AED {manager.casa_balance_aed:,.2f}\n")
        f.write("\n")
        
        # RM Info
        f.write("RELATIONSHIP MANAGER\n")
        f.write("-" * 100 + "\n")
        f.write(f"RM ID: {manager.rm_id or 'N/A'}\n")
        f.write(f"RM Name: {manager.rm_name or 'N/A'}\n")
        f.write("\n")
        
        # AECB Credit Bureau Status
        f.write("AECB CREDIT BUREAU STATUS\n")
        f.write("-" * 100 + "\n")
        f.write(f"AECB Alerts Count: {manager.aecb_alerts_count}\n")
        f.write(f"AECB Summary: {manager.aecb_summary or 'No data available'}\n")
        f.write("\n")
        
        # Executive Summary
        f.write("EXECUTIVE SUMMARY\n")
        f.write("-" * 100 + "\n")
        f.write(f"{manager.executive_summary}\n\n")
        
        # Immediate Actions
        if manager.immediate_actions:
            f.write("IMMEDIATE ACTION ITEMS\n")
            f.write("-" * 100 + "\n")
            for i, action in enumerate(manager.immediate_actions, 1):
                f.write(f"{i}. {action}\n")
            f.write("\n")
        
        # Downstream Summary
        f.write("DOWNSTREAM AGENT SUMMARY\n")
        f.write("-" * 100 + "\n")
        f.write(f"{manager.downstream_summary}\n\n")
        
        # SECTION 2: Risk & Compliance
        f.write("\n" + "#"*100 + "\n")
        f.write(f"# SECTION 2: RISK & COMPLIANCE ASSESSMENT\n")
        f.write("#"*100 + "\n\n")
        
        risk = agent_outputs["risk"]
        f.write(f"Risk Appetite: {risk.risk_appetite}\n")
        f.write(f"Risk Level: {risk.risk_level}/6\n")
        f.write(f"Risk Segment: {risk.risk_segment}\n\n")
        f.write(f"Investment Guidelines:\n{risk.investment_guidelines}\n\n")
        f.write(f"Risk Agent Recommendations:\n{risk.Agent_Recommends}\n\n")
        
        # SECTION 3: Asset Allocation
        f.write("\n" + "#"*100 + "\n")
        f.write(f"# SECTION 3: ASSET ALLOCATION ANALYSIS\n")
        f.write("#"*100 + "\n\n")
        
        asset_alloc = agent_outputs["asset_allocation"]
        f.write(f"Risk Appetite: {asset_alloc.risk_appetite}\n")
        f.write(f"Current Allocation: {asset_alloc.current_allocation}\n")
        f.write(f"Target Allocation: {asset_alloc.target_allocation}\n")
        f.write(f"Allocation Gaps: {asset_alloc.allocation_gaps}\n")
        f.write(f"Rebalancing Amount: AED {asset_alloc.total_rebalancing_amount_aed:,.2f}\n\n")
        f.write(f"Asset Allocation Recommendations:\n{asset_alloc.Agent_Recommends}\n\n")
        
        # SECTION 4: Market Intelligence
        f.write("\n" + "#"*100 + "\n")
        f.write(f"# SECTION 4: MARKET INTELLIGENCE\n")
        f.write("#"*100 + "\n\n")
        
        market = agent_outputs["market_intelligence"]
        f.write(f"Market Overview:\n{market.market_overview}\n\n")
        f.write(f"Investment Themes:\n")
        for theme in market.investment_themes:
            f.write(f"  • {theme}\n")
        f.write(f"\nMarket Recommendations:\n{market.Agent_Recommends}\n\n")
        
        # SECTION 5: Investment Agent
        f.write("\n" + "#"*100 + "\n")
        f.write(f"# SECTION 5: INVESTMENT STRATEGY\n")
        f.write("#"*100 + "\n\n")
        
        investment = agent_outputs["investment"]
        if investment.product_recommendations:
            f.write("Recommended Investment Products:\n")
            for i, product in enumerate(investment.product_recommendations, 1):
                f.write(f"{i}. {product.product_name}\n")
                f.write(f"   Justification: {product.justification}\n\n")
        f.write(f"Investment Agent Recommendations:\n{investment.Agent_Recommends}\n\n")
        
        # SECTION 6: Loan Agent
        f.write("\n" + "#"*100 + "\n")
        f.write(f"# SECTION 6: CREDIT & LOAN STRATEGY\n")
        f.write("#"*100 + "\n\n")
        
        loan = agent_outputs["loan"]
        f.write(f"Annual Income: AED {loan.annual_income_aed:,.2f}\n")
        f.write(f"Total Outstanding: AED {loan.total_outstanding_aed:,.2f}\n")
        f.write(f"Debt-to-Income Ratio: {loan.debt_to_income_ratio:.2%}\n")
        f.write(f"Lending Capacity: AED {loan.estimated_lending_capacity_aed:,.2f}\n\n")
        f.write(f"AECB Alerts Count: {loan.aecb_alerts_count}\n")
        f.write(f"AECB Summary: {loan.aecb_summary or 'No data available'}\n\n")
        if loan.product_recommendations:
            f.write("Recommended Loan Products:\n")
            for i, product in enumerate(loan.product_recommendations, 1):
                f.write(f"{i}. {product.product_name}\n")
                f.write(f"   Justification: {product.justification}\n\n")
        f.write(f"Loan Agent Recommendations:\n{loan.Agent_Recommends}\n\n")
        
        # SECTION 7: Banking/CASA Agent
        f.write("\n" + "#"*100 + "\n")
        f.write(f"# SECTION 7: BANKING & CASA STRATEGY\n")
        f.write("#"*100 + "\n\n")
        
        banking = agent_outputs["banking"]
        f.write(f"Total CASA Balance: AED {banking.total_casa_balance_aed:,.2f}\n\n")
        if banking.product_recommendations:
            f.write("Recommended Banking Products:\n")
            for i, product in enumerate(banking.product_recommendations, 1):
                f.write(f"{i}. {product.product_name}\n")
                f.write(f"   Justification: {product.justification}\n\n")
        f.write(f"Banking Agent Recommendations:\n{banking.Agent_Recommends}\n\n")
        
        # SECTION 8: Bancassurance Agent
        f.write("\n" + "#"*100 + "\n")
        f.write(f"# SECTION 8: BANCASSURANCE & PROTECTION STRATEGY\n")
        f.write("#"*100 + "\n\n")
        
        bancassurance = agent_outputs["bancassurance"]
        if bancassurance.existing_coverage_summary:
            f.write(f"Existing Coverage: {bancassurance.existing_coverage_summary}\n\n")
        if bancassurance.age:
            f.write(f"Client Age: {bancassurance.age} years\n")
        if bancassurance.days_to_birthday is not None:
            f.write(f"Days to Birthday: {bancassurance.days_to_birthday}\n")
        if bancassurance.lifecycle_stage:
            f.write(f"Lifecycle Stage: {bancassurance.lifecycle_stage}\n\n")
        if bancassurance.product_recommendations:
            f.write("Recommended Insurance Products:\n")
            for i, product in enumerate(bancassurance.product_recommendations, 1):
                f.write(f"{i}. {product.product_name}\n")
                f.write(f"   Justification: {product.justification}\n\n")
        f.write(f"Bancassurance Agent Recommendations:\n{bancassurance.Agent_Recommends}\n\n")
        
        # SECTION 9: RM Strategy Agent
        f.write("\n" + "#"*100 + "\n")
        f.write(f"# SECTION 9: RM STRATEGY & ACTION PLAN\n")
        f.write("#"*100 + "\n\n")
        
        rm_strategy = agent_outputs["rm_strategy"]
        
        f.write("EXECUTIVE SUMMARY FOR RM\n")
        f.write("-" * 100 + "\n")
        f.write(f"{rm_strategy.executive_summary}\n\n")
        
        f.write("CLIENT QUICK FACTS\n")
        f.write("-" * 100 + "\n")
        f.write(f"Client: {rm_strategy.client_name or rm_strategy.client_id}\n")
        f.write(f"Segment: {rm_strategy.client_segment}\n")
        f.write(f"Tenure: {rm_strategy.relationship_tenure:.1f} years\n")
        f.write(f"AUM: AED {rm_strategy.current_aum_aed:,.2f}\n")
        f.write(f"Risk Profile: {rm_strategy.risk_profile}\n")
        f.write(f"AECB Alerts: {rm_strategy.aecb_alerts_count} ({rm_strategy.aecb_status or 'No data'})\n\n")
        
        f.write("PRIORITY ACTION ITEMS\n")
        f.write("-" * 100 + "\n")
        for action in rm_strategy.priority_actions:
            if isinstance(action, dict):
                f.write(f"\n{action.get('action_number', '')}. [{action.get('priority', '')}]\n")
                f.write(f"   {action.get('action_description', '')}\n")
            else:
                f.write(f"• {action}\n")
        f.write("\n")
        
        f.write("DATA-DRIVEN TALKING POINTS\n")
        f.write("-" * 100 + "\n")
        for point in rm_strategy.talking_points:
            if isinstance(point, dict):
                f.write(f"\n{point.get('talking_point_number', '')}. {point.get('talking_point_text', '')}\n")
            else:
                f.write(f"• {point}\n")
        f.write("\n")
        
        f.write("CLIENT ENGAGEMENT QUESTIONS\n")
        f.write("-" * 100 + "\n")
        for question in rm_strategy.engagement_questions:
            if isinstance(question, dict):
                f.write(f"\n{question.get('question_number', '')}. {question.get('question_text', '')}\n")
            else:
                f.write(f"• {question}\n")
        f.write("\n")
        
        f.write("PRODUCT RECOMMENDATION STRATEGIES\n")
        f.write("-" * 100 + "\n")
        for strategy in rm_strategy.product_strategies:
            if isinstance(strategy, dict):
                f.write(f"\n{strategy.get('product_category', '')}\n")
                products = strategy.get('recommended_products', [])
                if products:
                    for product in products:
                        f.write(f"  • {product}\n")
            else:
                f.write(f"• {strategy}\n")
        f.write("\n")
        
        # Footer
        f.write("\n" + "="*100 + "\n")
        f.write("END OF REPORT\n")
        f.write("="*100 + "\n")
    
    print(f"✅ Readable report created: {report_file}")
    return report_file


def create_executive_summary(agent_outputs, output_folder):
    """Create a one-page executive summary"""
    
    summary_file = Path(output_folder) / "EXECUTIVE_SUMMARY.txt"
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("ELITEX V8 - EXECUTIVE SUMMARY\n")
        f.write("="*80 + "\n\n")
        
        manager = agent_outputs["manager"]
        
        f.write(f"Client: {manager.client_name} ({manager.client_id})\n")
        f.write(f"Segment: {manager.segment} - {manager.subsegment}\n")
        f.write(f"AUM: AED {manager.aum_aed:,.2f}\n")
        f.write(f"Risk: {manager.risk_appetite}\n\n")
        
        f.write("EXECUTIVE SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"{manager.executive_summary}\n\n")
        
        if manager.immediate_actions:
            f.write("IMMEDIATE ACTIONS REQUIRED\n")
            f.write("-" * 80 + "\n")
            for action in manager.immediate_actions[:3]:  # Top 3 only
                f.write(f"• {action}\n")
            f.write("\n")
        
        rm_strategy = agent_outputs["rm_strategy"]
        f.write("RM STRATEGY SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"{rm_strategy.executive_summary}\n\n")
        
        f.write("="*80 + "\n")
    
    print(f"✅ Executive summary created: {summary_file}")
    return summary_file

