# Missing Sales & Engagement Triggers Analysis
## EliteX V8 Multi-Agent System

**Date:** October 18, 2025  
**Analysis Scope:** Identify additional tool functions for more exhaustive client recommendations

---

## 🎯 Currently Implemented Triggers

### ✅ Compliance & Time-Sensitive
1. **KYC Expiry** - `get_kyc_expiring_within_6m()`
2. **Product Maturity** - `get_maturing_products_6m()` (Loans, Investments, CASA)

### ✅ Portfolio & Investment
3. **Portfolio Concentration Risk** - `get_elite_portfolio_risk_metrics()`
4. **Asset Allocation Mismatch** - `get_elite_asset_allocation_data()`
5. **Investment Holdings** - `get_elite_client_investments_summary()`
6. **Share of Potential** - `get_elite_share_of_potential()`

### ✅ Credit & Lending
7. **AECB Alerts** - `get_elite_aecb_alerts()`
8. **Credit Capacity** - `get_elite_loan_data()` (DTI, lending capacity)
9. **Loan Products** - `get_elite_loan_data()`

### ✅ Banking & CASA
10. **CASA Balances & Trends** - `get_elite_banking_casa_data()`
11. **Transaction Patterns** - `get_elite_client_behavior_analysis()`

### ✅ Bancassurance
12. **Insurance Holdings** - `get_elite_bancassurance_holdings()`
13. **Lifecycle Triggers** - `get_elite_bancassurance_lifecycle_triggers()`
14. **ML Propensity** - `get_elite_bancassurance_ml_propensity()`
15. **Coverage Gaps** - `get_elite_bancassurance_gap_analysis()`

### ✅ Engagement & Communication
16. **Engagement Analysis** - `get_elite_engagement_analysis()`
17. **Communication History** - `get_elite_communication_history()`

---

## 🔴 MISSING TRIGGERS - High Priority

### 1. RELATIONSHIP & LIFECYCLE TRIGGERS

#### A. **Relationship Tenure Milestones** 🎯 HIGH PRIORITY
**Status:** Mentioned in prompts but NOT calculated by any tool  
**Current Gap:** Prompts mention "1yr, 3yr, 5yr, 10yr - loyalty/upgrade opportunities" but no tool detects this  
**Proposed Tool:** `get_relationship_milestones()`

**Business Logic:**
```python
def get_relationship_milestones(client_id):
    """
    Detect relationship tenure milestones and loyalty opportunities
    
    Returns:
    - tenure_years: Exact relationship tenure
    - milestone_approaching: Upcoming milestone (1yr, 3yr, 5yr, 10yr, 15yr, 20yr)
    - days_to_milestone: Days until milestone
    - milestone_type: ANNIVERSARY_1Y, ANNIVERSARY_3Y, etc.
    - suggested_action: Loyalty reward, tier upgrade evaluation, relationship review
    - lifetime_value: Total revenue from client (AUM fees + product fees)
    - tenure_category: NEW (<1yr), ESTABLISHED (1-5yr), LOYAL (5-10yr), LEGACY (>10yr)
    """
    # Calculate from open_date in client_context
    # Check if within 60 days of milestone
    # Recommend: Thank you gift, relationship review, tier upgrade assessment
```

**Data Source:** `core.client_context.open_date`  
**Trigger Thresholds:**
- Within 60 days of 1yr, 3yr, 5yr, 10yr anniversary = HIGH priority
- New client (<6 months) = Welcome program opportunity
- Legacy client (>10yr) = VIP treatment, exclusive offerings

---

#### B. **Birthday Proximity & Age Milestones** 🎯 HIGH PRIORITY
**Status:** Mentioned in prompts but calculation is INCOMPLETE  
**Current Gap:** Bancassurance tool mentions it, but no standalone tool calculates days to birthday and age milestones  
**Proposed Tool:** `get_birthday_and_age_triggers()`

