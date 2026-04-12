"""
利益計算モジュール
仕入れコスト・関税・送料・プラットフォーム手数料を考慮して利益・ROIを計算する
"""

from dataclasses import dataclass


@dataclass
class ProfitResult:
    total_cost_jpy: int        # 総仕入れコスト（円）
    sell_price_jpy: int        # 販売価格（円）
    platform:       str        # 販売先プラットフォーム
    profit_jpy:     int        # 純利益（円）
    roi_pct:        float      # ROI（%）
    is_profitable:  bool       # 利益判定


def calc_total_cost(
    price_cny:          float,
    exchange_rate:      float,
    shipping_china_jpy: int,
    import_duty_rate:   float,
    domestic_ship_jpy:  int,
) -> int:
    """
    総仕入れコストを計算する。

    仕入れコスト = 商品代金(元→円) + 中国送料 + 関税 + 国内送料
    関税 = (商品代金円換算 + 中国送料) × 関税率
    """
    price_jpy = price_cny * exchange_rate
    duty = (price_jpy + shipping_china_jpy) * import_duty_rate
    total = price_jpy + shipping_china_jpy + duty + domestic_ship_jpy
    return int(total)


def calc_profit(
    total_cost_jpy:  int,
    sell_price_jpy:  int,
    platform_fee:    float,
    platform_name:   str,
) -> ProfitResult:
    """
    純利益とROIを計算する。

    純利益 = 販売価格 × (1 - プラットフォーム手数料率) - 総仕入れコスト
    """
    net_revenue = sell_price_jpy * (1 - platform_fee)
    profit = int(net_revenue - total_cost_jpy)
    roi = (profit / total_cost_jpy * 100) if total_cost_jpy > 0 else 0

    return ProfitResult(
        total_cost_jpy=total_cost_jpy,
        sell_price_jpy=sell_price_jpy,
        platform=platform_name,
        profit_jpy=profit,
        roi_pct=round(roi, 1),
        is_profitable=profit > 0,
    )


def find_best_platform(
    total_cost_jpy:  int,
    prices:          dict[str, int],
    platform_fees:   dict[str, float],
) -> ProfitResult | None:
    """
    複数プラットフォームの中から最も利益の高いものを選ぶ。

    prices: {"amazon": 3000, "rakuten": 2800, ...}
    """
    best = None
    for platform, sell_price in prices.items():
        if sell_price <= 0:
            continue
        fee = platform_fees.get(platform, 0.10)
        result = calc_profit(total_cost_jpy, sell_price, fee, platform)
        if best is None or result.profit_jpy > best.profit_jpy:
            best = result
    return best
