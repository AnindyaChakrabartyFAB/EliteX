"""
EliteX V6 - Pydantic Data Models for Structured Agent Input/Output

This module defines comprehensive Pydantic models for all agents in the EliteX V5 system.
Each model includes detailed field descriptions and validation rules.

Models are organized by agent:
1. Manager Agent
2. Risk & Compliance Agent
3. Investment Agent
4. Loan Agent
5. Banking/CASA Agent
6. Bancassurance Agent
7. RM Strategy Agent
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from decimal import Decimal
import re


def parse_decimal_field(v):
    """
    Universal decimal parser that handles:
    - Plain decimals: "123.45"
    - Thousand separators: "1,234.56"
    - Percentages and mixed text: "40% of allocation", "approx 1,234.56 USD equivalent"
    - Currency suffixes: "1,234.56 USD" or "1,234.56 AED"
    - Thinking text with calculations: "1,496,129.00 + 1,273,962.25 = 2,770,091.25" -> extracts 2,770,091.25
    - Returns None for non-numeric values like "N/A"
    """
    if v is None:
        return None
    if isinstance(v, (int, float, Decimal)):
        return Decimal(str(v))
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        
        # Special case: if string contains "=" sign (likely a calculation), extract the number after the last "="
        if '=' in s:
            parts = s.split('=')
            # Get the last part after the last equals sign
            last_part = parts[-1].strip()
            # Extract number from this part
            token_match = re.search(r'[-+]?\d[\d,]*(?:\.\d+)?', last_part)
            if token_match:
                numeric_token = token_match.group(0).replace(',', '')
                try:
                    return Decimal(numeric_token)
                except Exception:
                    pass
        
        # First, try to extract the first numeric token anywhere in the string
        # Supports optional sign, comma grouping, and decimal portion
        token_match = re.search(r'[-+]?\d[\d,]*(?:\.\d+)?', s)
        if token_match:
            numeric_token = token_match.group(0).replace(',', '')
            try:
                return Decimal(numeric_token)
            except Exception:
                pass
        # Fallback: remove common suffixes/symbols then parse
        s = re.sub(r'\s*(USD|AED|EUR|GBP|JPY|CHF|CAD|AUD)\s*$', '', s, flags=re.IGNORECASE)
        s = s.replace('%', '')
        s = s.replace(',', '')
        try:
            return Decimal(s.strip())
        except Exception:
            return None
    return v


def parse_client_fit_score(v):
    """Map qualitative scores to numeric, else parse as decimal."""
    if v is None:
        return None
    if isinstance(v, (int, float, Decimal)):
        return Decimal(str(v))
    if isinstance(v, str):
        s = v.strip().lower()
        mappings = {
            'very high': Decimal('95'),
            'high': Decimal('90'),
            'medium-high': Decimal('80'),
            'medium': Decimal('70'),
            'low': Decimal('50'),
        }
        if s in mappings:
            return mappings[s]
        # Try to parse any numeric token
        return parse_decimal_field(s)
    return v


# =============================================================================
# COMMON/SHARED MODELS
# =============================================================================

class ClientBasicInfo(BaseModel):
    """Complete client identification and profile information from core.client_context"""
    
    # Primary Identification
    client_id: str = Field(..., description="Unique client identifier")
    first_name: str = Field(..., description="Client's first name")
    last_name: str = Field(..., description="Client's last name")
    full_name: str = Field(..., description="Client's full name (first + last)")
    
    # Demographics
    age: float = Field(..., description="Client's age in years (decimal for precision)")
    dob: Optional[date] = Field(None, description="Client's date of birth")
    gender: Optional[str] = Field(None, description="Client's gender")
    customer_personal_nationality: Optional[str] = Field(None, description="Client's nationality")
    customer_personal_residence: Optional[str] = Field(None, description="Client's country of residence")
    emirate: Optional[str] = Field(None, description="Emirate of residence in UAE")
    
    # Professional Information
    employer: Optional[str] = Field(None, description="Client's employer name")
    occupation: Optional[str] = Field(None, description="Client's occupation/job title")
    occupation_sector: Optional[str] = Field(None, description="Client's occupation sector/industry")
    education: Optional[str] = Field(None, description="Client's education level")
    income: Optional[Decimal] = Field(default=None, description="Client's annual income in AED (null if not available)")
    
    @field_validator('income', mode='before')
    @classmethod
    def parse_income_field(cls, v):
        """Parse income field, return None for non-numeric values like 'not on record'"""
        if v is None or (isinstance(v, str) and v.strip().lower() in ['not on record', 'n/a', 'unknown', '']):
            return None
        return parse_decimal_field(v)
    
    # Personal Status
    family: Optional[str] = Field(None, description="Client's family status (e.g., married, single, children)")
    
    # Banking Segment
    customer_profile_banking_segment: str = Field(..., description="Primary banking segment (e.g., WEALTH MANAGEMENT, PRIORITY BANKING)")
    customer_profile_subsegment: str = Field(..., description="Banking subsegment (e.g., Elite Standard, Private Banking)")
    
    # Contact Information
    
    communication_type_1: Optional[str] = Field(None, description="Type of primary communication (e.g., Mobile, Office)")
    
    
    # Risk Profile
    risk_appetite: str = Field(..., description="Risk appetite classification (R1-R5)")
    risk_level: int = Field(..., description="Numeric risk level (1-5)")
    risk_segment: str = Field(..., description="Risk segment category (e.g., Conservative, Balanced, Growth)")
    
    # Relationship Dates
    open_date: Optional[date] = Field(None, description="Account opening date")
    tenure: float = Field(..., description="Banking relationship tenure in years")
    kyc_date: Optional[date] = Field(None, description="Last KYC completion date")
    kyc_expiry_date: Optional[date] = Field(None, description="KYC expiry date")
    
    # Additional Attributes
    professional_investor_flag: Optional[str] = Field(None, description="Professional/Sophisticated investor flag (Y/N)")
    aecb_rating: Optional[str] = Field(None, description="AECB credit rating if available")
    client_picture: Optional[str] = Field(None, description="Client profile picture reference")
    last_update: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Calculated Fields (derived from raw data)
    calculated_risk_capacity: str = Field(..., description="Calculated risk capacity (low, medium, high, very_high) based on income and segment")
    calculated_life_stage: str = Field(..., description="Calculated life stage (early_career, career_building, mid_career, pre_retirement, retirement)")
    calculated_sophistication: str = Field(..., description="Calculated sophistication level (basic, intermediate, sophisticated)")
    calculated_client_tier: str = Field(..., description="Calculated client tier (mass_market, affluent, high_net_worth, ultra_high_net_worth)")
    calculated_relationship_strength: str = Field(..., description="Calculated relationship strength (new, moderate, strong, very_strong) based on tenure")
    
    # Data Source
    data_source: str = Field(default="core.client_context@fab_elite", description="Source table for this data")


# Note: RiskProfile and SegmentInfo are now included in ClientBasicInfo for completeness
# These lightweight models are kept for backward compatibility and specific use cases

class RiskProfile(BaseModel):
    """Lightweight risk profile summary (full data in ClientBasicInfo)"""
    risk_appetite: str = Field(..., description="Risk appetite classification (R1-R5)")
    risk_level: int = Field(..., description="Numeric risk level (1-5)")
    risk_segment: str = Field(..., description="Risk segment category (e.g., Conservative, Balanced, Growth)")
    sophistication_level: str = Field(..., description="Investor sophistication level (e.g., Sophisticated, Professional, Retail)")


class SegmentInfo(BaseModel):
    """Lightweight segment summary (full data in ClientBasicInfo)"""
    banking_segment: str = Field(..., description="Primary banking segment (e.g., Wealth Management, Priority Banking)")
    subsegment: str = Field(..., description="Subsegment within primary segment (e.g., Elite Standard, Premier)")


class RMInfo(BaseModel):
    """Relationship Manager assignment information"""
    rm_id: Optional[str] = Field(None, description="Relationship Manager unique identifier")
    rm_name: Optional[str] = Field(None, description="Relationship Manager full name")
    relation_type: Optional[str] = Field(None, description="Type of RM relationship")


class FinancialMetrics(BaseModel):
    """Core financial metrics for the client"""
    annual_income_aed: Optional[Decimal] = Field(default=None, description="Client's annual income in AED (null if not available)")
    aum_aed: Decimal = Field(default=0, description="Total Assets Under Management in AED (from investment holdings)")
    casa_balance_aed: Decimal = Field(default=0, description="Current Account and Savings Account balance in AED")
    total_liabilities_aed: Decimal = Field(default=0, description="Total outstanding liabilities in AED (default 0 if unknown)")
    
    @field_validator('annual_income_aed', mode='before')
    @classmethod
    def parse_annual_income_field(cls, v):
        """Parse annual_income_aed field, return None for non-numeric values like 'not on record'"""
        if v is None or (isinstance(v, str) and v.strip().lower() in ['not on record', 'n/a', 'unknown', '']):
            return None
        return parse_decimal_field(v)
    
    @field_validator('aum_aed', 'casa_balance_aed', 'total_liabilities_aed', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        """Parse decimal fields with thousand separators, currency codes, etc."""
        return parse_decimal_field(v)


class DataSource(BaseModel):
    """Reference to data source and timestamp"""
    source_table: str = Field(..., description="Database table or tool name that provided this data")
    source_field: Optional[str] = Field(None, description="Specific field or column name")
    query_timestamp: datetime = Field(default_factory=datetime.now, description="When this data was retrieved")


# =============================================================================
# PRODUCT RECOMMENDATION MODELS (COMMON STRUCTURE)
# =============================================================================

class JustificationStep(BaseModel):
    """Single step in a 5-step product justification"""
    step_number: int = Field(..., ge=1, le=5, description="Step number (1-5)")
    step_title: str = Field(..., description="Title of the justification step (e.g., 'Client Profile Alignment')")
    analysis: str = Field(..., description="Detailed analysis and reasoning for this step")
    supporting_data: List[str] = Field(..., description="Specific data points supporting this step's analysis")


class ProductRecommendation(BaseModel):
    """Base structure for product recommendations across all agents"""
    product_code: Optional[str] = Field(None, description="Product identifier code")
    product_name: str = Field(..., description="Product name")
    product_category: str = Field(..., description="Product category (e.g., Investment-Linked, Term Loan, Fixed Deposit)")
    priority: Literal["HIGH", "MEDIUM", "LOW"] = Field(..., description="Recommendation priority level")
    product_eligibility: str = Field(None, description="Detailed Description of Product eligibility criteria and why this client is eligible")
    
    # 5-Step Chain of Thought Justification
    justification_steps: List[JustificationStep] = Field(
        ..., 
        min_items=5, 
        max_items=5,
        description="Five-step justification with supporting data for each step"
    )
    
    # Recommendation details

    recommended_amount_aed: Optional[Decimal] = Field(None, description="Recommended investment/loan amount in AED")
    percentage_of_portfolio: Optional[Decimal] = Field(None, description="Percentage of total portfolio/allocation")
    
    # Supporting data summary
    key_data_points: List[str] = Field(..., description="Key data points supporting this recommendation")
    client_fit_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Client fit score (0-100)")
    
    # Talking points
    rm_talking_point: str = Field(..., description="Specific talking point for RM to use with client")
    
    @field_validator('recommended_amount_aed', 'percentage_of_portfolio', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        """Parse decimal fields with thousand separators, currency codes, etc."""
        if isinstance(v, str) and 'percent of' in v.lower():
            # Extract first number from strings like "50 percent of..."
            match = re.search(r'(\d+(?:\.\d+)?)', v)
            if match:
                return Decimal(match.group(1))
            return None
        return parse_decimal_field(v)

    @field_validator('client_fit_score', mode='before')
    @classmethod
    def parse_client_fit_score_field(cls, v):
        return parse_client_fit_score(v)


# =============================================================================
# MANAGER AGENT MODELS
# =============================================================================

class ImmediateActionItem(BaseModel):
    """Time-sensitive action item requiring RM attention"""
    action_type: Literal["KYC_EXPIRY", "PRODUCT_MATURITY", "SERVICE_REQUEST", "AECB_ALERT", "COMPLIANCE", "OTHER"] = Field(
        ..., description="Type of action item"
    )
    description: str = Field(..., description="Detailed description of the action required")
    due_date: Optional[date] = Field(None, description="Due date for this action")
    days_until_due: Optional[int] = Field(None, description="Number of days until due date")
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(..., description="Priority level")
    data_source: str = Field(..., description="Tool or table that identified this action")


class AECBAlert(BaseModel):
    """Credit bureau alert detail"""
    alert_type: str = Field(..., description="Type of AECB alert (e.g., Credit Card Enquiry, Loan Default)")
    alert_date: date = Field(..., description="Date of the alert")
    description: str = Field(..., description="Business-friendly description of the alert")
    amount_aed: Optional[Decimal] = Field(None, description="Associated amount in AED if applicable")
    opportunity_implication: str = Field(..., description="What this alert means for product opportunities")


class OpportunityCategory(BaseModel):
    """Growth opportunity identified for the client"""
    opportunity_name: str = Field(..., description="Name of the opportunity category (e.g., Investment Growth)")
    estimated_potential_aed: Optional[Decimal] = Field(..., description="Estimated potential value in AED (nullable if not available)")
    supporting_data: List[str] = Field(..., description="Specific data points supporting this opportunity")
    client_readiness_indicators: List[str] = Field(..., description="Behavioral patterns or signals indicating readiness")
    relevant_context: List[str] = Field(..., description="Risk profile, sophistication, or other relevant context")
    data_supporting_opportunity: str = Field(..., description="Exact data supporting this opportunity")
    
    @field_validator('estimated_potential_aed', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        """Parse decimal fields with thousand separators, currency codes, etc."""
        return parse_decimal_field(v)


class BehavioralInsight(BaseModel):
    """Client behavioral pattern from transaction analysis"""
    insight_type: Literal["SPENDING", "INVESTMENT", "CREDIT", "DEPOSIT", "ENGAGEMENT"] = Field(
        ..., description="Type of behavioral insight"
    )
    period_months: int = Field(..., description="Analysis period in months")
    transaction_count: int = Field(..., description="Number of transactions in period")
    total_amount_aed: Decimal = Field(..., description="Total transaction amount in AED")
    patterns_identified: List[str] = Field(..., description="Specific patterns identified")
    top_products_interest_indicators: List[str] = Field(..., description="Top products client may be interested in based on behavior")
    justification_steps: List[str] = Field(..., description="Justification steps for this opportunity")
    
    @field_validator('total_amount_aed', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        """Parse decimal fields with thousand separators, currency codes, etc."""
        return parse_decimal_field(v)


class PortfolioAllocation(BaseModel):
    """Investment portfolio asset allocation"""
    has_investments: bool = Field(..., description="Whether client has any investment holdings")
    aum_aed: Decimal = Field(default=0, description="Total AUM in AED")
    equity_percentage: Decimal = Field(default=0, ge=0, le=100, description="Equity allocation percentage (default 0 if no investments)")
    fixed_income_percentage: Decimal = Field(default=0, ge=0, le=100, description="Fixed income allocation percentage (default 0 if no investments)")
    money_market_percentage: Decimal = Field(default=0, ge=0, le=100, description="Money Market allocation percentage (default 0 if no investments)")
    alternatives_percentage: Decimal = Field(default=0, ge=0, le=100, description="Alternative investments allocation percentage (default 0 if no investments)")
    
    @field_validator('aum_aed', 'equity_percentage', 'fixed_income_percentage', 'money_market_percentage', 'alternatives_percentage', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        """Parse decimal fields with thousand separators, currency codes, etc."""
        return parse_decimal_field(v)


class DepositTrend(BaseModel):
    """CASA deposit trend analysis"""
    current_month_aed: Decimal = Field(..., description="Current month deposit balance in AED")
    six_month_average_aed: Decimal = Field(..., description="Six-month average deposit balance in AED")
    trend_percentage: Decimal = Field(..., description="Percentage change (positive = increasing, negative = decreasing)")
    trend_direction: Literal["INCREASING", "DECREASING", "STABLE"] = Field(..., description="Trend direction")
    implication: str = Field(..., description="What this trend suggests about client needs")
    
    @field_validator('current_month_aed', 'six_month_average_aed', 'trend_percentage', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        """Parse decimal fields with thousand separators, currency codes, etc."""
        return parse_decimal_field(v)


class EngagementProfile(BaseModel):
    """Client engagement and communication profile"""
    total_interactions: int = Field(..., description="Total number of client interactions")
    key_interactions: List[str] = Field(..., description="Key interactions with client")
    analysis_period_months: int = Field(..., description="Period analyzed for engagement")
    preferred_channel: Optional[str] = Field(None, description="Preferred communication channel")
    response_pattern: Optional[str] = Field(None, description="How client typically responds to communication")


class ManagerAgentOutput(BaseModel):
    """Simplified Manager Agent output"""
    
    # Essential client identification
    client_id: str = Field(..., description="Client identifier")
    client_name: str = Field(..., description="Client full name")
    age: float = Field(..., description="Client age")
    risk_appetite: str = Field(..., description="Risk appetite (R1-R6)")
    segment: str = Field(..., description="Banking segment")
    subsegment: str = Field(default="", description="Banking subsegment")
    
    # Essential RM info
    rm_id: Optional[str] = Field(None, description="RM ID")
    rm_name: Optional[str] = Field(None, description="RM name")
    
    # Essential financial metrics
    annual_income_aed: Decimal = Field(..., description="Annual income in AED")
    aum_aed: Decimal = Field(..., description="AUM in AED")
    casa_balance_aed: Decimal = Field(..., description="CASA balance in AED")
    relationship_tenure_years: float = Field(..., description="Tenure in years")
    
    # Critical compliance
    kyc_expiry_date: Optional[date] = Field(None, description="KYC expiry date")
    
    # Immediate actions (essential)
    immediate_actions: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Time-sensitive actions"
    )
    
    # Downstream summary (essential for other agents)
    downstream_summary: str = Field(..., description="Summary for other agents")
    
    # Executive summary
    executive_summary: str = Field(default="", description="Executive summary")
    
    @field_validator('annual_income_aed', 'aum_aed', 'casa_balance_aed', mode='before')
    @classmethod
    def _parse_decimal(cls, v):
        return parse_decimal_field(v)


# =============================================================================
# ASSET ALLOCATION AGENT MODELS
# =============================================================================

class AssetAllocationRecommendation(BaseModel):
    """Asset allocation recommendation with specific percentages and rationale"""
    asset_class: str = Field(..., description="Asset class (Equity, Fixed Income, Money Market, Alternatives)")
    current_allocation_percentage: Decimal = Field(..., ge=0, le=100, description="Current allocation percentage")
    recommended_allocation_percentage: Decimal = Field(..., ge=0, le=100, description="Recommended allocation percentage")
    allocation_change_percentage: Decimal = Field(..., description="Change in allocation percentage (positive = increase, negative = decrease)")
    rationale: str = Field(..., description="Detailed rationale for this allocation recommendation")
    risk_impact: str = Field(..., description="Impact on overall portfolio risk")
    expected_return_impact: str = Field(..., description="Expected impact on portfolio returns")
    implementation_priority: Literal["HIGH", "MEDIUM", "LOW"] = Field(..., description="Priority for implementing this change")
    
    @field_validator('current_allocation_percentage', 'recommended_allocation_percentage', 
                     'allocation_change_percentage', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        return parse_decimal_field(v)


class RebalancingAction(BaseModel):
    """Specific rebalancing action to implement allocation changes"""
    action_type: Literal["BUY", "SELL", "HOLD"] = Field(..., description="Type of rebalancing action")
    asset_class: str = Field(..., description="Asset class for this action")
    amount_aed: Decimal = Field(..., description="Amount in AED to buy/sell")
    percentage_of_portfolio: Decimal = Field(..., ge=0, le=100, description="Percentage of total portfolio")
    target_securities: List[str] = Field(..., description="Specific securities or funds to target")
    execution_timeline: str = Field(..., description="Recommended timeline for execution")
    cost_benefit_analysis: str = Field(..., description="Cost-benefit analysis of this action")
    
    @field_validator('amount_aed', 'percentage_of_portfolio', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        return parse_decimal_field(v)


class PortfolioRiskMetrics(BaseModel):
    """Portfolio risk metrics and analysis"""
    current_risk_level: str = Field(..., description="Current portfolio risk level")
    target_risk_level: str = Field(..., description="Target risk level based on client profile")
    risk_adjustment_needed: str = Field(..., description="Risk adjustment needed (increase/decrease/maintain)")
    concentration_risk_score: Optional[Decimal | str] = Field(None, description="Concentration risk score (0-100) or 'N/A'")
    diversification_score: Optional[Decimal | str] = Field(None, description="Diversification score (0-100) or 'N/A'")
    volatility_estimate: Optional[Decimal | str] = Field(None, description="Estimated portfolio volatility or 'N/A'")
    risk_mitigation_recommendations: List[str] = Field(..., description="Specific risk mitigation recommendations")
    
    @field_validator('concentration_risk_score', 'diversification_score', 'volatility_estimate', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        return parse_decimal_field(v)


class AssetAllocationAgentOutput(BaseModel):
    """Complete structured output from Asset Allocation Agent"""
    
    client_id: str = Field(..., description="Client identifier")
    
    # Current Portfolio Analysis
    current_total_aum_aed: Decimal = Field(..., description="Current total AUM in AED")
    # Allow rich objects per asset class (e.g., { percentage, amount_aed })
    current_asset_allocation: Dict[str, Any] = Field(..., description="Current allocation by asset class (percentages and/or amounts)")
    
    # Allocation Recommendations (allow rich objects with target percentages/amounts)
    recommended_asset_allocation: Dict[str, Any] = Field(..., description="Recommended allocation by asset class (target percentages/amounts)")
    allocation_recommendations: List[AssetAllocationRecommendation] = Field(
        ..., description="Detailed allocation recommendations with rationale"
    )
    
    # Rebalancing Actions
    rebalancing_actions: List[RebalancingAction] = Field(
        ..., description="Specific rebalancing actions to implement"
    )
    total_rebalancing_amount_aed: Decimal = Field(..., description="Total amount involved in rebalancing")
    
    # Risk Analysis
    portfolio_risk_metrics: PortfolioRiskMetrics = Field(..., description="Portfolio risk analysis and metrics")
    
    # Allow these fields at top level for backward compatibility (agent sometimes outputs them here)
    risk_adjustment_needed: Optional[str] = Field(None, description="Risk adjustment needed (if not in portfolio_risk_metrics)")
    concentration_risk_score: Optional[Decimal] = Field(None, description="Concentration risk score (if not in portfolio_risk_metrics)")
    diversification_score: Optional[Decimal] = Field(None, description="Diversification score (if not in portfolio_risk_metrics)")
    volatility_estimate: Optional[Decimal] = Field(None, description="Volatility estimate (if not in portfolio_risk_metrics)")
    risk_mitigation_recommendations: Optional[List[str]] = Field(None, description="Risk mitigation recommendations (if not in portfolio_risk_metrics)")
    
    # Implementation Strategy
    implementation_priority: str = Field(..., description="Overall implementation priority")
    implementation_timeline: str = Field(..., description="Recommended implementation timeline")
    expected_benefits: List[str] = Field(..., description="Expected benefits of rebalancing")
    potential_risks: List[str] = Field(..., description="Potential risks of rebalancing")
    
    # Context for Investment Agent
    investment_agent_context: str = Field(..., description="Context to pass to Investment Agent for product recommendations")
    
    # Data Sources
    data_sources_used: List[str] = Field(..., description="List of all tools/tables used for allocation analysis")
    
    @field_validator('current_total_aum_aed', 'total_rebalancing_amount_aed', 'concentration_risk_score', 'diversification_score', 'volatility_estimate', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        return parse_decimal_field(v)

    # Executive narrative for senior management
    Agent_Recommends: str = Field(
        default="",
        description=(
            "Executive narrative: actionable, professional summary referencing actual data points, "
            "combining inputs and recommendations for senior management."
        ),
    )


# =============================================================================
# RISK & COMPLIANCE AGENT MODELS
# =============================================================================

class RiskAssessment(BaseModel):
    """Risk assessment details"""
    risk_appetite: str = Field(..., description="Risk appetite classification (R1-R5)")
    current_portfolio_risk: str = Field(..., description="Current portfolio risk exposure assessment")
    risk_capacity: str = Field(..., description="Client's capacity to take on risk")
    active_alerts: List[str] = Field(..., description="Active AECB or compliance alerts")
    alert_count: int = Field(..., description="Number of active alerts")


class ProductRecommendationGuideline(BaseModel):
    """Guidelines for product recommendations based on risk profile"""
    investment_guideline: str = Field(..., description="Investment product recommendation guidelines")
    credit_guideline: str = Field(..., description="Credit product recommendation guidelines")
    liquidity_requirement: str = Field(..., description="Liquidity requirements based on risk profile")
    volatility_tolerance: str = Field(..., description="Tolerance for principal volatility")


class RiskComplianceAgentOutput(BaseModel):
    """Complete structured output from Risk & Compliance Agent"""
    
    client_id: str = Field(..., description="Client identifier")
    
    # Risk Assessment
    risk_assessment: RiskAssessment = Field(..., description="Comprehensive risk assessment")
    
    # Product Guidelines
    product_guidelines: ProductRecommendationGuideline = Field(
        ..., description="Guidelines for product recommendations aligned with risk profile"
    )
    
    # Data Sources
    data_sources_used: List[str] = Field(..., description="List of all tools/tables used for risk analysis")


# =============================================================================
# INVESTMENT AGENT MODELS
# =============================================================================

class CurrentHolding(BaseModel):
    """Current investment holding detail"""
    security_id: str = Field(..., description="Security identifier")
    security_name: str = Field(..., description="Security name")
    asset_class: str = Field(..., description="Asset class (Equity, Fixed Income, etc.)")
    market_value_aed: Decimal = Field(..., description="Current market value in AED")
    cost_basis_aed: Decimal = Field(..., description="Original cost basis in AED")
    return_since_inception: Optional[Decimal] = Field(None, description="Return percentage since inception")
    allocation_percentage: Decimal = Field(..., ge=0, le=100, description="Percentage of total portfolio")
    
    @field_validator('market_value_aed', 'cost_basis_aed', 'return_since_inception', 'allocation_percentage', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        """Parse decimal fields with thousand separators, currency codes, etc."""
        return parse_decimal_field(v)


class InvestmentProductRecommendation(ProductRecommendation):
    """Investment product recommendation with investment-specific fields"""
    
    # Investment-specific fields
    investment_objective: str = Field(..., description="Exact investment objective from product data")
    asset_class: str = Field(..., description="Asset class (Equity, Fixed Income, Alternatives)")
    sub_asset_class: Optional[str] = Field(None, description="Sub-asset class or sector")
    eligibility_reasons: List[str] = Field(..., description="Reasons for client eligibility")
    justification: JustificationStep = Field(..., description="Justification for of the recommendation using 5 step process")
    alignment_with_Investment_opportunity: str = Field(..., description="How this recommendation aligns with the Investment opportunity")
    client_fit_score: int = Field(..., description="Client fit score for this recommendation")
    key_data_points: List[str] = Field(..., description="Key data points supporting this recommendation")
    # Performance metrics
    annualized_return_3y: Optional[Decimal] = Field(None, description="3-year annualized return percentage")
    annualized_return_5y: Optional[Decimal] = Field(None, description="5-year annualized return percentage")
    morningstar_rating: Optional[int] = Field(None, ge=1, le=5, description="Morningstar rating (1-5 stars)")
    
    # Product details
    total_net_assets_aed: Optional[Decimal] = Field(None, description="Total net assets in AED")
    fund_domicile: Optional[str] = Field(None, description="Fund domicile country")
    currency: Optional[str] = Field(None, description="Fund currency")
    isin: Optional[str] = Field(None, description="ISIN identifier")
    
    @field_validator('annualized_return_3y', 'annualized_return_5y', 'total_net_assets_aed', 
                     'recommended_amount_aed', 'percentage_of_portfolio', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        """Parse decimal fields with thousand separators, currency codes, percentages, etc."""
        if isinstance(v, str) and ('percent of' in v.lower() or '% of' in v):
            # Extract first number from strings like "40% of suggested investment deployment"
            match = re.search(r'(\d+(?:\.\d+)?)\s*%', v)
            if match:
                return Decimal(match.group(1))
        return parse_decimal_field(v)


class InvestmentOpportunitySummary(BaseModel):
    """Summary of investment growth opportunities"""
    has_share_of_potential_data: bool = Field(..., description="Whether modeled share-of-potential data exists from app.upsellopportunity")
    total_opportunity_aed: Decimal = Field(..., description="Total investment opportunity in AED from share-of-potential data (0 if has_share_of_potential_data is False)")
    opportunity_breakdown: OpportunityCategory= Field(..., description="Breakdown by category - can include estimated opportunities from portfolio analysis")
    
    @field_validator('total_opportunity_aed', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        """Parse decimal fields with thousand separators, currency codes, etc."""
        return parse_decimal_field(v)
    
    @field_validator('total_opportunity_aed', mode='after')
    @classmethod
    def validate_opportunity_amount(cls, v, info):
        """Ensure total_opportunity_aed is 0 when has_share_of_potential_data is False"""
        # Get the has_share_of_potential_data value from the validation context
        if hasattr(info, 'data') and 'has_share_of_potential_data' in info.data:
            has_data = info.data['has_share_of_potential_data']
            if not has_data and v != 0:
                # If no share-of-potential data exists, total should be 0
                return Decimal('0')
        return v



class InvestmentAgentOutput(BaseModel):
    """Simplified Investment Agent output"""
    
    client_id: str = Field(..., description="Client identifier")
    RM_id: Optional[str] = Field(None, description="Relationship Manager ID")
   
    # Product Recommendations (0-3 only)
    product_recommendations: List[InvestmentProductRecommendation] = Field(
        default_factory=list,
        min_items=0,
        max_items=3,
        description="Top 2-3 investment product recommendations"
    )

    # Executive summary
    Agent_Recommends: str = Field(default="", description="2-3 sentence summary")


# =============================================================================
# LOAN AGENT MODELS
# =============================================================================

class ExistingCreditFacility(BaseModel):
    """Existing credit facility or loan"""
    facility_type: str = Field(..., description="Type of facility (Personal Loan, Mortgage, LOC, etc.)")
    facility_id: Optional[str] = Field(None, description="Facility identifier")
    outstanding_balance_aed: Decimal = Field(..., description="Outstanding balance in AED")
    interest_rate: Optional[Decimal] = Field(None, description="Interest rate percentage")
    monthly_payment_aed: Optional[Decimal] = Field(None, description="Monthly payment amount in AED")
    maturity_date: Optional[date] = Field(None, description="Loan maturity date")
    status: str = Field(..., description="Facility status (Active, Overdue, etc.)")
    
    @field_validator('outstanding_balance_aed', 'interest_rate', 'monthly_payment_aed', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        """Parse decimal fields with thousand separators, currency codes, etc."""
        return parse_decimal_field(v)


class AECBCreditAlert(BaseModel):
    """AECB credit bureau alert detail"""
    alert_type: Literal["ENQUIRY", "NEW_FACILITY", "OVERDUE", "DEFAULT", "CLOSURE"] = Field(
        ..., description="Type of AECB alert"
    )
    alert_date: date = Field(..., description="Date of alert")
    product_type: Optional[str] = Field(None, description="Product type related to alert")
    amount_aed: Optional[Decimal] = Field(None, description="Amount associated with alert")
    overdue_amount_aed: Optional[Decimal] = Field(None, description="Overdue amount if applicable")
    credit_limit_queried: Optional[Decimal] = Field(None, description="Credit limit queried for enquiries")
    implication: str = Field(..., description="Business implication of this alert")

    @field_validator('amount_aed', 'overdue_amount_aed', 'credit_limit_queried', mode='before')
    @classmethod
    def _parse_decimal(cls, v):
        return parse_decimal_field(v)


class LoanProductRecommendation(ProductRecommendation):
    """Loan product recommendation with loan-specific fields"""
    
    # Loan-specific fields
    loan_type: Literal["PERSONAL_LOAN", "LINE_OF_CREDIT", "MORTGAGE", "AUTO_LOAN", "CREDIT_CARD", "OTHER"] = Field(
        ..., description="Type of loan product"
    )
    
    # Interest and terms
    product_name: str = Field(..., description="Product name")
    product_description: str = Field(..., description="Product description")
    interest_rate_range: str = Field(..., description="Interest rate range (e.g., '5.0% - 15.0% p.a.')")
    
    # Loan details
    collateral_required: bool = Field(..., description="Whether collateral is required")
    interest_structure: Literal["FIXED", "VARIABLE", "HYBRID"] = Field(..., description="Interest rate structure")
    product_risk_rating: int = Field(..., ge=1, le=5, description="Product risk rating (1-5)")
    
    # Eligibility
    product_eligibility: str = Field(..., description="Detailed Description of Product eligibility criteria and why this client is eligible")
    eligibility_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Client eligibility score (0-100)")
    eligibility_reasons: List[str] = Field(..., description="Reasons for eligibility/recommendation")
    justification: JustificationStep = Field(..., description="Justification for of the recommendation using 5 step process")
    alignment_with_Loan_opportunity: str = Field(..., description="How this recommendation aligns with the Loan opportunity")
    client_fit_score: int = Field(..., description="Client fit score for this recommendation")
    key_data_points: List[str] = Field(..., description="Key data points supporting this recommendation")
    
    @field_validator('recommended_amount_aed', 'percentage_of_portfolio', 'eligibility_score', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        """Parse decimal fields with thousand separators, currency codes, percentages, etc."""
        if isinstance(v, str) and ('percent of' in v.lower() or '% of' in v):
            match = re.search(r'(\d+(?:\.\d+)?)\s*%', v)
            if match:
                return Decimal(match.group(1))
        return parse_decimal_field(v)


class CreditCapacityAssessment(BaseModel):
    """Client credit capacity assessment"""
    annual_income_aed: Optional[Decimal] = Field(None, description="Verified annual income in AED (None if not available)")
    current_obligations_aed: Decimal = Field(..., description="Current credit obligations in AED")
    debt_to_income_ratio: Optional[Decimal] = Field(None, description="Debt-to-income ratio percentage")
    estimated_lending_capacity_aed: Optional[Decimal] = Field(None, description="Estimated lending capacity in AED")
    capacity_utilization_percentage: Optional[Decimal] = Field(default=None, ge=0, description="Current capacity utilization percentage (can exceed 100% if over-leveraged)")
    capacity_assessment: str = Field(..., description="Narrative assessment of lending capacity")
    
    @field_validator('annual_income_aed', 'current_obligations_aed', 'debt_to_income_ratio', 
                     'estimated_lending_capacity_aed', 'capacity_utilization_percentage', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        """Parse decimal fields with thousand separators, currency codes, percentages, etc."""
        return parse_decimal_field(v)


class LoanAgentOutput(BaseModel):
    """Complete structured output from Loan Agent"""
    
    client_id: str = Field(..., description="Client identifier")
    
    # Current Credit Relationship
    existing_facilities: List[ExistingCreditFacility] = Field(..., description="Existing credit facilities")
    total_credit_exposure_aed: Decimal = Field(..., description="Total on-us credit exposure in AED")
    
    # AECB Alerts
    aecb_credit_alerts: List[AECBCreditAlert] = Field(..., description="Credit bureau alerts with implications")
    
    # Credit Capacity
    credit_capacity: CreditCapacityAssessment = Field(..., description="Credit capacity assessment")

    # Transaction Behavior
    credit_transaction_count: int = Field(..., description="Number of credit transactions")
    behavioral_insights: List[str] = Field(..., description="Credit-related behavioral insights")
    
    # Top 3 Product Recommendations
    product_recommendations: List[LoanProductRecommendation] = Field(
        ..., 
        min_items=1,
        max_items=3,
        description="Top 3 loan product recommendations with 5-step justification and eligibility"
    )
    
    
    
    # Priority Ranking
    priority_ranking_rationale: str = Field(
        ..., description="Explanation of how recommendations are prioritized"
    )
    
    # Data Sources
    data_sources_used: List[str] = Field(..., description="List of all tools/tables used for loan analysis")

    # Executive narrative for senior management
    Agent_Recommends: str = Field(
        default="",
        description=(
            "Executive narrative: actionable, professional summary referencing actual data points, "
            "combining inputs and recommendations for senior management."
        ),
    )
    
    @field_validator('total_credit_exposure_aed', mode='before')
    @classmethod
    def parse_total_credit_exposure(cls, v):
        """Parse total_credit_exposure_aed field, extracting final number from thinking text if present"""
        return parse_decimal_field(v)


# =============================================================================
# BANKING/CASA AGENT MODELS
# =============================================================================

class CASATrendAnalysis(BaseModel):
    """CASA balance trend analysis"""
    current_month_balance_aed: Decimal = Field(..., description="Current month balance")
    six_month_average_aed: Decimal = Field(..., description="Six-month average balance")
    peak_balance_aed: Decimal = Field(..., description="Peak balance in analysis period")
    trough_balance_aed: Decimal = Field(..., description="Lowest balance in analysis period")
    trend_percentage: Decimal = Field(..., description="Percentage change vs 6-month average")
    trend_direction: Literal["INCREASING", "DECREASING", "STABLE"] = Field(..., description="Overall trend")
    volatility_assessment: str = Field(..., description="Assessment of balance volatility")
    implication: str = Field(..., description="Business implication of the trend")

    @field_validator(
        'current_month_balance_aed', 'six_month_average_aed', 'peak_balance_aed',
        'trough_balance_aed', 'trend_percentage', mode='before'
    )
    @classmethod
    def _parse_decimal(cls, v):
        return parse_decimal_field(v)


class CASAAccountDetail(BaseModel):
    """CASA account detail"""
    account_type: Literal["CURRENT", "SAVINGS", "MONEY_MARKET"] = Field(..., description="Type of account")
    account_id: Optional[str] = Field(None, description="Account identifier")
    balance_aed: Decimal = Field(..., description="Current balance in AED")
    interest_rate: Optional[Decimal] = Field(None, description="Interest rate percentage if applicable")
    casa_trend_analysis: Optional[CASATrendAnalysis] = Field(None, description="Change in balance in AED last 6 months")
    key_data_points: List[str] = Field(..., description="Key data points supporting this analysis")

    @field_validator('balance_aed', 'interest_rate', mode='before')
    @classmethod
    def _parse_decimal(cls, v):
        return parse_decimal_field(v)


class BankingTransaction(BaseModel):
    """Banking transaction detail"""
    transaction_date: date = Field(..., description="Transaction date")
    transaction_type: Literal["DEBIT", "CREDIT", "TRANSFER", "FEE"] = Field(..., description="Transaction type")
    amount_aed: Decimal = Field(..., description="Transaction amount in AED")
    description: str = Field(None, description="Transaction description")
    category: str = Field(None, description="Transaction category")

    @field_validator('amount_aed', mode='before')
    @classmethod
    def _parse_decimal(cls, v):
        return parse_decimal_field(v)


class BankingProductRecommendation(ProductRecommendation):
    """Banking product recommendation with banking-specific fields"""
    
    # Banking-specific fields
    banking_product_type: Literal["CURRENT_ACCOUNT", "SAVINGS_ACCOUNT", "FIXED_DEPOSIT", "OVERDRAFT", "SWEEP", "OTHER"] = Field(
        ..., description="Type of banking product"
    )
    
    # Product features
    interest_rate: Optional[Decimal] = Field(None, description="Interest rate percentage")
    minimum_balance_aed: Optional[Decimal] = Field(None, description="Minimum balance requirement in AED")
    key_features: List[str] = Field(..., description="Key product features")
    fee_structure: Optional[str] = Field(None, description="Fee structure description")
    product_eligibility: str = Field(..., description="Detailed Description of Product eligibility criteria and why this client is eligible")
    justification: JustificationStep = Field(..., description="Justification for of the recommendation using 5 step process")
    
    # Suitability
    liquidity_impact: str = Field(..., description="Impact on client liquidity")
    optimization_benefit: str = Field(..., description="How this optimizes client's banking relationship")
    
    @field_validator('recommended_amount_aed', 'percentage_of_portfolio', 'interest_rate', 'minimum_balance_aed', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        """Parse decimal fields with thousand separators, currency codes, percentages, etc."""
        if isinstance(v, str) and ('percent of' in v.lower() or '% of' in v):
            match = re.search(r'(\d+(?:\.\d+)?)\s*%', v)
            if match:
                return Decimal(match.group(1))
        return parse_decimal_field(v)


class BankingAgentOutput(BaseModel):
    """Simplified Banking/CASA Agent output"""
    
    client_id: str = Field(..., description="Client identifier")
    
    # Simplified Banking Overview
    total_casa_balance_aed: Decimal = Field(..., description="Total CASA balance in AED")
    investible_cash_aed: Decimal = Field(..., description="Estimated investible cash in AED")
    
    # Product Recommendations (0-2 only)
    product_recommendations: List[BankingProductRecommendation] = Field(
        default_factory=list,
        min_items=0,
        max_items=2,
        description="Top 1-2 banking product recommendations"
    )

    @field_validator('total_casa_balance_aed', 'investible_cash_aed', mode='before')
    @classmethod
    def _parse_decimal(cls, v):
        return parse_decimal_field(v)

    # Executive summary
    Agent_Recommends: str = Field(default="", description="2-3 sentence summary")


# =============================================================================
# BANCASSURANCE AGENT MODELS
# =============================================================================

class ExistingPolicy(BaseModel):
    """Existing bancassurance policy"""
    policy_number: str = Field(..., description="Policy number")
    policy_type: str = Field(..., description="Policy type")
    policy_category: str = Field(..., description="Policy category (e.g., Investment-Linked, Protection)")
    market_value_aed: Decimal = Field(..., description="Current market value in AED")
    time_key: Optional[date] = Field(None, description="Snapshot date of policy data")

    @field_validator('market_value_aed', mode='before')
    @classmethod
    def _parse_decimal(cls, v):
        return parse_decimal_field(v)


class MLInsuranceNeed(BaseModel):
    """ML-identified insurance need"""
    need_name: str = Field(..., description="Name of insurance need")
    need_value: Literal[0, 1] = Field(..., description="Whether need is active (1) or not (0)")
    recommended_products: List[str] = Field(..., description="Product categories recommended for this need")


class LifecycleTrigger(BaseModel):
    """Lifecycle event trigger for bancassurance"""
    trigger_type: Literal[
        "BIRTHDAY_PROXIMITY", "AGE_MILESTONE", "FAMILY_STATUS", "INCOME_LEVEL", 
        "BANKING_SEGMENT", "COVERAGE_GAP", "SPENDING_PATTERN"
    ] = Field(..., description="Type of lifecycle trigger")
    priority: Literal["HIGH", "MEDIUM", "LOW"] = Field(..., description="Trigger priority")
    description: str = Field(..., description="Description of the trigger")
    days_to_event: Optional[int] = Field(None, description="Days until event if time-sensitive")
    milestone: Optional[str] = Field(None, description="Milestone description if applicable")
    recommended_products: List[str] = Field(..., description="Products recommended based on this trigger")
    talking_point: str = Field(..., description="RM talking point for this trigger")
    
    @field_validator('trigger_type', mode='before')
    @classmethod
    def normalize_trigger_type(cls, v):
        """Normalize trigger_type to uppercase with underscores"""
        if isinstance(v, str):
            # Convert to uppercase and replace spaces with underscores
            return v.upper().replace(' ', '_').replace('-', '_')
        return v




class BancassuranceProductRecommendation(ProductRecommendation):
    """Bancassurance product recommendation with insurance-specific fields"""
    
    # Insurance-specific fields
    insurance_type: Literal[
        "INVESTMENT_LINKED", "ULIP", "TERM_LIFE", "WHOLE_LIFE", "HEALTH", 
        "CRITICAL_ILLNESS", "PENSION", "ENDOWMENT", "CHILD_PLAN", "MORTGAGE_PROTECTION",
        "LEGACY_PLANNING", "WHOLE_OF_LIFE"
    ] = Field(..., description="Type of insurance product")
    
    # Coverage details (product_eligibility and justification_steps inherited from ProductRecommendation base class)
    
    # Trigger alignment
    lifecycle_trigger_alignment: List[str] = Field(..., description="Lifecycle triggers this product addresses")
    ml_need_alignment: List[str] = Field(..., description="ML needs this product addresses")
    
    # Objection handling
    objection_handling: dict = Field(..., description="Pre-emptive objection handling talking points")
    
    @field_validator('recommended_amount_aed', 'percentage_of_portfolio', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        """Parse decimal fields with thousand separators, currency codes, percentages, etc."""
        if isinstance(v, str) and ('percent of' in v.lower() or '% of' in v):
            match = re.search(r'(\d+(?:\.\d+)?)\s*%', v)
            if match:
                return Decimal(match.group(1))
        return parse_decimal_field(v)


class BancassuranceAgentOutput(BaseModel):
    """Complete structured output from Bancassurance Agent"""
    
    client_id: str = Field(..., description="Client identifier")
    client_name: str = Field(..., description="Client full name")
    age: float = Field(..., description="Client age")
    age_segment: str = Field(..., description="Client age segment")
    
    # Current Bancassurance Portfolio
    existing_policies: List[ExistingPolicy] = Field(..., description="Existing bancassurance policies")
    total_policies_count: int = Field(..., description="Total number of policies")
    total_policy_value_aed: Decimal = Field(..., description="Total policy value in AED")
    portfolio_adequacy: str = Field(..., description="Assessment of current coverage adequacy")
    
    # ML-Identified Insurance Needs
    
    insurance_needs: List[MLInsuranceNeed] = Field(..., description="ML-identified insurance needs")
    active_needs_count: int = Field(..., description="Number of active needs")
    
    # Lifecycle Triggers
    lifecycle_triggers: List[LifecycleTrigger] = Field(..., description="Time-sensitive lifecycle triggers")
    high_priority_trigger_count: int = Field(..., description="Number of high-priority triggers")
    
  
    
    # Top 3-5 Product Recommendations
    product_recommendations: List[BancassuranceProductRecommendation] = Field(
        ..., 
        min_items=0,
        max_items=5,
        description="Top 3-5 bancassurance recommendations with 5-step justification (empty if client has adequate coverage)"
    )
    

    
    # Cross-sell Opportunities
    cross_sell_opportunities: List[str] = Field(..., description="Cross-sell with other products")
    
    # Data Sources
    data_sources_used: List[str] = Field(..., description="List of all tools/tables used for bancassurance analysis")

    @field_validator('total_policy_value_aed', mode='before')
    @classmethod
    def _parse_decimal(cls, v):
        return parse_decimal_field(v)

    # Executive narrative for senior management
    Agent_Recommends: str = Field(
        default="",
        description=(
            "Executive narrative: actionable, professional summary referencing actual data points, "
            "combining inputs and recommendations for senior management."
        ),
    )


# =============================================================================
# RM STRATEGY AGENT MODELS
# =============================================================================

class ActionItem(BaseModel):
    """Specific action item for RM"""
    action_number: int = Field(..., description="Action item number")
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(..., description="Action priority")
    action_description: str = Field(..., description="Detailed action description")
    rationale: str = Field(..., description="Data-driven rationale for this action")
    execution_steps: List[str] = Field(..., description="Specific steps to execute this action")
    expected_outcome: str = Field(..., description="Expected outcome of this action")
    data_supporting_action: str = Field(..., description="Agent output or data source supporting this action")


class ProductRecommendationStrategy(BaseModel):
    """Strategic approach for product recommendations"""
    product_category: str = Field(..., description="Product category (Investment, Loan, Banking, Bancassurance)")
    recommended_products: List[str] = Field(..., description="List of recommended products from specialist agent")
    client_fit_rationale: str = Field(..., description="Why these products fit the client")
    conversation_approach: str = Field(..., description="How to approach conversation about these products")
    expected_investment_amount: Optional[str] = Field(None, description="Expected investment/uptake amount")
    supporting_data_summary: List[str] = Field(..., description="Key data points supporting recommendation")


class ClientEngagementQuestion(BaseModel):
    """Data-backed question for client engagement"""
    question_number: int = Field(..., description="Question number")
    question_text: str = Field(..., description="Exact question to ask client")
    context: str = Field(..., description="Context/data point supporting this question")
    purpose: str = Field(..., description="Purpose of asking this question")
    follow_up_action: str = Field(..., description="Follow-up action based on client response")


class RiskFlag(BaseModel):
    """Risk flag requiring monitoring or mitigation"""
    flag_type: str = Field(..., description="Type of risk flag")
    issue_description: str = Field(..., description="Description of the issue")
    impact: str = Field(..., description="Potential impact if not addressed")
    mitigation_strategy: str = Field(..., description="Strategy to mitigate this risk")
    monitoring_approach: str = Field(..., description="How to monitor this risk")


class SuccessMetric(BaseModel):
    """Success metric for tracking strategy execution"""
    metric_number: int = Field(..., description="Metric number")
    goal_description: str = Field(..., description="Description of the goal")
    target_value: str = Field(..., description="Target value or outcome")
    measurement_method: str = Field(..., description="How to measure success")
    timeline: str = Field(..., description="Timeline for achievement")
    data_source: str = Field(..., description="Agent output supporting this metric")


class DataDrivenTalkingPoint(BaseModel):
    """Data-driven talking point for RM"""
    talking_point_number: int = Field(..., description="Talking point number")
    talking_point_text: str = Field(..., description="Exact talking point with specific data")
    supporting_data: str = Field(..., description="Specific data supporting this point")
    when_to_use: str = Field(..., description="When/in what context to use this point")


class RMStrategyAgentOutput(BaseModel):
    """Complete structured output from RM Strategy Agent"""
    
    client_id: str = Field(..., description="Client identifier")
    
    # Executive Summary
    executive_summary: str = Field(..., description="Executive summary for RM")
    
    # RM Information
    rm_id: Optional[str] = Field(None, description="RM identifier")
    client_name: Optional[str] = Field(None, description="Client name")
    client_segment: str = Field(..., description="Client segment")
    relationship_tenure: float = Field(..., description="Relationship tenure in years")
    current_aum_aed: Decimal = Field(..., description="Current AUM in AED")
    risk_profile: str = Field(..., description="Risk profile")
    
    # Priority Action Items (Top 7 from next 7 days section)
    priority_actions: List[ActionItem] = Field(
        ..., 
        min_items=1,
        max_items=7,
        description="Priority action items with data-driven rationale"
    )
    
    # Data-Driven Talking Points (Top 10)
    talking_points: List[DataDrivenTalkingPoint] = Field(
        ...,
        min_items=5,
        max_items=10,
        description="Data-driven talking points with specific numbers"
    )

     # Client Engagement Questions (Top 15)
    engagement_questions: List[ClientEngagementQuestion] = Field(
        ...,
        min_items=5,
        max_items=15,
        description="Data-backed questions for client engagement"
    )

    # Product Recommendation Strategy (by category)
    product_strategies: List[ProductRecommendationStrategy] = Field(
        ..., description="Strategic approach for each product category"
    )

    @field_validator('current_aum_aed', mode='before')
    @classmethod
    def _parse_decimal(cls, v):
        return parse_decimal_field(v)


class MarketIntelligenceAgentOutput(BaseModel):
    """Simplified Market Intelligence Agent output - provides essential market context"""
    
    model_config = {"populate_by_name": True}
    
    # Market Overview (Required)
    market_overview: str = Field(description="2-3 sentence market summary", alias="Market Overview")
    
    # Investment Themes (Required)
    investment_themes: List[str] = Field(description="Top 3 investment themes", max_items=3, alias="Investment Themes")
    
    # Agent_Recommends (Required)
    Agent_Recommends: str = Field(description="2-3 sentence market timing recommendation")


# =============================================================================
# COMPLETE SYSTEM OUTPUT
# =============================================================================

class EliteXV5CompleteOutput(BaseModel):
    """Complete structured output from entire EliteX V5 system"""
    
    client_id: str = Field(..., description="Client identifier")
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="When analysis was performed")
    
    # Agent Outputs
    manager_output: ManagerAgentOutput = Field(..., description="Manager Agent structured output")
    risk_output: RiskComplianceAgentOutput = Field(..., description="Risk & Compliance Agent structured output")
    investment_output: InvestmentAgentOutput = Field(..., description="Investment Agent structured output")
    loan_output: LoanAgentOutput = Field(..., description="Loan Agent structured output")
    banking_output: BankingAgentOutput = Field(..., description="Banking/CASA Agent structured output")
    bancassurance_output: BancassuranceAgentOutput = Field(..., description="Bancassurance Agent structured output")
    rm_strategy_output: RMStrategyAgentOutput = Field(..., description="RM Strategy Agent structured output")
    
    # Metadata
    model_version: str = Field(default="V5", description="EliteX model version")
    processing_time_seconds: Optional[float] = Field(None, description="Total processing time in seconds")

