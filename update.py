
import json
import math
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pykrx import stock

KST = ZoneInfo('Asia/Seoul')

WATCH = [
    '005930', '000660', '035420', '035720', '005380',
    '000270', '068270', '207940', '373220', '006400',
    '034020', '267260', '012450', '042660', '329180',
    '009540', '010140', '086280', '047810', '066570',
    '051910', '003670', '247540', '196170', '058470',
    '079550', '298040', '015760', '017670', '105560'
]

KOSPI_FALLBACK = {
    '005930', '000660', '005380', '000270', '068270',
    '207940', '373220', '006400', '034020', '267260',
    '012450', '042660', '329180', '009540', '010140',
    '086280', '047810', '066570', '051910', '003670',
    '079550', '298040', '015760', '017670', '105560',
    '035420', '035720'
}


def wilder_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None

    changes = [
        closes[i] - closes[i-1]
        for i in range(1, len(closes))
    ]

    avg_gain = sum(
        max(x, 0) for x in changes[:period]
    ) / period

    avg_loss = sum(
        max(-x, 0) for x in changes[:period]
    ) / period

    for change in changes[period:]:
        avg_gain = (
            avg_gain * (period - 1) + max(change, 0)
        ) / period

        avg_loss = (
            avg_loss * (period - 1) + max(-change, 0)
        ) / period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0

    return 100 - 100 / (1 + avg_gain / avg_loss)


def wilder_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return None

    tr = [
        max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        for i in range(1, len(closes))
    ]

    atr = sum(tr[:period]) / period

    for value in tr[period:]:
        atr = (
            atr * (period - 1) + value
        ) / period

    return atr


def score_components(
    close, ma20, ma60, strength,
    momentum, volume_ratio, atr_pct
):
    trend = (
        (15 if close > ma20 else 0)
        + (15 if ma20 > ma60 else 0)
    )

    rsi_points = (
        20 if 45 <= strength <= 65
        else (
            10 if (
                35 <= strength < 45
                or 65 < strength <= 70
            ) else 0
        )
    )

    momentum_points = (
        20 if 2 <= momentum <= 15
        else (
            10 if (
                0 < momentum < 2
                or 15 < momentum <= 25
            ) else 0
        )
    )

    volume_points = (
        15 if 1.2 <= volume_ratio <= 3
        else (
            8 if (
                0.8 <= volume_ratio < 1.2
                or 3 < volume_ratio <= 4
            ) else 0
        )
    )

    volatility_points = (
        15 if 1 <= atr_pct <= 5
        else (
            8 if (
                0.5 <= atr_pct < 1
                or 5 < atr_pct <= 8
            ) else 0
        )
    )

    return {
        'trend': trend,
        'rsi': rsi_points,
        'momentum': momentum_points,
        'volume': volume_points,
        'volatility': volatility_points
    }


