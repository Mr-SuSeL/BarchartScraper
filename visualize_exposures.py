import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from coffee_parser import parse_coffee_options
from exposure_engine import OptionExposureCalculator

plt.style.use("dark_background")
plt.ion()

def plot_exposures_dashboard(
    df_results: pd.DataFrame,
    summary: dict,
    symbol: str = "Coffee C (KC)",
    out_file: str = "coffee_exposures_dashboard.png",
    fig=None,
):
    if fig is None or not plt.fignum_exists(fig.number):
        fig = plt.figure(figsize=(20, 11))
        fig.canvas.manager.set_window_title(f"Options Exposures — {symbol}")
    else:
        fig.clf()

    fig.patch.set_facecolor("#121212")
    
    # Symetryczna siatka 2 × 3: trzy ekspozycje w każdym rzędzie.
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.42, wspace=0.42)
    
    axes = {
        "gex": fig.add_subplot(gs[0, 0]),
        "vex": fig.add_subplot(gs[0, 1]),
        "voex": fig.add_subplot(gs[0, 2]),
        "chex": fig.add_subplot(gs[1, 0]),
        "vanna_flow": fig.add_subplot(gs[1, 1]),
        "iv": fig.add_subplot(gs[1, 2])
    }

    df_agg = (
        df_results.groupby("strike")
        .agg({
            "gex": "sum",
            "vex": "sum",
            "voex": "sum",       # Nowa kolumna z silnika
            "chex": "sum",
            "vanna_flow": "sum",
            "iv": "mean",
            "delta_iv": "mean",
        })
        .reset_index()
    )

    spot_price = summary["spot_price"]
    delta_iv_pct = summary["delta_iv_pct"]

    min_strike = spot_price * 0.75
    max_strike = spot_price * 1.25
    df_filtered = df_agg[(df_agg["strike"] >= min_strike) & (df_agg["strike"] <= max_strike)].copy()

    iv_str = f"+{delta_iv_pct:.2f}%" if delta_iv_pct >= 0 else f"{delta_iv_pct:.2f}%"
    fig.suptitle(
        f"Ares Analytics: Profil Ekspozycji Dealerów — {symbol} | Spot: {spot_price:.2f} | Weighted IV: {summary['weighted_iv']*100:.1f}% (ΔIV: {iv_str})",
        fontsize=16,
        fontweight="bold",
        color="#ffffff",
        y=0.97,
    )

    # Konfiguracja paneli słupkowych
    subplots_config = [
        (axes["gex"], "gex", "GEX (Gamma Exposure — $ / +1% Spot)", 1e6, "M USD"),
        (axes["vex"], "vex", "VEX (Vanna Exposure — $ / +1% IV)", 1e6, "M USD"),
        (axes["voex"], "voex", "VOEX (Volga/Vomma Exposure — $)", 1e3, "K USD"),
        (axes["chex"], "chex", "CHEX (Charm Exposure — $ Drift / 1 Day)", 1e6, "M USD"),
        (axes["vanna_flow"], "vanna_flow", "VANNA FLOW (Real Dealer Flow w USD)", 1e6, "M USD"),
    ]

    for ax, col, title, scale_factor, unit in subplots_config:
        ax.set_facecolor("#181818")
        strikes = df_filtered["strike"]
        # Zabezpieczenie w razie braku kolumny w początkowym etapie testów
        values = (df_filtered[col] if col in df_filtered else np.zeros(len(strikes))) / scale_factor
        colors = ["#26a69a" if val >= 0 else "#ef5350" for val in values]

        ax.bar(strikes, values, width=1.8, color=colors, alpha=0.85, edgecolor="none")
        ax.axvline(x=spot_price, color="#ffb74d", linestyle="--", linewidth=1.5, label=f"Spot: {spot_price:.2f}")
        ax.axhline(0, color="#666666", linewidth=0.8, linestyle="-")

        ax.set_title(title, fontsize=11, pad=8, fontweight="semibold", color="#ffffff")
        ax.set_ylabel(f"Wartość [{unit}]", fontsize=9, color="#cccccc", labelpad=7)
        ax.grid(True, linestyle=":", alpha=0.25)
        ax.legend(loc="upper right", frameon=True, facecolor="#1e1e1e", edgecolor="#333333", fontsize=8)
        ax.set_xlabel("Strike Price", fontsize=9, color="#cccccc")

    # Panel IV Skew (Zajmujący szerokość 2 kolumn)
    ax_iv = axes["iv"]
    ax_iv.set_facecolor("#181818")
    strikes = df_filtered["strike"]
    iv_vals = df_filtered["iv"] * 100.0
    delta_iv_pp = df_filtered["delta_iv"] * 100.0

    color_iv = "#42a5f5"
    ax_iv.set_xlabel("Strike Price", fontsize=9, color="#cccccc")
    ax_iv.set_ylabel("Implied Volatility [%]", color=color_iv, fontsize=9, labelpad=7)
    ax_iv.plot(strikes, iv_vals, color=color_iv, linewidth=2.0, marker="o", markersize=4, label="IV Profile (%)")
    ax_iv.tick_params(axis="y", labelcolor=color_iv)

    ax_div = ax_iv.twinx()
    color_div = "#ff7043"
    ax_div.set_ylabel("Local ΔIV [pp]", color=color_div, fontsize=9, labelpad=7)

    div_colors = ["#26a69a" if val >= 0 else "#ef5350" for val in delta_iv_pp]
    ax_div.bar(strikes, delta_iv_pp, width=1.2, color=div_colors, alpha=0.45, label="Real ΔIV Shift (pp)")
    ax_div.tick_params(axis="y", labelcolor=color_div)

    ax_iv.axvline(x=spot_price, color="#ffb74d", linestyle="--", linewidth=1.5)
    ax_iv.grid(True, linestyle=":", alpha=0.25)
    ax_iv.set_title("RZECZYWISTA KRZYWA IV ORAZ LOKALNA ΔIV", fontsize=11, pad=8, fontweight="semibold", color="#ffffff")

    lines_1, labels_1 = ax_iv.get_legend_handles_labels()
    lines_2, labels_2 = ax_div.get_legend_handles_labels()
    ax_div.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper right", frameon=True, facecolor="#1e1e1e", edgecolor="#333333", fontsize=8)

    fig.subplots_adjust(left=0.075, right=0.93, bottom=0.08, top=0.90, wspace=0.42, hspace=0.42)
    plt.savefig(out_file, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())

    fig.canvas.draw()
    fig.canvas.flush_events()

    return fig

if __name__ == "__main__":
    df_raw = parse_coffee_options("coffee_options.json")

    if not df_raw.empty:
        CURRENT_SPOT = 286.95
        TIME_TO_EXPIRY = 0.15

        calc = OptionExposureCalculator(spot_price=CURRENT_SPOT, multiplier=37500.0, cache_dir="cache")
        df_results = calc.compute_exposures(df_raw, time_to_expiry_years=TIME_TO_EXPIRY, ticker="KC")
        summary = calc.get_summary(df_results)

        fig = plot_exposures_dashboard(df_results, summary=summary)
        plt.show(block=True)