# app.py
# MBA Tax Optimizer - Updated with expanded salary breakup, 80E, itemized 80C, reimbursements, LTA
# Paste this file into your GitHub repo replacing the previous app.py.

import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO
from datetime import date

st.set_page_config(page_title="MBA Tax Optimizer", layout="wide")

# -------------------------
# EDITABLE RULES / PARAMETERS (change these when Budget rules change)
# -------------------------
RULES = {
    "fy": "2025-26",
    "standard_deduction": 50000,
    "80c_limit": 150000,
    "80ccd_1b_limit": 50000,
    "hra_metro_pct": 0.50,
    "hra_nonmetro_pct": 0.40,
    "cess_rate": 0.04,
    # tax slabs (example) - edit these numbers if government changes slabs
    "tax_slabs_old": [
        {"upto": 250000, "rate": 0.0},
        {"upto": 500000, "rate": 0.05},
        {"upto": 1000000, "rate": 0.20},
        {"upto": 999999999, "rate": 0.30}
    ],
    # Example new regime slab structure (editable)
    "tax_slabs_new": [
        {"upto": 300000, "rate": 0.0},
        {"upto": 600000, "rate": 0.05},
        {"upto": 900000, "rate": 0.10},
        {"upto": 1200000, "rate": 0.15},
        {"upto": 1500000, "rate": 0.20},
        {"upto": 999999999, "rate": 0.30}
    ],
    # Which deductions remain allowed in new regime (toggle here)
    "new_regime_allowed": {
        "standard_deduction": False,
        "80ccd_1b": True   # many budgets allow/exclude; keep editable
    },
    "allowed_reimbursements": ["internet", "phone", "books", "conveyance", "meal_voucher", "other_reimbursement"]
}

# -------------------------
# Helper / Tax functions (defined early)
# -------------------------
def compute_hra_exemption(basic, da, hra_received, rent_paid, is_metro):
    salary_for_hra = basic + da
    pct = RULES["hra_metro_pct"] if is_metro else RULES["hra_nonmetro_pct"]
    limit_pct = pct * salary_for_hra
    rent_minus_10pct = max(0, rent_paid - 0.10 * salary_for_hra)
    hra_exemption = min(hra_received, limit_pct, rent_minus_10pct)
    return round(max(0, hra_exemption), 0)

def tax_from_slabs(taxable_income, slabs):
    tax = 0.0
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
    return round(tax, 0)

def compute_old_regime_tax(gross_income, exemptions_sum, deductions):
    """
    deductions: dict with keys standard_deduction, 80c, 80ccd_1b, 80d, 80e, home_loan_interest, 80tta
    exemptions_sum: total exempt amounts (HRA exempt, LTA exempt, reimbursements exempt etc.)
    """
    taxable = gross_income - exemptions_sum
    taxable -= deductions.get("standard_deduction", 0)
    taxable -= deductions.get("80c", 0)
    taxable -= deductions.get("80ccd_1b", 0)
    taxable -= deductions.get("80d", 0)
    taxable -= deductions.get("80e", 0)  # education loan interest
    taxable -= deductions.get("home_loan_interest", 0)
    # 80TTA is a deduction up to a limit on interest income (applies separately)
    taxable = max(0, round(taxable))
    tax = tax_from_slabs(taxable, RULES["tax_slabs_old"])
    return int(tax), int(taxable)

def compute_new_regime_tax(gross_income, exemptions_sum, allowed_deductions):
    """
    New regime: only allow some deductions if configured in RULES["new_regime_allowed"].
    allowed_deductions: dict; we will filter via RULES settings.
    """
    taxable = gross_income - exemptions_sum
    # apply only allowed ones
    if RULES["new_regime_allowed"].get("standard_deduction", False):
        taxable -= allowed_deductions.get("standard_deduction", 0)
    if RULES["new_regime_allowed"].get("80ccd_1b", False):
        taxable -= allowed_deductions.get("80ccd_1b", 0)
    taxable = max(0, round(taxable))
    tax = tax_from_slabs(taxable, RULES["tax_slabs_new"])
    return int(tax), int(taxable)

def estimate_marginal_rate_old(taxable_income):
    """Return marginal (nominal) tax rate (no cess) for old slabs for quick estimates."""
    previous = 0
    for slab in RULES["tax_slabs_old"]:
        upto = slab["upto"]
        rate = slab["rate"]
        if taxable_income <= upto:
            return rate
        previous = upto
    return RULES["tax_slabs_old"][-1]["rate"]

def marginal_tax_rate_for_income_old(taxable_income):
    base = estimate_marginal_rate_old(taxable_income)
    return base * (1 + RULES["cess_rate"])