**Business Logic:**
```python
def get_birthday_and_age_triggers(client_id):
    """
    Calculate birthday proximity and age milestone triggers
    
    Returns:
    - date_of_birth: Client DOB
    - age: Current age
    - next_birthday_date: Next birthday date
    - days_to_birthday: Days until birthday (0-365)
    - birthday_month: Month of birthday
    - birthday_proximity_flag: IMMEDIATE (<30d), NEAR (<60d), UPCOMING (<90d)
    - age_milestone_type: RETIREMENT_AGE (60, 65), MID_CAREER (40, 45, 50), YOUNG (25, 30, 35)
    - milestone_implications: Insurance needs, retirement planning, estate planning
    - generational_cohort: Gen Z, Millennial, Gen X, Boomer, Silent
    - life_stage: YOUNG_PROFESSIONAL, MID_CAREER, PRE_RETIREMENT, RETIREMENT
    """
    # Calculate from dob in client_context
    # Flag if birthday within 60 days
    # Identify age milestones: 25, 30, 35, 40, 45, 50, 55, 60, 65, 70
```

**Data Source:** `core.client_context.dob`  
**Trigger Thresholds:**
- Birthday within 30 days = Send gift, call client = CRITICAL
- Birthday within 60 days = Plan engagement = HIGH
- Age 40, 45, 50 = Insurance, estate planning = HIGH
- Age 60, 65 = Retirement planning = HIGH
- Age 25, 30, 35 = Wealth accumulation products = MEDIUM

---

### 2. IDLE CASH & LIQUIDITY OPTIMIZATION TRIGGERS

#### C. **Idle Cash Optimization** 🎯 HIGH PRIORITY
**Status:** Mentioned in prompts but NOT calculated  
**Current Gap:** Prompt says "CASA > 3x monthly income = optimization opportunity" but no tool calculates this  
**Proposed Tool:** `get_idle_cash_opportunities()`

**Business Logic:**
```python
def get_idle_cash_opportunities(client_id):
    """
    Identify idle cash and liquidity optimization opportunities
    
    Returns:
    - total_casa_balance: Current CASA balance
    - monthly_income: Monthly income
    - monthly_expenses_estimate: Estimated from transaction history (avg 6m spend)
    - recommended_emergency_fund: 3-6 months expenses
    - excess_liquidity: CASA - recommended_emergency_fund
    - idle_cash_percentage: (excess_liquidity / total_net_worth) * 100
    - opportunity_amount: Amount that can be invested
    - cash_drag_cost: Estimated opportunity cost (inflation + lost returns)
    - recommended_allocation: Suggested products for excess cash
    - urgency: CRITICAL (>6x monthly expense), HIGH (>4x), MEDIUM (>3x)
    """
    # Compare CASA balance to monthly income & spending
    # If CASA > 3x monthly income, flag for investment
    # If CASA > 6x monthly income, CRITICAL priority
```

**Data Source:** 
- `core.client_prod_balance_monthly` (CASA balances)
- `core.client_context.income` (monthly income)
- `core.client_transaction` (spending patterns)

**Trigger Thresholds:**
- CASA > 6x monthly income = CRITICAL (severe cash drag)
- CASA > 4x monthly income = HIGH (excess liquidity)
- CASA > 3x monthly income = MEDIUM (optimization opportunity)

---

#### D. **Large Cash Inflows Detection** 🎯 HIGH PRIORITY
**Status:** Completely missing  
**Proposed Tool:** `get_large_cash_inflow_triggers()`

**Business Logic:**
```python
def get_large_cash_inflow_triggers(client_id):
    """
    Detect recent large cash inflows requiring investment planning
    
    Returns:
    - recent_large_deposits: List of deposits >100K AED in last 30 days
    - total_inflow_30d: Sum of large deposits
    - inflow_source_category: Salary, Bonus, Sale_of_Asset, Inheritance, Gift, Business_Income
    - days_since_inflow: Days since deposit
    - current_uninvested_balance: Amount still in CASA
    - investment_readiness_score: HIGH/MEDIUM/LOW
    - suggested_allocation_strategy: Based on risk profile and amount
    - time_sensitivity: IMMEDIATE (<7d), URGENT (<30d), MODERATE (<90d)
    """
    # Analyze clienttransactioncredit for large deposits
    # Flag deposits >100K AED or >2x average monthly deposit
    # Track if invested or still in CASA
```

**Data Source:**
- `core.clienttransactioncredit` (credit transactions)
- `core.client_prod_balance_monthly` (current CASA)

