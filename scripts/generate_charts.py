"""
Advanced Visual Chart Generator for Project Atlas Reports.
Generates diverse publication-quality visual formats using Matplotlib:
1. Donut Chart (Regional Market Share)
2. Trajectory Line Chart with Shaded Area / Confidence Band
3. 100% Stacked Bar Chart (Hardware vs Software vs Services Evolution)
4. Multi-Line Cost Erosion Trend (Ultrasonic vs Mechanical Metrology)
5. Radar / Spider Chart (Technology Multi-Attribute Evaluation: RO vs UV vs UF)
6. Grouped Side-by-Side Bar Chart (2024 Base vs 2030 Projected Capex)
7. Dual-Axis Line + Bar Chart (Market Volume vs YoY Growth Rate)
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def setup_chart_style():
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['axes.edgecolor'] = '#CBD5E1'
    plt.rcParams['axes.linewidth'] = 0.8


def generate_all_charts(output_dir: str = "data/charts"):
    os.makedirs(output_dir, exist_ok=True)
    setup_chart_style()
    chart_paths = {}

    # =========================================================================
    # 1. R-101: SMART WATER METER MARKET
    # =========================================================================
    
    # Chart 1A: Regional Share Donut
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=200)
    regions = ['Asia-Pacific (APAC)', 'North America', 'Europe', 'Rest of World']
    shares = [38.0, 31.1, 23.0, 7.9]
    colors_donut = ['#1E3A8A', '#2563EB', '#60A5FA', '#94A3B8']
    wedges, texts, autotexts = ax.pie(
        shares, labels=regions, autopct='%1.1f%%', startangle=140,
        colors=colors_donut, pctdistance=0.75,
        wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2)
    )
    for t in texts:
        t.set_fontsize(8)
        t.set_color('#1E293B')
    for at in autotexts:
        at.set_fontsize(8)
        at.set_weight('bold')
        at.set_color('white')
    ax.set_title('Global Smart Water Meter Market Share by Region (2024)\nScope: Hardware, Software & Services | Source: CMR R-101', fontsize=9, fontweight='bold', pad=10, color='#0F172A')
    plt.tight_layout()
    p1 = os.path.join(output_dir, "r101_regional_share.png")
    plt.savefig(p1)
    plt.close()
    chart_paths["r101_regional"] = p1

    # Chart 1B: Multi-Line Trajectory with Shaded Area (Global vs APAC 2024-2030)
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=200)
    years = np.array([2024, 2025, 2026, 2027, 2028, 2029, 2030])
    global_rev = 4.21 * ((1 + 0.112) ** (years - 2024))
    apac_rev = 1.60 * ((1 + 0.129) ** (years - 2024))
    
    ax.plot(years, global_rev, marker='o', linewidth=2.2, color='#1E3A8A', label='Global Total Market ($B)')
    ax.plot(years, apac_rev, marker='s', linewidth=2.0, color='#2563EB', linestyle='--', label='APAC Regional Spend ($B)')
    ax.fill_between(years, apac_rev, global_rev, color='#DBEAFE', alpha=0.5, label='Non-APAC Differential')
    
    ax.set_title('Market Trajectory & APAC Divergence (2024–2030)\nCompound Growth: 11.2% Global | Source: CMR R-101', fontsize=9, fontweight='bold', color='#0F172A')
    ax.set_ylabel('Revenue (USD Billions)', fontsize=8, color='#475569')
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.set_ylim(0, 9.5)
    ax.legend(fontsize=7.5, loc='upper left', framealpha=0.9)
    for y, g, a in zip(years, global_rev, apac_rev):
        if y in [2024, 2027, 2030]:
            ax.annotate(f'${g:.2f}B', (y, g), textcoords="offset points", xytext=(0, 6), ha='center', fontsize=7.5, fontweight='bold', color='#1E3A8A')
            ax.annotate(f'${a:.2f}B', (y, a), textcoords="offset points", xytext=(0, -12), ha='center', fontsize=7.5, fontweight='bold', color='#2563EB')
    plt.tight_layout()
    p2 = os.path.join(output_dir, "r101_market_growth.png")
    plt.savefig(p2)
    plt.close()
    chart_paths["r101_growth"] = p2

    # Chart 1C: 100% Stacked Bar Chart (Hardware vs Software vs Services Evolution)
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=200)
    periods = ['2024 (Base)', '2026 (Mid)', '2028 (Exp)', '2030 (Target)']
    hw_pct = np.array([58.2, 53.0, 48.5, 45.0])
    sw_pct = np.array([22.1, 26.5, 30.5, 34.2])
    svc_pct = np.array([19.7, 20.5, 21.0, 20.8])
    
    width = 0.52
    b1 = ax.bar(periods, hw_pct, width, label='Hardware Endpoints', color='#1E3A8A')
    b2 = ax.bar(periods, sw_pct, width, bottom=hw_pct, label='Cloud MDM & Analytics SaaS', color='#3B82F6')
    b3 = ax.bar(periods, svc_pct, width, bottom=hw_pct + sw_pct, label='Systems Integration & Services', color='#93C5FD')
    
    ax.set_title('Evolving Revenue Architecture Mix (2024–2030)\nTransition to Recurring High-Margin Software | Source: CMR R-101', fontsize=9, fontweight='bold', color='#0F172A')
    ax.set_ylabel('Share of Total Expenditure (%)', fontsize=8, color='#475569')
    ax.set_ylim(0, 105)
    ax.legend(fontsize=7.5, loc='lower right', framealpha=0.9)
    for idx, (h, s, v) in enumerate(zip(hw_pct, sw_pct, svc_pct)):
        ax.text(idx, h/2, f'{h:.1f}%', ha='center', va='center', color='white', fontweight='bold', fontsize=7.5)
        ax.text(idx, h + s/2, f'{s:.1f}%', ha='center', va='center', color='white', fontweight='bold', fontsize=7.5)
        ax.text(idx, h + s + v/2, f'{v:.1f}%', ha='center', va='center', color='#0F172A', fontweight='bold', fontsize=7.5)
    plt.tight_layout()
    p1c = os.path.join(output_dir, "r101_stack_evolution.png")
    plt.savefig(p1c)
    plt.close()
    chart_paths["r101_stack"] = p1c

    # =========================================================================
    # 2. R-102: AQUILA HARDWARE OUTLOOK
    # =========================================================================
    
    # Chart 2A: Horizontal Bar Chart of Hardware Revenue by Region
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=200)
    hw_regions = ['APAC (41.0%)', 'North America (30.5%)', 'Europe (21.5%)', 'RoW (7.0%)']
    hw_vals = [1.59, 1.18, 0.83, 0.27]
    colors_hw = ['#065F46', '#059669', '#34D399', '#9CA3AF']
    
    bars = ax.barh(hw_regions[::-1], hw_vals[::-1], color=colors_hw[::-1], height=0.52, edgecolor='#064E3B')
    ax.set_title('2024 Smart Water Meter Hardware Revenue by Region\nAMR / AMI Endpoints Only (USD 3.87B Total) | Source: Aquila R-102', fontsize=9, fontweight='bold', color='#064E3B')
    ax.set_xlabel('Hardware Valuation (USD Billions)', fontsize=8, color='#475569')
    ax.grid(axis='x', linestyle='--', alpha=0.5)
    for bar in bars:
        w = bar.get_width()
        ax.annotate(f'${w:.2f}B', xy=(w, bar.get_y() + bar.get_height() / 2),
                    xytext=(5, 0), textcoords="offset points", ha='left', va='center', fontsize=7.5, fontweight='bold', color='#0F172A')
    ax.set_xlim(0, 1.9)
    plt.tight_layout()
    p3 = os.path.join(output_dir, "r102_hardware_share.png")
    plt.savefig(p3)
    plt.close()
    chart_paths["r102_hardware"] = p3

    # Chart 2B: Line Chart showing Component Cost Erosion (Ultrasonic vs Mechanical)
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=200)
    timeline = np.array([2020, 2021, 2022, 2023, 2024, 2025])
    ultrasonic_cost = [82, 74, 66, 58, 52, 47]
    mechanical_cost = [42, 43, 45, 46, 46, 47]
    
    ax.plot(timeline, ultrasonic_cost, marker='^', color='#047857', linewidth=2.2, label='Ultrasonic Endpoint BOM ($)')
    ax.plot(timeline, mechanical_cost, marker='o', color='#B45309', linewidth=2.0, linestyle='--', label='Mechanical Multi-Jet BOM ($)')
    ax.axvline(x=2025, color='#DC2626', linestyle=':', alpha=0.8, label='Cost Parity Crossover Point (2025)')
    
    ax.set_title('Hardware Metrology Unit BOM Cost Parity Trajectory\nHistoric vs Forecast Unit Economics | Source: Aquila R-102', fontsize=9, fontweight='bold', color='#064E3B')
    ax.set_ylabel('Factory-Gate BOM Cost ($/Unit)', fontsize=8, color='#475569')
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.legend(fontsize=7.2, loc='upper right')
    for x, u, m in zip(timeline, ultrasonic_cost, mechanical_cost):
        if x in [2020, 2023, 2025]:
            ax.annotate(f'${u}', (x, u), textcoords="offset points", xytext=(0, 5), ha='center', fontsize=7.2, fontweight='bold', color='#047857')
            ax.annotate(f'${m}', (x, m), textcoords="offset points", xytext=(0, -11), ha='center', fontsize=7.2, fontweight='bold', color='#B45309')
    plt.tight_layout()
    p2b = os.path.join(output_dir, "r102_cost_parity.png")
    plt.savefig(p2b)
    plt.close()
    chart_paths["r102_parity"] = p2b

    # =========================================================================
    # 3. R-103: RESIDENTIAL WATER PURIFIERS
    # =========================================================================
    
    # Chart 3A: Donut Chart
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=200)
    techs = ['Reverse Osmosis (RO)', 'UV Purification', 'Ultrafiltration (UF)', 'Gravity / Carbon Filters']
    tech_shares = [52.4, 24.6, 13.8, 9.2]
    colors_purifier = ['#0284C7', '#38BDF8', '#7DD3FC', '#CBD5E1']
    ax.pie(tech_shares, labels=techs, autopct='%1.1f%%', startangle=120, colors=colors_purifier,
           wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2),
           textprops={'fontsize': 8, 'color': '#1E293B'})
    ax.set_title('Global Residential Water Purifier Market by Technology (2024)\n2024 Base: USD 9.85B | CAGR: 8.9% | Source: CMR R-103', fontsize=9, fontweight='bold', color='#0369A1')
    plt.tight_layout()
    p4 = os.path.join(output_dir, "r103_tech_share.png")
    plt.savefig(p4)
    plt.close()
    chart_paths["r103_tech"] = p4

    # Chart 3B: Radar / Spider Chart (RO vs UV vs UF Technical Comparison)
    fig = plt.figure(figsize=(6, 3.2), dpi=200)
    ax = fig.add_subplot(111, polar=True)
    categories = ['TDS Removal', 'Microbial Kill', 'Flow Rate', 'Energy Efficiency', 'Zero Water Waste']
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    
    ro_vals = [9.5, 9.8, 4.0, 5.0, 3.5]
    ro_vals += ro_vals[:1]
    uv_vals = [2.0, 9.2, 8.5, 9.0, 9.5]
    uv_vals += uv_vals[:1]
    uf_vals = [4.5, 7.5, 9.0, 9.5, 9.0]
    uf_vals += uf_vals[:1]
    
    ax.plot(angles, ro_vals, linewidth=1.8, color='#0284C7', label='Reverse Osmosis (RO)')
    ax.fill(angles, ro_vals, color='#0284C7', alpha=0.15)
    ax.plot(angles, uv_vals, linewidth=1.5, color='#10B981', label='UV System')
    ax.fill(angles, uv_vals, color='#10B981', alpha=0.1)
    ax.plot(angles, uf_vals, linewidth=1.5, color='#F59E0B', label='Ultrafiltration (UF)')
    ax.fill(angles, uf_vals, color='#F59E0B', alpha=0.1)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=7.5, fontweight='bold', color='#1E293B')
    ax.set_ylim(0, 10)
    ax.set_title('Filtration Technology Multi-Attribute Comparison Matrix\nScale: 1-10 Benchmark | Source: CMR R-103', fontsize=8.5, fontweight='bold', pad=14, color='#0369A1')
    ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.15), fontsize=6.8)
    plt.tight_layout()
    p3b = os.path.join(output_dir, "r103_radar_matrix.png")
    plt.savefig(p3b)
    plt.close()
    chart_paths["r103_radar"] = p3b

    # =========================================================================
    # 4. R-104: COMMERCIAL & INDUSTRIAL WATER TREATMENT
    # =========================================================================
    
    # Chart 4A: Grouped Side-by-Side Bar Chart (2024 Base vs 2030 Projected Capex)
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=200)
    sectors = ['Pharma/Bio', 'Power Gen', 'Food & Bev', 'Chemicals', 'Desalination']
    base_2024 = [4.54, 3.41, 2.84, 1.99, 1.42]
    proj_2030 = [7.12, 5.15, 4.38, 3.01, 2.24]
    
    x = np.arange(len(sectors))
    w = 0.35
    b1 = ax.bar(x - w/2, base_2024, w, label='2024 Baseline ($B)', color='#6D28D9')
    b2 = ax.bar(x + w/2, proj_2030, w, label='2030 Projected ($B)', color='#A78BFA')
    
    ax.set_title('Industrial RO & Water Treatment Capex: 2024 vs 2030\n7.4% Overall Market CAGR | Source: CMR R-104', fontsize=9, fontweight='bold', color='#4C1D95')
    ax.set_xticks(x)
    ax.set_xticklabels(sectors, fontsize=8)
    ax.set_ylabel('Capex Spend (USD Billions)', fontsize=8, color='#475569')
    ax.grid(axis='y', linestyle=':', alpha=0.6)
    ax.legend(fontsize=7.5, loc='upper right')
    for bar in b1:
        h = bar.get_height()
        ax.annotate(f'${h:.1f}', (bar.get_x() + bar.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=7, fontweight='bold')
    for bar in b2:
        h = bar.get_height()
        ax.annotate(f'${h:.1f}', (bar.get_x() + bar.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha='center', fontsize=7, fontweight='bold', color='#4C1D95')
    ax.set_ylim(0, 8.5)
    plt.tight_layout()
    p5 = os.path.join(output_dir, "r104_industrial_spend.png")
    plt.savefig(p5)
    plt.close()
    chart_paths["r104_spend"] = p5

    # =========================================================================
    # 5. R-105: SMART MULTI-UTILITY METERING
    # =========================================================================
    
    # Chart 5A: Pie/Donut Chart
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=200)
    utilities = ['Electricity AMI', 'Smart Water Meters', 'Gas AMI Endpoints']
    endpoint_shares = [62.0, 26.0, 12.0]
    colors_multi = ['#D97706', '#F59E0B', '#FCD34D']
    wedges, texts, autotexts = ax.pie(
        endpoint_shares, labels=utilities, autopct='%1.1f%%',
        startangle=90, colors=colors_multi,
        wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2),
        textprops={'fontsize': 8.5, 'color': '#1E293B'}
    )
    for at in autotexts:
        at.set_weight('bold')
        at.set_color('white')
    ax.set_title('Multi-Utility Smart Metering Infrastructure Shipments (2024)\nTotal Multi-Grid Market: USD 11.50B | Source: Apex Grid R-105', fontsize=9, fontweight='bold', color='#92400E')
    plt.tight_layout()
    p6 = os.path.join(output_dir, "r105_utility_mix.png")
    plt.savefig(p6)
    plt.close()
    chart_paths["r105_mix"] = p6

    # =========================================================================
    # 6. R-106: DECENTRALIZED WASTEWATER RECYCLING
    # =========================================================================
    
    # Chart 6A: Dual-Axis Line + Bar Chart (Market Volume vs YoY Growth Rate)
    fig, ax1 = plt.subplots(figsize=(6, 3.2), dpi=200)
    years_w = ['2024', '2025', '2026', '2027', '2028', '2029', '2030']
    base_w = 7.60
    cagr_w = 0.125
    vals_w = [base_w * ((1 + cagr_w) ** i) for i in range(len(years_w))]
    growth_rates = [0.0, 12.5, 12.8, 13.1, 12.4, 12.1, 11.8]
    
    color_bar = '#0D9488'
    bars = ax1.bar(years_w, vals_w, color=color_bar, width=0.50, edgecolor='#115E59', label='Market Valuation ($B)')
    ax1.set_ylabel('Market Sizing (USD Billions)', color=color_bar, fontsize=8)
    ax1.tick_params(axis='y', labelcolor=color_bar)
    ax1.set_ylim(0, 18.0)
    for bar in bars:
        h = bar.get_height()
        ax1.annotate(f'${h:.1f}B', (bar.get_x() + bar.get_width()/2, h), xytext=(0, 2), textcoords="offset points", ha='center', fontsize=6.8, fontweight='bold')

    ax2 = ax1.twinx()
    color_line = '#DC2626'
    ax2.plot(years_w[1:], growth_rates[1:], color=color_line, marker='o', linewidth=2.0, linestyle='--', label='YoY Growth Rate (%)')
    ax2.set_ylabel('Annual Growth Rate (%)', color=color_line, fontsize=8)
    ax2.tick_params(axis='y', labelcolor=color_line)
    ax2.set_ylim(8, 16)
    for yr, gr in zip(years_w[1:], growth_rates[1:]):
        ax2.annotate(f'{gr:.1f}%', (yr, gr), xytext=(0, 5), textcoords="offset points", ha='center', fontsize=6.8, fontweight='bold', color=color_line)

    ax1.set_title('Decentralized Wastewater Treatment: Sizing & YoY Growth\nDual-Axis Valuation & Growth Dynamics | Source: CMR R-106', fontsize=8.8, fontweight='bold', color='#134E4A')
    plt.tight_layout()
    p7 = os.path.join(output_dir, "r106_wastewater_growth.png")
    plt.savefig(p7)
    plt.close()
    chart_paths["r106_growth"] = p7

    print(f"Generated {len(chart_paths)} diverse visual charts in {output_dir}")
    return chart_paths


if __name__ == "__main__":
    generate_all_charts("data/charts")