def generate_hr_email(name="[Your Name]", emp_id="[ID]", changes=None):
    if changes is None:
        changes = []
    lines = []
    lines.append(f"Subject: Request to review salary structure for FY {RULES['fy']}")
    lines.append("")
    lines.append(f"Hi HR Team,")
    lines.append("")
    lines.append(f"I would like to request a review of my salary structure for the upcoming financial year to optimize tax efficiency while remaining aligned with company policy.")
    lines.append("")
    lines.append("Proposed items for discussion:")
    for c in changes:
        lines.append(f"- {c['what']}: {c.get('why','')}")
    lines.append("")
    lines.append("Purpose: These changes help align my in-hand salary and retirement savings while being fully compliant with tax rules. Happy to meet and discuss feasibility or provide required documents.")
    lines.append("")
    lines.append("Thanks & regards,")
    lines.append(name)
    lines.append(emp_id)
    return "\n".join(lines)

# -------------------------
# Small UI helpers
# -------------------------
def money(x): return f"₹{int(x):,}"

# -------------------------
# UI: page content
# -------------------------
st.title("MBA Tax Optimizer — Expanded Questionnaire")
st.caption(f"FY: {RULES['fy']}  •  Edit constants at top of app.py to change limits/slabs")

with st.expander("Quick guide — what to enter (short)"):
    st.write("""
    - If you don't know exact breakup, give your best estimate for Basic (typical 35%-45% of CTC).
    - Mark allowances as 'reimbursement (proof-based)' only if your company reimburses on submitting bills.
    - 80C: you can either enter a total or itemize typical components (EPF, PPF, ELSS, Insurance, principal repayment).
    - 80E: enter interest paid on education loan this FY (full interest available as deduction for a limited number of years).
    """)

# Layout: left = questionnaire, right = results
col_left, col_right = st.columns([2,3])