**Trigger Thresholds:**
- Deposit >500K AED in last 30 days = CRITICAL
- Deposit >200K AED in last 30 days = HIGH
- Deposit >100K AED in last 30 days = MEDIUM

---

### 3. PORTFOLIO PERFORMANCE & HEALTH TRIGGERS

#### E. **Underperforming Holdings** 🎯 MEDIUM-HIGH PRIORITY
**Status:** Partially covered, needs dedicated tool  
**Proposed Tool:** `get_underperforming_holdings()`

**Business Logic:**
```python
def get_underperforming_holdings(client_id):
    """
    Identify underperforming securities requiring review/rebalancing
    
    Returns:
    - underperforming_securities: List of holdings with XIRR < benchmark
    - performance_gap: Difference from benchmark
    - holding_period: Years held
    - unrealized_loss_aed: Current paper loss
    - tax_loss_harvesting_opportunity: If applicable
    - replacement_recommendations: Better alternatives
    - total_underperformance_drag: Total portfolio drag from poor performers
    - action_priority: IMMEDIATE, REVIEW, MONITOR
    """
    # Compare security XIRR to benchmark
    # Flag holdings with negative or significantly below-benchmark returns
    # Recommend replacement or rebalancing
```

**Data Source:**
- `core.client_investment` (holdings with XIRR)
- `core.fund_segment_benchmarks` (benchmarks)

**Trigger Thresholds:**
- XIRR < -10% = CRITICAL review
- XIRR < benchmark - 5% = HIGH priority
- XIRR < benchmark - 3% = MEDIUM review

---

#### F. **Dividend & Coupon Maturity Tracker** 🎯 MEDIUM PRIORITY
**Status:** Completely missing  
**Proposed Tool:** `get_upcoming_dividend_coupon_payments()`

**Business Logic:**
```python
def get_upcoming_dividend_coupon_payments(client_id):
    """
    Track upcoming dividend/coupon payments for reinvestment planning
    
    Returns:
    - upcoming_payments: List of expected payments in next 90 days
    - payment_date: Expected payment date
    - estimated_amount_aed: Expected payment amount
    - security_name: Source security
    - reinvestment_opportunity: Flag if should be reinvested
    - total_expected_inflow_90d: Sum of all payments
    - auto_reinvest_enabled: Boolean
    - suggested_reinvestment_product: If not auto-reinvest
    """
    # Track dividend/coupon schedules from holdings
    # Flag payments requiring reinvestment decisions
```

**Data Source:**
- `core.client_holding` (securities held)
- `core.funds`, `core.bonds` (payment schedules)

---

### 4. CREDIT & LENDING BEHAVIOR TRIGGERS

#### G. **High Credit Utilization** 🎯 HIGH PRIORITY
**Status:** Mentioned but NOT calculated  
**Proposed Tool:** `get_credit_utilization_triggers()`

**Business Logic:**
```python
def get_credit_utilization_triggers(client_id):
    """
    Analyze credit card and credit line utilization patterns
    
    Returns:
    - total_credit_limit: Sum of all credit facilities
    - total_utilized: Current utilization
    - utilization_percentage: Utilization rate
    - utilization_trend: INCREASING, DECREASING, STABLE (last 6 months)
    - high_utilization_cards: Cards with >70% utilization
    - missed_payments_6m: Count of missed payments
    - opportunity_type: CONSOLIDATION, INCREASE_LIMIT, BALANCE_TRANSFER, PAYDOWN
    - credit_health_score: Excellent/Good/Fair/Poor
    - recommended_action: Specific product or strategy
    """
    # Analyze credit facilities from productbalance
    # Calculate utilization = outstanding / limit
    # Flag high utilization for consolidation or limit increase
```

**Data Source:**
- `core.productbalance` (credit facilities)
- `core.client_transaction` (payment patterns)

**Trigger Thresholds:**
- Utilization >90% = CRITICAL (debt trap risk)
- Utilization >70% = HIGH (consolidation/increase opportunity)
- Utilization >50% with increasing trend = MEDIUM
- Utilization <10% consistently = Reduce limit or cancel

---