def calculate(ticker, name, market, df):
    if df is None or len(df) < 65:
        return None

    df = df.sort_index()

    cols = ['시가', '고가', '저가', '종가', '거래량']

    if any(col not in df.columns for col in cols):
        return None

    values = {
        col: [float(x) for x in df[col].tolist()]
        for col in cols
    }

    if any(
        not all(math.isfinite(x) for x in values[col])
        for col in cols
    ):
        return None

    c, v, h, l, o = (
        values['종가'],
        values['거래량'],
        values['고가'],
        values['저가'],
        values['시가']
    )

    if (
        any(x <= 0 for x in c[-65:])
        or v[-1] <= 0
        or min(l[-1], o[-1]) <= 0
        or h[-1] < l[-1]
    ):
        return None

    ma20 = sum(c[-20:]) / 20
    ma60 = sum(c[-60:]) / 60

    previous_volume = sum(v[-21:-1]) / 20

    rv = (
        v[-1] / previous_volume
        if previous_volume > 0 else 0
    )

    momentum = (c[-1] / c[-21] - 1) * 100

    strength = wilder_rsi(c)
    atr = wilder_atr(h, l, c)

    if strength is None or atr is None or atr <= 0:
        return None

    atr_pct = atr / c[-1] * 100

    breakdown = score_components(
        c[-1], ma20, ma60,
        strength, momentum, rv, atr_pct
    )

    score = sum(breakdown.values())

    change_pct = (c[-1] / c[-2] - 1) * 100
    day_range = (h[-1] - l[-1]) / c[-2] * 100

    if change_pct >= 3:
        trend = '강한 상승'
    elif change_pct >= 0.5:
        trend = '상승'
    elif change_pct <= -3:
        trend = '강한 하락'
    elif change_pct <= -0.5:
        trend = '하락'
    else:
        trend = '보합권'

    support20 = min(l[-20:])
    support60 = min(l[-60:])

    resistance20 = max(h[-20:])
    resistance60 = max(h[-60:])

    first = min(
        c[-1] - 0.75 * atr,
        ma20 if ma20 < c[-1]
        else c[-1] - 0.75 * atr
    )

    second = min(
        first - 0.75 * atr,
        support20 if support20 < first
        else first - 0.75 * atr
    )

    third = min(
        second - 0.75 * atr,
        support60 if support60 < second
        else second - 0.75 * atr
    )

    # Reject unrealistic reference levels.
    if (
        third <= 1
        or second <= third
        or first <= second
    ):
        return None

    stop = min(
        third - 0.5 * atr,
        support60 - 0.25 * atr
    )

    if stop <= 0:
        return None

    target = min(
        max(
            c[-1] + 2 * atr,
            resistance20
            if resistance20 > c[-1] else 0
        ),
        c[-1] + 4 * atr
    )

    buy1 = round(first)
    buy2 = round(second)
    buy3 = round(third)

    stop_price = round(stop)
    target_price = round(target)

    if not (
        0 < stop_price < buy3 < buy2
        < buy1 < round(c[-1]) < target_price
    ):
        return None

    reasons = []
    risks = []

    if c[-1] > ma20:
        reasons.append(
            '종가가 20일 이동평균선 위에 있습니다.'
        )
    else:
        risks.append(
            '종가가 20일 이동평균선 아래에 있습니다.'
        )

    if ma20 > ma60:
        reasons.append(
            '20일 이동평균선이 60일 이동평균선 위에 있습니다.'
        )
    else:
        risks.append(
            '20일 이동평균선이 60일 이동평균선 이하입니다.'
        )

    if 45 <= strength <= 65:
        reasons.append(
            f'Wilder RSI {strength:.1f}로 중립~상승 구간입니다.'
        )
    elif strength >= 70:
        risks.append(
            f'Wilder RSI {strength:.1f}로 과열 가능성이 있습니다.'
        )
    elif strength <= 30:
        risks.append(
            f'Wilder RSI {strength:.1f}로 약세 압력이 강할 수 있습니다.'
        )

    if rv >= 1.2:
        reasons.append(
            f'거래량이 직전 20거래일 평균의 {rv:.2f}배입니다.'
        )
    elif rv < 0.8:
        risks.append(
            f'거래량이 직전 20거래일 평균의 {rv:.2f}배로 낮습니다.'
        )

    if momentum > 0:
        reasons.append(
            f'최근 20거래일 수익률은 {momentum:+.1f}%입니다.'
        )
    else:
        risks.append(
            f'최근 20거래일 수익률은 {momentum:+.1f}%입니다.'
        )

    if atr_pct > 5:
        risks.append(
            f'ATR 변동성이 종가의 {atr_pct:.1f}%로 높아 '
            '가격 흔들림에 유의해야 합니다.'
        )

    if change_pct < 0 and c[-1] > o[-1]:
        reasons.append(
            '전일 대비 하락했지만 시가보다 높게 마감했습니다.'
        )

    if change_pct > 0 and c[-1] < o[-1]:
        risks.append(
            '전일 대비 상승했지만 시가보다 낮게 마감했습니다.'
        )

    if not reasons:
        reasons.append(
            '현재 조건에서 뚜렷한 긍정 신호가 부족합니다.'
        )

    if not risks:
        risks.append(
            '시장 급변, 기업 공시 및 실적 위험은 '
            '별도로 확인해야 합니다.'
        )

    summary = (
        f'{trend} 마감({change_pct:+.2f}%). '
        f'시가 {o[-1]:,.0f}원, '
        f'고가 {h[-1]:,.0f}원, '
        f'저가 {l[-1]:,.0f}원. '
        f'거래량은 직전 20거래일 평균의 {rv:.2f}배.'
    )

    return dict(
        ticker=ticker,
        name=name,
        market=market,
        close=round(c[-1]),
        change=round(change_pct, 2),
        score=score,
        scoreBreakdown=breakdown,
        scoreMax={
            'trend': 30,
            'rsi': 20,
            'momentum': 20,
            'volume': 15,
            'volatility': 15
        },
        rsi=round(strength, 1),
        ma20=round(ma20),
        ma60=round(ma60),
        volumeRatio=round(rv, 2),
        momentum20=round(momentum, 2),
        atr14=round(atr, 2),
        atrPct=round(atr_pct, 2),
        support20=round(support20),
        support60=round(support60),
        resistance20=round(resistance20),
        resistance60=round(resistance60),
        buy1=buy1,
        buy2=buy2,
        buy3=buy3,
        stop=stop_price,
        target=target_price,
        priceMethod='ATR(14)·20/60일 지지/저항 참고 (미검증 예시)',
        date=str(df.index[-1].date()),
        open=round(o[-1]),
        high=round(h[-1]),
        low=round(l[-1]),
        volume=round(v[-1]),
        dayRangePct=round(day_range, 2),
        trend=trend,
        trendSummary=summary,
        reasons=reasons,
        risks=risks,
        analysisType='기술적 지표 기반 자동 생성 (뉴스·공시 미포함)',
        analysisVersion='1.4'
    )