with col_left:
    st.header("Section A — Personal & Accommodation")
    age = st.selectbox("Age bracket", ["<60", "60-80", ">80"])
    is_senior = (age != "<60")
    city = st.text_input("City (type a city name or write 'metro'/'non-metro')", value="metro")
    is_metro = st.radio("City type", ["Metro", "Non-Metro"]) == "Metro"
    lives_rented = st.radio("Do you live in rented accommodation?", ["Yes","No"]) == "Yes"
    rent_annual = 0
    if lives_rented:
        rent_annual = st.number_input("Annual rent paid (₹)", min_value=0, value=240000, step=1000)

    st.markdown("---")
    st.header("Section B — Salary breakup (annual amounts)")
    ctc = st.number_input("Total CTC (₹)", min_value=0, value=1800000, step=10000)
    st.info("If you don't have exact breakup, give best estimate; Basic is typically 35-45% of CTC for many companies.")
    basic = st.number_input("Basic salary (₹)", min_value=0, value=720000, step=10000)
    da = st.number_input("Dearness Allowance (DA) (₹) — if none put 0", min_value=0, value=0, step=1000)
    hra = st.number_input("HRA received (₹)", min_value=0, value=288000, step=1000)
    special_allowance = st.number_input("Special allowance (taxable) (₹)", min_value=0, value=200000, step=1000)
    variable_pay = st.number_input("Bonus / variable components (₹)", min_value=0, value=200000, step=1000)
    employer_pf = st.number_input("Employer PF contribution (₹)", min_value=0, value=86400, step=1000)
    employee_pf = st.number_input("Employee PF contribution (₹)", min_value=0, value=86400, step=1000)
    employer_nps = st.number_input("Employer NPS contribution (₹) if any", min_value=0, value=60000, step=1000)
    gratuity = st.number_input("Gratuity (if defined) (₹)", min_value=0, value=0, step=1000)

    st.markdown("### Company allowances / reimbursements (enter amounts even if 0)")
    st.info("Mark 'Proof-based' only if your company reimburses against bills (these are generally tax-exempt).")
    internet_allowance = st.number_input("Internet allowance (₹)", min_value=0, value=0, step=500)
    internet_proof = st.checkbox("Internet allowance: proof-based reimbursement (exempt if checked)", value=False)
    phone_allowance = st.number_input("Phone allowance (₹)", min_value=0, value=0, step=500)
    phone_proof = st.checkbox("Phone allowance: proof-based reimbursement (exempt if checked)", value=False)
    lta_claimed = st.number_input("LTA claimed this FY (₹) — if any", min_value=0, value=0, step=1000)
    lta_proof = st.checkbox("Have supporting travel proof for LTA (exempt if checked)", value=False)
    conveyance_allowance = st.number_input("Conveyance allowance (₹)", min_value=0, value=0, step=500)
    conveyance_proof = st.checkbox("Conveyance: proof-based reimbursement (exempt if checked)", value=False)
    meal_voucher = st.number_input("Meal voucher / canteen (₹)", min_value=0, value=0, step=500)
    meal_proof = st.checkbox("Meal vouchers provided as tax-exempt (e.g., Sodexo) (check if applies)", value=False)
    other_reimb = st.number_input("Other reimbursements (₹)", min_value=0, value=0, step=500)
    other_reimb_proof = st.checkbox("Other reimbursements proof-based (exempt if checked)", value=False)

    st.markdown("---")
    st.header("Section C — Investments & Deductions (80C, 80D, 80E etc.)")
    st.write("You can either enter a total 80C amount or itemize components (recommended).")
    use_itemized_80c = st.radio("80C input mode", ["Enter total 80C", "Itemize 80C components"]) == "Itemize 80C components"
    if not use_itemized_80c:
        invest_80c = st.number_input("Total 80C investments this FY (₹)", min_value=0, value=150000, step=1000)
    else:
        epf = st.number_input("Employee PF (EPF) in 80C (₹)", min_value=0, value=86400, step=1000)
        ppf = st.number_input("PPF (₹)", min_value=0, value=0, step=1000)
        elss = st.number_input("ELSS (₹)", min_value=0, value=0, step=1000)
        life_ins = st.number_input("Life insurance premium (₹)", min_value=0, value=0, step=1000)
        tax_fd = st.number_input("Tax saving FD (5-year FD) (₹)", min_value=0, value=0, step=1000)
        principal_home_loan = st.number_input("Principal repaid on home loan (₹)", min_value=0, value=0, step=1000)
        sukanya = st.number_input("Sukanya Samriddhi / other (₹)", min_value=0, value=0, step=1000)
        invest_80c = epf + ppf + elss + life_ins + tax_fd + principal_home_loan + sukanya

    nps_employee = st.number_input("NPS (employee contribution) this FY (₹)", min_value=0, value=50000, step=1000)
    health_insurance = st.number_input("Health insurance premium claimed under 80D (₹)", min_value=0, value=25000, step=1000)
    education_loan_interest = st.number_input("Interest paid on education loan (80E) this FY (₹)", min_value=0, value=0, step=1000)
    home_loan_interest = st.number_input("Home loan interest (Section 24) this FY (₹)", min_value=0, value=0, step=1000)
    savings_interest = st.number_input("Interest on savings account (for 80TTA) (₹)", min_value=0, value=0, step=100)
    donations_80g = st.number_input("Donations (80G) this FY (₹)", min_value=0, value=0, step=1000)

    st.markdown("---")
    st.header("Section D — Preferences & HR")
    willing_restructure = st.radio("Willing to ask HR for restructuring?", ["Yes","No"]) == "Yes"
    hr_flexibility = st.selectbox("HR flexibility (your guess)", ["High","Medium","Low"])
    priority = st.selectbox("Priority", ["Maximize immediate take-home", "Maximize tax savings", "Balanced"])
    st.markdown("---")
    st.write("Optional: add notes / spouse income / join-date if needed")
    spouse_income = st.number_input("Spouse annual taxable income (₹) — optional", min_value=0, value=0, step=1000)
    joined_mid_year = st.checkbox("Joined employer mid-year (affects prorated calculations)", value=False)