#### H. **Loan Nearing Payoff** 🎯 MEDIUM-HIGH PRIORITY
**Status:** Mentioned but NOT calculated  
**Proposed Tool:** `get_loan_payoff_opportunities()`

**Business Logic:**
```python
def get_loan_payoff_opportunities(client_id):
    """
    Identify loans nearing payoff for refinance/new lending opportunities
    
    Returns:
    - loans_nearing_payoff: Loans with <10% remaining balance
    - current_outstanding: Remaining balance
    - original_amount: Original loan amount
    - percentage_paid: % of loan paid off
    - estimated_payoff_date: Based on payment history
    - months_to_payoff: Estimated months remaining
    - opportunity_type: NEW_LOAN, REFINANCE, TOP_UP, CREDIT_INCREASE
    - freed_capacity_upon_payoff: Monthly cash flow freed up
    - cross_sell_opportunity_aed: Estimated new lending capacity
    """
    # Identify loans with outstanding < 10% of original
    # Or loans within 12 months of payoff
    # Recommend new lending or refinancing
```

**Data Source:**
- `core.productbalance` (loan balances)
- Historical balance trends

**Trigger Thresholds:**
- Outstanding <10% of original = HIGH priority
- <12 months to payoff = MEDIUM priority
- Recently paid off (<90 days) = HIGH (freed capacity)

---

### 5. SPENDING & TRANSACTION BEHAVIOR TRIGGERS

#### I. **Spending Category Shifts** 🎯 MEDIUM PRIORITY
**Status:** Partially captured in behavior analysis, needs dedicated tool  
**Proposed Tool:** `get_spending_category_shifts()`

**Business Logic:**
```python
def get_spending_category_shifts(client_id):
    """
    Detect significant shifts in spending categories indicating life changes
    
    Returns:
    - top_spending_categories_current: Last 3 months
    - top_spending_categories_prior: Prior 6 months (months 4-9)
    - category_changes: Categories with >30% increase or decrease
    - emerging_categories: New spending categories
    - declining_categories: Reduced spending categories
    - life_event_indicators: MARRIAGE, CHILD, RELOCATION, BUSINESS_START, TRAVEL_INCREASE
    - product_opportunities: Suggested products based on spending shifts
    - change_significance: MAJOR, MODERATE, MINOR
    """
    # Compare spending by category across time periods
    # Flag significant shifts (>30% change)
    # Infer life events from spending patterns
```

**Data Source:**
- `core.client_transaction`
- `core.clienttransactiondebit` (categorized spending)

**Examples:**
- Education spending spike → Education financing products
- Healthcare spending increase → Health insurance upgrade
- Travel spending surge → Travel insurance, forex cards
- Rent/mortgage changes → Relocation, home loan opportunity

---

#### J. **Dormant Account Reactivation** 🎯 MEDIUM PRIORITY
**Status:** Completely missing  
**Proposed Tool:** `get_dormant_account_triggers()`

**Business Logic:**
```python
def get_dormant_account_triggers(client_id):
    """
    Identify dormant products/accounts for reactivation or closure
    
    Returns:
    - dormant_accounts: Accounts with no transactions in 6+ months
    - account_type: CASA, Investment, Credit Card
    - days_inactive: Days since last transaction
    - balance_amount: Current balance (if any)
    - monthly_fees_paid: Fees paid for inactive account
    - opportunity_type: REACTIVATE, CONSOLIDATE, CLOSE
    - reactivation_incentive: Suggested promotion
    - annual_cost_of_dormancy: Total fees on dormant accounts
    """
    # Identify accounts/products with no activity for 180+ days
    # Calculate opportunity cost of fees on dormant accounts
```

**Data Source:**
- `core.productbalance` (all products)
- `core.client_transaction` (transaction history)

**Trigger Thresholds:**
- No activity for 12+ months = HIGH (closure/reactivation)
- No activity for 6-12 months = MEDIUM (check-in)

---

### 6. CROSS-SELL & PRODUCT GAP TRIGGERS

#### K. **Missing Core Products** 🎯 HIGH PRIORITY
**Status:** Partially covered, needs comprehensive tool  
**Proposed Tool:** `get_product_gap_analysis()`

