# -*- coding: utf-8 -*-
"""
ACT / 堪培拉房产测算骨架。改参数即可复用。
用法：改下面的 ASSUMPTIONS 与 SCENARIOS，然后 python model_template.py
"""

# ---------------- 工具函数 ----------------

def pmt(principal, annual_rate, years=30):
    """等额本息月供"""
    r = annual_rate / 12.0
    n = years * 12
    return principal * r / (1 - (1 + r) ** (-n))


def duty_oo(p):
    """ACT 印花税 — 自住税率表"""
    if p <= 260000: return p * 0.0028
    if p <= 300000: return 728 + (p - 260000) * 0.022
    if p <= 500000: return 1608 + (p - 300000) * 0.034
    if p <= 750000: return 8408 + (p - 500000) * 0.0432
    if p <= 1000000: return 19208 + (p - 750000) * 0.059
    if p <= 1455000: return 33958 + (p - 1000000) * 0.064
    return p * 0.0454


def duty_inv(p):
    """ACT 印花税 — 投资者（非自住）税率表"""
    if p <= 200000: return p * 0.012
    if p <= 300000: return 2400 + (p - 200000) * 0.022
    if p <= 500000: return 4600 + (p - 300000) * 0.034
    if p <= 750000: return 11400 + (p - 500000) * 0.0432
    if p <= 1000000: return 22200 + (p - 750000) * 0.059
    if p <= 1455000: return 36950 + (p - 1000000) * 0.064
    return p * 0.0454


def land_tax_act(auv, fixed=1778.0):
    """ACT 土地税。单元传 unit entitlement 分摊后的 AUV。自住豁免，不调用本函数。"""
    if auv <= 150000: v = auv * 0.0054
    elif auv <= 275000: v = 810 + (auv - 150000) * 0.0064
    elif auv <= 1000000: v = 1610 + (auv - 275000) * 0.0124
    elif auv <= 2000000: v = 10600 + (auv - 1000000) * 0.0125
    else: v = 23100 + (auv - 2000000) * 0.0126
    return fixed + v


def ann(buy, val, years):
    """年化收益率"""
    return (val / buy) ** (1.0 / years) - 1.0


# ---------------- 假设（按需修改）----------------
LVR           = 0.80
RATE          = 0.0620     # 投资者 P&I 浮动，2026-09 区间 5.89%–6.59%
TERM          = 30
VACANCY_WEEKS = 2
MGMT_RATE     = 0.088      # 8% + GST
STRATA        = 5000.0     # 物业费/年
COUNCIL_RATES = 1600.0     # 市政费/年
WATER         = 450.0
INSURANCE     = 550.0      # 房东险（自住改物品险约 350）
REPAIRS       = 1200.0
DEPRECIATION  = 8000.0     # 非现金，需 QS 报告
MARGINAL_TAX  = 0.30
RENT_GROWTH   = 0.020


def invest_model(price, weekly_rent, rate=RATE, lvr=LVR, land_tax=3228.0):
    """投资情形：年度现金流"""
    collected = weekly_rent * (52 - VACANCY_WEEKS)
    loan      = price * lvr
    equity    = price - loan
    duty      = duty_inv(price)

    mgmt  = collected * MGMT_RATE
    opex  = STRATA + COUNCIL_RATES + land_tax + WATER + INSURANCE + REPAIRS + mgmt
    noi   = collected - opex

    m     = pmt(loan, rate, TERM)
    repay = m * 12
    bal, interest = loan, 0.0
    for _ in range(12):
        i = bal * rate / 12
        interest += i
        bal -= (m - i)

    pretax = noi - repay
    tax_ben = max(0.0, -pretax + DEPRECIATION) * MARGINAL_TAX
    return dict(
        price=price, loan=loan, equity=equity, duty=duty, cash_in=equity + duty,
        collected=collected, opex=opex, noi=noi, monthly=m, repay=repay,
        gross_yield=weekly_rent * 52 / price, net_yield=noi / price,
        pretax=pretax, pretax_wk=pretax / 52,
        tax_benefit=tax_ben, aftertax=pretax + tax_ben,
        aftertax_wk=(pretax + tax_ben) / 52,
        cash_on_cash=(pretax + tax_ben) / (equity + duty),
    )


def owner_occ_model(price, weekly_rent_market, years, strata=None, rates_q=None,
                    water=None, insure=350.0, loan=None, rate=0.0):
    """自住情形：含机会收益（省下的租金）与免土地税"""
    strata = strata if strata is not None else STRATA
    rates_q = rates_q if rates_q is not None else COUNCIL_RATES
    water = water if water is not None else WATER

    hold_yr = strata + rates_q + water + insure      # 自住免土地税
    hold_total = hold_yr * years
    rent_saved = weekly_rent_market * 52 * years
    interest = (loan or 0.0) * rate * years
    return dict(hold_per_year=hold_yr, hold_total=hold_total,
                rent_saved=rent_saved, interest_total=interest,
                net=lambda value: (value - price) - hold_total + rent_saved - interest)


if __name__ == "__main__":
    r = invest_model(900000, 800)
    print("投资基准：毛收益率 %.2f%%  税前 %.0f/年  税后 %.0f/年"
          % (r["gross_yield"] * 100, r["pretax"], r["aftertax"]))