with col_right:
    st.header("Results & Suggestions")
    if st.button("Run full analysis"):
        # Compute exemptions from reimbursements + HRA + LTA
        hra_exempt = compute_hra_exemption(basic, da, hra, rent_annual, is_metro) if lives_rented else 0
        lta_exempt = lta_claimed if (lta_claimed > 0 and lta_proof) else 0

        reimb_exempt = 0
        reimb_notes = []
        for amt, proof, name in [
            (internet_allowance, internet_proof, "Internet"),
            (phone_allowance, phone_proof, "Phone"),
            (conveyance_allowance, conveyance_proof, "Conveyance"),
            (meal_voucher, meal_proof, "Meal vouchers"),
            (other_reimb, other_reimb_proof, "Other reimbursements")
        ]:
            if amt > 0 and proof:
                reimb_exempt += amt
                reimb_notes.append(f"{name}: {money(amt)} (proof-based)")
            elif amt > 0 and not proof:
                reimb_notes.append(f"{name}: {money(amt)} (taxable)")

        exemptions_sum = hra_exempt + lta_exempt + reimb_exempt

        # Build deductions dict
        deductions = {
            "standard_deduction": RULES["standard_deduction"],
            "80c": min(invest_80c, RULES["80c_limit"]) if invest_80c is not None else 0,
            "80ccd_1b": min(nps_employee, RULES["80ccd_1b_limit"]),
            "80d": health_insurance,
            "80e": education_loan_interest,
            "home_loan_interest": home_loan_interest,
            "80tta": min(savings_interest, 10000)  # typical 80TTA limit (editable if needed)
        }

        gross_income = ctc  # simple approach: treat CTC as gross for this MVP

        old_tax, old_taxable = compute_old_regime_tax(gross_income, exemptions_sum, deductions)

        allowed_new = {}
        if RULES["new_regime_allowed"].get("standard_deduction", False):
            allowed_new["standard_deduction"] = RULES["standard_deduction"]
        if RULES["new_regime_allowed"].get("80ccd_1b", False):
            allowed_new["80ccd_1b"] = min(nps_employee, RULES["80ccd_1b_limit"])

        new_tax, new_taxable = compute_new_regime_tax(gross_income, exemptions_sum, allowed_new)

        # Summary table
        summary = pd.DataFrame({
            "Component": ["Gross Income", "Exemptions (HRA+LTA+reimb)", "Deductions applied (sum)", "Taxable Income", "Estimated Tax (annual)"],
            "Old Regime": [gross_income, int(exemptions_sum), int(deductions["standard_deduction"] + deductions["80c"] + deductions["80ccd_1b"] + deductions["80d"] + deductions["80e"] + deductions["home_loan_interest"]), old_taxable, old_tax],
            "New Regime": [gross_income, int(exemptions_sum), int(allowed_new.get("standard_deduction",0) + allowed_new.get("80ccd_1b",0)), new_taxable, new_tax]
        })

        st.subheader("Side-by-side: Old vs New regime")
        st.table(summary.set_index("Component"))

        # Pick best regime
        if old_tax < new_tax:
            st.success(f"Old regime is better here — Estimated annual tax: {money(old_tax)} vs New regime: {money(new_tax)}")
        elif new_tax < old_tax:
            st.success(f"New regime is better here — Estimated annual tax: {money(new_tax)} vs Old regime: {money(old_tax)}")
        else:
            st.info(f"Both regimes give similar tax: {money(old_tax)}")

        # Show breakdown of exemptions
        st.markdown("### Exemptions & Proofs")
        st.write(f"HRA exemption: {money(hra_exempt)} {'(requires rent receipts)' if lives_rented else ''}")
        st.write(f"LTA exempt: {money(lta_exempt)} {'(proof provided)' if lta_proof else ''}")
        if reimb_notes:
            st.write("Reimbursements details:")
            for r in reimb_notes:
                st.write("-", r)
        else:
            st.write("No proof-based reimbursements marked.")

        # Missed deductions: give opportunities
        st.markdown("### Missed / Partially used deductions (quick wins)")
        missed = []
        if deductions["80c"] < RULES["80c_limit"]:
            missing_80c = RULES["80c_limit"] - deductions["80c"]
            missed.append({"Deduction":"80C (investments)", "Current":money(deductions["80c"]), "Max":money(RULES["80c_limit"]), "Opportunity (₹)": money(missing_80c)})
        if deductions["80ccd_1b"] < RULES["80ccd_1b_limit"]:
            missed.append({"Deduction":"80CCD(1B) - NPS (employee)", "Current":money(deductions["80ccd_1b"]), "Max":money(RULES["80ccd_1b_limit"]), "Opportunity (₹)": money(RULES["80ccd_1b_limit"] - deductions["80ccd_1b"])})
        if deductions["80d"] == 0:
            missed.append({"Deduction":"80D - Health insurance", "Current":"₹0", "Max":"Varies (typical ₹25k)", "Opportunity (₹)":"Buy family/policy if needed"})
        if deductions["80e"] == 0:
            missed.append({"Deduction":"80E - Education loan interest", "Current":"₹0", "Max":"No fixed cap (check eligibility)", "Opportunity (₹)":"Enter interest if applicable"})

        if missed:
            st.table(pd.DataFrame(missed))
        else:
            st.write("From common deductions checked here, you seem to be using most available options.")

        # Salary restructuring suggestions (heuristics)
        st.markdown("### Salary restructuring suggestions (safe & common ideas)")
        suggestions = []
        # 1) Move taxable special allowance -> HRA if renting and special_allowance exists
        if lives_rented and special_allowance > 0:
            # how much additional HRA could be useful? suggest up to special_allowance or cover rent gap
            rent_gap = max(0, rent_annual - hra_exempt)
            hypothetical_move = min(special_allowance, rent_gap)
            if hypothetical_move > 0:
                marginal = marginal_tax_rate_for_income_old(old_taxable)
                est_tax_saved = int(hypothetical_move * marginal)
                suggestions.append({
                    "Action": f"Request moving ₹{hypothetical_move:,} from Special Allowance → HRA",
                    "Estimated Tax Saving (₹/yr)": money(est_tax_saved),
                    "Notes": "Requires rent receipts & HR willingness; check take-home impact (PF/NPS base may change)"
                })

        # 2) Convert allowances to proof-based reimbursements
        reimb_candidates = []
        for amt, proof, name in [
            (internet_allowance, internet_proof, "Internet"),
            (phone_allowance, phone_proof, "Phone"),
            (conveyance_allowance, conveyance_proof, "Conveyance"),
            (meal_voucher, meal_proof, "Meal voucher")
        ]:
            if amt > 0 and not proof:
                reimb_candidates.append((amt, name))
        if reimb_candidates and hr_flexibility != "Low":
            total_possible = sum([x[0] for x in reimb_candidates])
            marginal = marginal_tax_rate_for_income_old(old_taxable)
            est_saved = int(total_possible * marginal)
            suggestions.append({
                "Action": f"Ask HR to convert {', '.join([n for (_,n) in reimb_candidates])} into proof-based reimbursements (total ₹{total_possible:,})",
                "Estimated Tax Saving (₹/yr)": money(est_saved),
                "Notes": "Requires company policy & bills"
            })

        # 3) Increase NPS (80CCD(1B)) if not maxed
        if nps_employee < RULES["80ccd_1b_limit"]:
            to_invest = RULES["80ccd_1b_limit"] - nps_employee
            marginal = marginal_tax_rate_for_income_old(old_taxable)
            est_saved = int(to_invest * marginal)
            suggestions.append({
                "Action": f"Invest additional ₹{to_invest:,} in NPS (80CCD(1B))",
                "Estimated Tax Saving (₹/yr)": money(est_saved),
                "Notes": "NPS is long-term; employer matching has different treatment"
            })

        # 4) Use 80C if not full
        if deductions["80c"] < RULES["80c_limit"]:
            to_invest = RULES["80c_limit"] - deductions["80c"]
            marginal = marginal_tax_rate_for_income_old(old_taxable)
            est_saved = int(to_invest * marginal)
            suggestions.append({
                "Action": f"Invest additional ₹{to_invest:,} under 80C (ELSS/PPF/Insurance/Principal)",
                "Estimated Tax Saving (₹/yr)": money(est_saved),
                "Notes": "Choose instruments based on liquidity & risk appetite"
            })

        if suggestions:
            st.table(pd.DataFrame(suggestions))
        else:
            st.write("No immediate safe restructuring suggestions were generated automatically. You may still have advanced options — discuss with a CA or HR.")

        # HR email / talking points
        st.markdown("### HR Email / Talking points (editable)")
        changes = []
        # include top 3 suggestions as talking points
        for s in suggestions[:3]:
            changes.append({"what": s["Action"], "why": s["Notes"]})
        hr_email = generate_hr_email(name="[Your Name]", emp_id="[Employee ID]", changes=changes)
        st.code(hr_email, language="markdown")
        st.download_button("Download HR email (txt)", hr_email, file_name="hr_email.txt")

        # Downloadable CSV summary
        out = {
            "fy": RULES["fy"],
            "ctc": ctc,
            "basic": basic,
            "hra_received": hra,
            "hra_exempt": int(hra_exempt),
            "lta_exempt": int(lta_exempt),
            "reimb_exempt_total": int(reimb_exempt),
            "old_taxable": old_taxable,
            "old_tax": old_tax,
            "new_taxable": new_taxable,
            "new_tax": new_tax
        }
        df_out = pd.DataFrame([out])
        csv = df_out.to_csv(index=False)
        st.download_button("Download analysis (CSV)", csv, file_name="tax_analysis.csv", mime="text/csv")

        # Notes & disclaimers
        st.markdown("#### Important notes & next steps")
        st.write("""
            - This tool is educational and not legal tax advice. For ESOPs, foreign income, expatriate taxation or aggressive tax planning consult a Chartered Accountant.
            - Suggestions assume truthful documentation (rent receipts, bills). Do not use forged receipts.
            - To update limits/slabs, edit the RULES section at the top of app.py and re-deploy.
        """)
        st.markdown("---")

st.caption("If anything errors when you run it, copy the error message here and I will debug with you.")