**Business Logic:**
```python
def get_product_gap_analysis(client_id):
    """
    Comprehensive analysis of missing core banking products
    
    Returns:
    - current_products: List of products held
    - missing_products: List of core products NOT held
    - gap_category: BANKING, INVESTMENT, CREDIT, INSURANCE, TRADE
    - gap_priority: CRITICAL, HIGH, MEDIUM, LOW
    - gap_rationale: Why client should have this product
    - expected_revenue: Potential revenue from gap closure
    - client_eligibility: Eligible/Not_Eligible with reason
    - recommended_sequence: Order to pitch products
    
    Core Products Checklist:
    Banking:
    - Savings Account
    - Current Account
    - Fixed Deposit
    - Salary Account
    - Foreign Currency Account
    
    Credit:
    - Credit Card (any)
    - Personal Loan
    - Auto Loan
    - Mortgage
    - Credit Line
    
    Investment:
    - Mutual Funds
    - Bonds
    - Stocks
    - Portfolio Management
    - Structured Products
    
    Insurance:
    - Life Insurance
    - Health Insurance
    - Critical Illness
    - Disability Insurance
    
    Trade:
    - Trade Finance (if business client)
    - Documentary Credit
    """
    # Check all product categories against client holdings
    # Prioritize by income, segment, and risk profile
```

**Data Source:**
- `core.productbalance` (current products)
- All product catalogs
- `core.client_context` (eligibility)

---

#### L. **Segment Mismatch / Upgrade Opportunity** 🎯 HIGH PRIORITY
**Status:** Completely missing  
**Proposed Tool:** `get_segment_upgrade_opportunities()`

**Business Logic:**
```python
def get_segment_upgrade_opportunities(client_id):
    """
    Identify clients eligible for segment upgrade (e.g., Premium to Elite)
    
    Returns:
    - current_segment: Current banking segment
    - current_tier: Elite Standard, Elite Plus, etc.
    - total_relationship_value: AUM + CASA + Credit Facilities
    - segment_upgrade_eligible: Boolean
    - target_segment: Recommended segment
    - gap_to_upgrade: AED amount or criteria missing
    - upgrade_benefits: List of benefits at higher tier
    - estimated_additional_revenue: Revenue from upgrade
    - downgrade_risk: If at risk of segment downgrade
    - retention_priority: If borderline for downgrade
    """
    # Calculate total relationship value (TRV)
    # Compare to segment thresholds
    # Flag if eligible for upgrade or at risk of downgrade
    
    # Typical Thresholds (UAE):
    # Mass Market: <250K AED TRV
    # Priority: 250K-1M AED TRV
    # Wealth: 1M-5M AED TRV
    # Elite: 5M-25M AED TRV
    # Private: >25M AED TRV
```

**Data Source:**
- `core.client_context.customer_profile_banking_segment`
- All balance data

---

### 7. EXTERNAL EVENT TRIGGERS

#### M. **Interest Rate Environment Triggers** 🎯 MEDIUM PRIORITY
**Status:** Completely missing  
**Proposed Tool:** `get_interest_rate_opportunities()`

**Business Logic:**
```python
def get_interest_rate_opportunities(client_id):
    """
    Identify opportunities based on interest rate environment changes
    
    Returns:
    - current_eibor_rate: Current EIBOR
    - rate_trend: RISING, FALLING, STABLE (last 90 days)
    - rate_change_bps: Basis points change
    - affected_products: Client products with variable rates
    - refinance_opportunities: Loans that could be refinanced
    - deposit_optimization: Fixed deposit opportunities
    - savings_potential_aed: Potential savings from actions
    - timing_urgency: Act_Now, Within_30d, Monitor
    """
    # Track EIBOR/Fed Rate trends
    # Identify variable rate loans for refinancing if rates rising
    # Suggest locking in fixed rates if rates rising
    # Suggest variable rates if rates falling
```

**Data Source:**
- `economic_indicators` table
- `core.productbalance` (variable rate products)

---

## 📊 DATA AVAILABILITY VALIDATION ✅ COMPLETE

**Analysis Date:** October 18, 2025  
**Method:** Direct database column verification  
**Result:** 14 out of 18 triggers FEASIBLE