def main():
    now = datetime.now(KST)

    end = now.strftime('%Y%m%d')
    start = (now - timedelta(days=180)).strftime('%Y%m%d')

    kospi = set()
    kosdaq = set()

    try:
        kospi = set(
            stock.get_market_ticker_list(
                end, market='KOSPI'
            )
        )
        kosdaq = set(
            stock.get_market_ticker_list(
                end, market='KOSDAQ'
            )
        )
    except Exception as exc:
        print(
            'Market lookup warning:',
            str(exc)[:150]
        )

    results = []
    errors = []

    for ticker in WATCH:
        try:
            name = (
                stock.get_market_ticker_name(ticker)
                or ticker
            )

            df = stock.get_market_ohlcv_by_date(
                start, end, ticker
            )

            market = (
                'KOSPI' if ticker in kospi
                else 'KOSDAQ' if ticker in kosdaq
                else 'KOSPI' if ticker in KOSPI_FALLBACK
                else 'KOSDAQ'
            )

            item = calculate(
                ticker, name, market, df
            )

            if item:
                results.append(item)
            else:
                errors.append(
                    ticker + ': insufficient or invalid data'
                )

        except Exception as exc:
            errors.append(
                f'{ticker}: {str(exc)[:120]}'
            )

        time.sleep(0.3)

    if len(results) < 24:
        raise RuntimeError(
            f'Only {len(results)}/{len(WATCH)} '
            'stocks collected; keeping previous '
            'data.json unchanged. '
            + '; '.join(errors[:5])
        )

    results.sort(
        key=lambda x: (
            -x['score'],
            -x['momentum20']
        )
    )

    payload = {
        'updatedAt': now.isoformat(timespec='seconds'),
        'asOf': max(x['date'] for x in results),
        'universeCount': len(WATCH),
        'successCount': len(results),
        'errors': errors,
        'analysisVersion': '1.4',
        'stocks': results
    }

    path = 'data.json'

    with open(
        path + '.tmp',
        'w',
        encoding='utf-8'
    ) as f:
        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2,
            allow_nan=False
        )

    os.replace(path + '.tmp', path)

    print(
        'Updated',
        len(results),
        'stocks; errors',
        len(errors),
        '; asOf',
        payload['asOf']
    )


if __name__ == '__main__':
    main()
