# app.py
# MBA Tax Optimizer — Final version with in-hand salary logic for old and new regime

import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO
from datetime import date

st.set_page_config(page_title="MBA Tax Optimizer", layout="wide")

# -------------------------
# RULES
# -------------------------

RULES = {
    "fy": "2025-26",
    "standard_deduction": 50000,
    "80c_limit": 150000,
    "80ccd_1b_limit": 50000,
    "hra_metro_pct": 0.50,
    "hra_nonmetro_pct": 0.40,
    "cess_rate": 0.04,
    "tax_slabs_old": [
        {"upto": 250000, "rate": 0},
        {"upto": 500000, "rate": 0.05},
        {"upto": 1000000, "rate": 0.20},
        {"upto": 999999999, "rate": 0.30}
    ],
    "tax_slabs_new": [
        {"upto": 300000, "rate": 0},
        {"upto": 600000, "rate": 0.05},
        {"upto": 900000, "rate": 0.10},
        {"upto": 1200000, "rate": 0.15},
        {"upto": 1500000, "rate": 0.20},
        {"upto": 999999999, "rate": 0.30}
    ],
    "new_regime_allowed": {
        "standard_deduction": True,
        "80ccd_1b": True
    }
}

# -------------------------
# FUNCTIONS
# -------------------------

def compute_hra_exemption(basic, da, hra_received, rent_paid, is_metro):
    salary_for_hra = basic + da
    pct = RULES["hra_metro_pct"] if is_metro else RULES["hra_nonmetro_pct"]
    limit_pct = pct * salary_for_hra
    rent_minus_10pct = max(0, rent_paid - 0.10 * salary_for_hra)
    hra_exemption = min(hra_received, limit_pct, rent_minus_10pct)
    return int(max(0, round(hra_exemption)))


def tax_from_slabs(taxable_income, slabs):
    tax = 0
    previous = 0

    for slab in slabs:
        upto = slab["upto"]
        rate = slab["rate"]

        if taxable_income <= previous:
            break

        taxable_here = min(taxable_income, upto) - previous

        if taxable_here > 0:
            tax += taxable_here * rate

        previous = upto

    tax = tax * (1 + RULES["cess_rate"])
    return int(round(tax))


def compute_old_regime_tax(gross_income, exemptions_sum, deductions):
    taxable = gross_income - exemptions_sum

    taxable -= deductions.get("standard_deduction", 0)
    taxable -= deductions.get("80c", 0)
    taxable -= deductions.get("80ccd_1b", 0)
    taxable -= deductions.get("80d", 0)
    taxable -= deductions.get("80e", 0)
    taxable -= deductions.get("home_loan_interest", 0)

    taxable = max(0, round(taxable))
    tax = tax_from_slabs(taxable, RULES["tax_slabs_old"])

    return int(tax), int(taxable)


def compute_new_regime_tax(gross_income, exemptions_sum, allowed_deductions):
    taxable = gross_income - exemptions_sum

    if RULES["new_regime_allowed"]["standard_deduction"]:
        taxable -= allowed_deductions.get("standard_deduction", 0)

    if RULES["new_regime_allowed"]["80ccd_1b"]:
        taxable -= allowed_deductions.get("80ccd_1b", 0)

    taxable = max(0, round(taxable))
    tax = tax_from_slabs(taxable, RULES["tax_slabs_new"])

    return int(tax), int(taxable)


def estimate_marginal_rate_old(taxable_income):
    for slab in RULES["tax_slabs_old"]:
        if taxable_income <= slab["upto"]:
            return slab["rate"]
    return RULES["tax_slabs_old"][-1]["rate"]


def marginal_with_cess(taxable_income):
    base = estimate_marginal_rate_old(taxable_income)
    return base * (1 + RULES["cess_rate"])


def money(x):
    return f"₹{int(round(x)):,}"


# -------------------------
# UI
# -------------------------

st.title("MBA Tax Optimizer — Expanded Questionnaire")
st.caption(f"FY {RULES['fy']}")

col_left, col_right = st.columns([2, 3])