### ✅ FEASIBLE TRIGGERS (14) - Ready for Implementation
1. ✅ **Relationship Tenure Milestones** - `core.client_context.open_date`, `tenure`
2. ✅ **Birthday Proximity & Age Milestones** - `core.client_context.dob`, `age`
3. ✅ **Idle Cash Optimization** - `core.productbalance` CASA + `income`
4. ✅ **Large Cash Inflows** - `core.clienttransactioncredit`
5. ✅ **High Credit Utilization** - `core.productbalance` credit facilities
6. ✅ **Product Gap Analysis** - All product tables available
7. ✅ **Segment Upgrade Opportunities** - `customer_profile_banking_segment` + balances
8. ✅ **Complaint Follow-up** - `core.followup`, `rmclientservicerequests`
9. ✅ **Underperforming Holdings** - `core.client_holding.holding_wise_return_since_inception`
10. ✅ **Loan Nearing Payoff** - `core.productbalance.outstanding`, `maturity_date`
11. ✅ **Spending Category Shifts** - `transaction_history.Category`
12. ✅ **Dormant Account Reactivation** - Transaction timestamps
13. ✅ **Engagement Risk Score** - `core.engagement_analysis`, `communication_log`
14. ✅ **Interest Rate Opportunities** - `economic_indicators`

### ❌ NOT FEASIBLE (4) - Insufficient Data
1. ❌ **Off-Us Relationship Intelligence** - Fields exist but NULL/empty
2. ❌ **Passport/Visa/Document Expiry** - No expiry date columns
3. ❌ **Dividend/Coupon Tracker** - No payment schedule data
4. ❌ **Regulatory/Tax Changes** - Requires external regulatory feed

**📄 See `TRIGGERS_IMPLEMENTATION_PLAN.md` for detailed implementation roadmap.**

---

### 8. COMMUNICATION & ENGAGEMENT TRIGGERS

#### O. **Low Engagement Alert** 🎯 MEDIUM PRIORITY
**Status:** Partially covered, needs enhancement  
**Proposed Tool:** `get_engagement_risk_score()`

**Business Logic:**
```python
def get_engagement_risk_score(client_id):
    """
    Calculate engagement risk and attrition probability
    
    Returns:
    - engagement_score: 0-100 (100 = highly engaged)
    - engagement_trend: IMPROVING, DECLINING, STABLE
    - last_interaction_date: Most recent contact
    - days_since_last_contact: Days
    - interaction_frequency_last_6m: Count of interactions
    - channel_preference: Digital, Branch, Phone, Email
    - response_rate: % of outreach responded to
    - product_usage_score: Active vs dormant products
    - attrition_risk: HIGH, MEDIUM, LOW
    - retention_action_required: Boolean
    - recommended_engagement_strategy: Specific next steps
    """
    # Analyze communication logs
    # Calculate engagement metrics
    # Flag clients with declining engagement
```

**Data Source:**
- `core.engagement_analysis`
- `core.communication_log`
- `core.callreport`

---

#### P. **Complaint Resolution Follow-up** 🎯 HIGH PRIORITY
**Status:** Completely missing  
**Proposed Tool:** `get_complaint_followup_triggers()`

**Business Logic:**
```python
def get_complaint_followup_triggers(client_id):
    """
    Track complaint resolution and follow-up opportunities
    
    Returns:
    - open_complaints: Count of unresolved complaints
    - recent_complaints_6m: List of recent complaints
    - complaint_category: SERVICE, PRODUCT, FEES, TECHNICAL
    - complaint_severity: CRITICAL, HIGH, MEDIUM, LOW
    - days_open: Days since complaint filed
    - resolution_status: OPEN, IN_PROGRESS, RESOLVED, ESCALATED
    - follow_up_required: Boolean
    - days_since_resolution: For resolved complaints
    - relationship_health_impact: Negative/Neutral/Positive
    - recovery_action_required: Goodwill gesture, fee waiver, etc.
    """
    # Track complaints from service request systems
    # Flag unresolved complaints >7 days old
    # Schedule follow-up for resolved complaints
```

**Data Source:**
- `core.rmclientservicerequests`
- `core.followup`

---