with col_left:
    st.header("Section A — Compensation Structure")

    fixed_pay = st.number_input("Fixed Pay", value=2400000)
    employer_pf_included = st.checkbox("Employer PF is part of Fixed Pay", value=True)

    joining_bonus = st.number_input("Joining Bonus", value=200000)
    relocation_bonus = st.number_input("Relocation Bonus (Lump Sum)", value=150000)
    performance_bonus = st.number_input("Non-Assured / Performance Bonus", value=550000)

    gross_income = (
        fixed_pay
        + joining_bonus
        + relocation_bonus
        + performance_bonus
    )

    st.info(f"Calculated Gross Annual Income = {money(gross_income)}")

    st.header("Section B — Accommodation")

    is_metro = st.radio("City Type", ["Metro", "Non-Metro"]) == "Metro"
    lives_rented = st.radio("Live in rented house?", ["Yes", "No"]) == "Yes"

    rent_annual = 0
    if lives_rented:
        rent_annual = st.number_input("Annual Rent Paid", value=240000)

    st.header("Section C — Salary Breakdown")

    basic = st.number_input("Basic", value=720000)
    da = st.number_input("DA", value=0)
    hra = st.number_input("HRA", value=360000)
    special_allowance = st.number_input("Special Allowance", value=1181600)

    employer_pf = st.number_input("Employer PF contribution", value=86400)
    employee_pf = st.number_input(
        "Employee PF contribution (enter 0 if you are entering EPF in 80C below)",
        value=0
    )

    st.header("Allowances")
    internet_allowance = st.number_input("Internet", value=12000)
    phone_allowance = st.number_input("Phone", value=0)
    conveyance_allowance = st.number_input("Conveyance", value=0)
    meal_voucher = st.number_input("Meal Voucher", value=0)
    lta_claimed = st.number_input("LTA", value=40000)

with col_right:
    st.header("Section D — 80C Breakup")

    epf = st.number_input("EPF (Employee PF)", value=86400)
    ppf = st.number_input("PPF", value=0)
    elss = st.number_input("ELSS", value=0)
    life_ins = st.number_input("Life Insurance Premium", value=0)
    tax_fd = st.number_input("Tax Saving FD", value=0)
    principal_home = st.number_input("Home Loan Principal", value=0)
    sukanya = st.number_input("Sukanya / Other", value=0)

    invest_80c = epf + ppf + elss + life_ins + tax_fd + principal_home + sukanya

    st.header("Other Deductions")

    nps_employee = st.number_input("NPS 80CCD(1B)", value=50000)
    health_insurance = st.number_input("Health Insurance 80D", value=25000)
    education_loan_interest = st.number_input("Education Loan Interest 80E", value=0)
    home_loan_interest = st.number_input("Home Loan Interest", value=0)

# -------------------------
# ANALYSIS
# -------------------------

if st.button("Run full analysis"):

    hra_exempt = compute_hra_exemption(basic, da, hra, rent_annual, is_metro) if lives_rented else 0

    reimbursements = internet_allowance + phone_allowance + conveyance_allowance + meal_voucher
    exemptions_old = hra_exempt + reimbursements + lta_claimed

    deductions = {
        "standard_deduction": RULES["standard_deduction"],
        "80c": min(invest_80c, RULES["80c_limit"]),
        "80ccd_1b": min(nps_employee, RULES["80ccd_1b_limit"]),
        "80d": health_insurance,
        "80e": education_loan_interest,
        "home_loan_interest": home_loan_interest
    }

    # Main tax calculations
    old_tax, old_taxable = compute_old_regime_tax(gross_income, exemptions_old, deductions)

    allowed_new = {
        "standard_deduction": RULES["standard_deduction"],
        "80ccd_1b": min(nps_employee, RULES["80ccd_1b_limit"])
    }

    new_tax, new_taxable = compute_new_regime_tax(gross_income, 0, allowed_new)

    # One-time tax calculations — OLD
    old_tax_without_joining, _ = compute_old_regime_tax(gross_income - joining_bonus, exemptions_old, deductions)
    joining_bonus_tax_old = old_tax - old_tax_without_joining

    old_tax_without_relocation, _ = compute_old_regime_tax(gross_income - relocation_bonus, exemptions_old, deductions)
    relocation_bonus_tax_old = old_tax - old_tax_without_relocation

    old_tax_without_perf, _ = compute_old_regime_tax(gross_income - performance_bonus, exemptions_old, deductions)
    performance_bonus_tax_old = old_tax - old_tax_without_perf

    # One-time tax calculations — NEW
    new_tax_without_joining, _ = compute_new_regime_tax(gross_income - joining_bonus, 0, allowed_new)
    joining_bonus_tax_new = new_tax - new_tax_without_joining

    new_tax_without_relocation, _ = compute_new_regime_tax(gross_income - relocation_bonus, 0, allowed_new)
    relocation_bonus_tax_new = new_tax - new_tax_without_relocation

    new_tax_without_perf, _ = compute_new_regime_tax(gross_income - performance_bonus, 0, allowed_new)
    performance_bonus_tax_new = new_tax - new_tax_without_perf

    # Monthly TDS after removing one-time taxes
    monthly_tax_pool_old = max(0, old_tax - joining_bonus_tax_old - relocation_bonus_tax_old - performance_bonus_tax_old)
    monthly_tax_pool_new = max(0, new_tax - joining_bonus_tax_new - relocation_bonus_tax_new - performance_bonus_tax_new)

    monthly_tds_old = int(round(monthly_tax_pool_old / 12))
    monthly_tds_new = int(round(monthly_tax_pool_new / 12))

    # Employee PF for in-hand:
    # If user enters it in salary breakup, use that.
    # If they keep it 0 there, use EPF from 80C breakup.
    employee_pf_for_inhand = employee_pf if employee_pf > 0 else epf
    employee_pf_monthly = int(round(employee_pf_for_inhand / 12))

    # Monthly fixed salary pool:
    # If employer PF is part of fixed pay, subtract it from monthly fixed pay.
    monthly_fixed_available = int(round(fixed_pay / 12))
    if employer_pf_included:
        monthly_fixed_available -= int(round(employer_pf / 12))

    # Monthly in-hand
    monthly_in_hand_old = monthly_fixed_available - employee_pf_monthly - monthly_tds_old
    monthly_in_hand_new = monthly_fixed_available - employee_pf_monthly - monthly_tds_new

    annual_in_hand_old_excluding_one_time = monthly_in_hand_old * 12
    annual_in_hand_new_excluding_one_time = monthly_in_hand_new * 12

    # Net receipts for one-time payouts
    joining_bonus_net_old = joining_bonus - joining_bonus_tax_old
    relocation_bonus_net_old = relocation_bonus - relocation_bonus_tax_old
    performance_bonus_net_old = performance_bonus - performance_bonus_tax_old

    joining_bonus_net_new = joining_bonus - joining_bonus_tax_new
    relocation_bonus_net_new = relocation_bonus - relocation_bonus_tax_new
    performance_bonus_net_new = performance_bonus - performance_bonus_tax_new

    # -------------------------
    # MAIN SUMMARY TABLE
    # -------------------------

    summary = pd.DataFrame({
        "Component": [
            "Gross Annual Income",

            "Exemptions (Old only)",
            "  ↳ HRA Exemption",
            "  ↳ Internet Reimbursement",
            "  ↳ Phone Reimbursement",
            "  ↳ Conveyance",
            "  ↳ Meal Voucher",
            "  ↳ LTA",

            "Deductions",
            "  ↳ Standard Deduction",
            "  ↳ 80C",
            "  ↳ NPS 80CCD(1B)",
            "  ↳ Health Insurance 80D",
            "  ↳ Education Loan Interest 80E",
            "  ↳ Home Loan Interest",

            "Taxable Income",
            "Estimated Tax",

            "Tax on Joining Bonus (one-time)",
            "Tax on Relocation Bonus (one-time)",
            "Tax on Non-Assured / Performance Bonus (one-time)",

            "Monthly TDS (excluding one-time taxes)",
            "Monthly In-Hand Salary",
            "Annual In-Hand (excluding one-time payouts)"
        ],

        "Old Regime": [
            int(round(gross_income)),

            int(round(exemptions_old)),
            int(round(hra_exempt)),
            int(round(internet_allowance)),
            int(round(phone_allowance)),
            int(round(conveyance_allowance)),
            int(round(meal_voucher)),
            int(round(lta_claimed)),

            int(round(
                deductions["standard_deduction"]
                + deductions["80c"]
                + deductions["80ccd_1b"]
                + deductions["80d"]
                + deductions["80e"]
                + deductions["home_loan_interest"]
            )),

            int(round(deductions["standard_deduction"])),
            int(round(deductions["80c"])),
            int(round(deductions["80ccd_1b"])),
            int(round(deductions["80d"])),
            int(round(deductions["80e"])),
            int(round(deductions["home_loan_interest"])),

            int(round(old_taxable)),
            int(round(old_tax)),

            int(round(joining_bonus_tax_old)),
            int(round(relocation_bonus_tax_old)),
            int(round(performance_bonus_tax_old)),

            int(round(monthly_tds_old)),
            int(round(monthly_in_hand_old)),
            int(round(annual_in_hand_old_excluding_one_time))
        ],

        "New Regime": [
            int(round(gross_income)),

            0,
            0,
            0,
            0,
            0,
            0,
            0,

            int(round(
                allowed_new["standard_deduction"] + allowed_new["80ccd_1b"]
            )),

            int(round(allowed_new["standard_deduction"])),
            0,
            int(round(allowed_new["80ccd_1b"])),
            0,
            0,
            0,

            int(round(new_taxable)),
            int(round(new_tax)),

            int(round(joining_bonus_tax_new)),
            int(round(relocation_bonus_tax_new)),
            int(round(performance_bonus_tax_new)),

            int(round(monthly_tds_new)),
            int(round(monthly_in_hand_new)),
            int(round(annual_in_hand_new_excluding_one_time))
        ]
    })

    st.subheader("Old vs New")
    st.table(summary)
    st.caption("Rows show detailed breakup of exemptions, deductions, one-time taxes, and monthly in-hand logic.")

    # -------------------------
    # ONE-TIME PAYOUT TABLE
    # -------------------------

    st.subheader("One-Time Payouts (Net After Tax)")

    one_time_df = pd.DataFrame({
        "Component": [
            "Joining Bonus",
            "Relocation Bonus",
            "Non-Assured / Performance Bonus"
        ],
        "Gross Amount": [
            int(round(joining_bonus)),
            int(round(relocation_bonus)),
            int(round(performance_bonus))
        ],
        "Old Tax Deducted": [
            int(round(joining_bonus_tax_old)),
            int(round(relocation_bonus_tax_old)),
            int(round(performance_bonus_tax_old))
        ],
        "Old Net Received": [
            int(round(joining_bonus_net_old)),
            int(round(relocation_bonus_net_old)),
            int(round(performance_bonus_net_old))
        ],
        "New Tax Deducted": [
            int(round(joining_bonus_tax_new)),
            int(round(relocation_bonus_tax_new)),
            int(round(performance_bonus_tax_new))
        ],
        "New Net Received": [
            int(round(joining_bonus_net_new)),
            int(round(relocation_bonus_net_new)),
            int(round(performance_bonus_net_new))
        ]
    })

    st.table(one_time_df)

    st.caption(f"Employee PF used for in-hand calculation: {money(employee_pf_for_inhand)}")
    if employer_pf_included:
        st.caption(f"Employer PF removed from monthly fixed pay: {money(employer_pf)}")

    # -------------------------
    # RECOMMENDATIONS
    # -------------------------

    st.subheader("Recommendations")

    marginal = marginal_with_cess(old_taxable)

    if invest_80c < RULES["80c_limit"]:
        gap = RULES["80c_limit"] - invest_80c
        est_save = int(round(gap * marginal))
        st.write(f"Invest additional {money(gap)} in 80C to save approx {money(est_save)} tax")

    if nps_employee < RULES["80ccd_1b_limit"]:
        gap = RULES["80ccd_1b_limit"] - nps_employee
        est_save = int(round(gap * marginal))
        st.write(f"Invest additional {money(gap)} in NPS to save approx {money(est_save)} tax")

    if lives_rented and special_allowance > 0:
        st.write("Consider restructuring part of Special Allowance into HRA")

    if reimbursements > 0:
        st.write("Convert allowances into proof-based reimbursements if company policy allows")

    if old_tax < new_tax:
        st.success(f"Old Regime Better — Save {money(new_tax - old_tax)}")
    else:
        st.success(f"New Regime Better — Save {money(old_tax - new_tax)}")
