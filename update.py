import json, os, time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pykrx import stock

KST=ZoneInfo('Asia/Seoul')
WATCH=['005930','000660','035420','035720','005380','000270','068270','207940','373220','006400','034020','267260','012450','042660','329180','009540','010140','086280','047810','066570','051910','003670','247540','196170','058470','079550','298040','015760','017670','105560']

def rsi(closes, n=14):
    diffs=[closes[i]-closes[i-1] for i in range(1,len(closes))]
    if len(diffs)<n: return None
    gains=[max(x,0) for x in diffs[-n:]]
    losses=[max(-x,0) for x in diffs[-n:]]
    ag=sum(gains)/n; al=sum(losses)/n
    return 100 if al==0 else 100-100/(1+ag/al)

def calculate(ticker, name, market, df):
    if df is None or len(df)<65: return None
    c=[float(v) for v in df['종가'].tolist()]
    v=[float(x) for x in df['거래량'].tolist()]
    if c[-1]<=0 or v[-1]<=0:return None
    ma20=sum(c[-20:])/20; ma60=sum(c[-60:])/60
    rv=v[-1]/(sum(v[-21:-1])/20 or 1)
    momentum=(c[-1]/c[-21]-1)*100
    strength=rsi(c)
    if strength is None:return None
    score=35
    score+=20 if c[-1]>ma20 else 0
    score+=15 if ma20>ma60 else 0
    score+=10 if 45<=strength<=65 else (5 if 35<=strength<=75 else 0)
    score+=10 if 0<momentum<20 else (4 if momentum>=20 else 0)
    score+=10 if rv>=1.2 else (5 if rv>=0.8 else 0)
    score=min(100,score)
    previous=c[-2]
    change_pct=(c[-1]/previous-1)*100
    open_price=float(df['시가'].iloc[-1])
    high_price=float(df['고가'].iloc[-1])
    low_price=float(df['저가'].iloc[-1])
    day_range=(high_price-low_price)/previous*100
    if change_pct>=3: trend='강한 상승'
    elif change_pct>=0.5: trend='상승'
    elif change_pct<=-3: trend='강한 하락'
    elif change_pct<=-0.5: trend='하락'
    else: trend='보합권'
    reasons=[]; risks=[]
    if c[-1]>ma20: reasons.append('종가가 20일 이동평균선 위에 있어 단기 추세가 상대적으로 양호합니다.')
    else: risks.append('종가가 20일 이동평균선 아래에 있어 단기 추세가 약합니다.')
    if ma20>ma60: reasons.append('20일선이 60일선 위에 있어 중기 추세가 우호적입니다.')
    else: risks.append('20일선이 60일선 이하로 중기 추세 확인이 필요합니다.')
    if rv>=1.2: reasons.append(f'당일 거래량이 직전 20거래일 평균의 {rv:.2f}배로 증가했습니다.')
    elif rv<0.8: risks.append('거래량이 최근 평균보다 적어 가격 움직임의 신뢰도가 낮을 수 있습니다.')
    if 45<=strength<=65: reasons.append(f'RSI {strength:.1f}로 과열·과매도 구간에서 비교적 떨어져 있습니다.')
    elif strength>=70: risks.append(f'RSI {strength:.1f}로 단기 과열 가능성에 유의해야 합니다.')
    elif strength<=30: risks.append(f'RSI {strength:.1f}로 하락 압력이 강할 수 있습니다.')
    if 0<momentum<20: reasons.append(f'최근 20거래일 수익률이 +{momentum:.1f}%로 양의 모멘텀을 보입니다.')
    elif momentum<0: risks.append(f'최근 20거래일 수익률이 {momentum:.1f}%로 음의 모멘텀입니다.')
    if change_pct>0 and c[-1]<open_price: risks.append('전일 대비 상승했지만 시가보다 낮게 마감해 장중 매도 압력이 있었습니다.')
    if change_pct<0 and c[-1]>open_price: reasons.append('전일 대비 하락했지만 시가보다 높게 마감해 장중 낙폭을 일부 만회했습니다.')
    if not reasons: reasons.append('현재 기술적 조건에서 뚜렷한 긍정 신호가 부족합니다. 관찰 대상으로 분류합니다.')
    if not risks: risks.append('지표가 양호해도 시장 급변, 공시 및 실적 위험은 남아 있습니다.')
    trend_summary=f'{trend} 마감({change_pct:+.2f}%). 시가 {open_price:,.0f}원, 고가 {high_price:,.0f}원, 저가 {low_price:,.0f}원. 거래량은 최근 20거래일 평균의 {rv:.2f}배.'
    return dict(ticker=ticker,name=name,market=market,close=round(c[-1]),change=round((c[-1]/c[-2]-1)*100,2),score=score,rsi=round(strength,1),ma20=round(ma20),ma60=round(ma60),volumeRatio=round(rv,2),momentum20=round(momentum,2),buy1=round(c[-1]*0.98),buy2=round(c[-1]*0.95),buy3=round(c[-1]*0.92),stop=round(c[-1]*0.90),target=round(c[-1]*1.12),date=str(df.index[-1].date()),open=round(open_price),high=round(high_price),low=round(low_price),volume=round(v[-1]),dayRangePct=round(day_range,2),trend=trend,trendSummary=trend_summary,reasons=reasons,risks=risks,analysisType='기술적 지표 기반 자동 생성 (뉴스·공시 미포함)')

def main():
    now=datetime.now(KST)
    end=now.strftime('%Y%m%d'); start=(now-timedelta(days=145)).strftime('%Y%m%d')
    results=[]; errors=[]
    for ticker in WATCH:
        try:
            name=stock.get_market_ticker_name(ticker) or ticker
            df=stock.get_market_ohlcv_by_date(start,end,ticker)
            market='KOSPI' if ticker in {'005930','000660','005380','000270','068270','207940','373220','006400','034020','267260','012450','042660','329180','009540','010140','086280','047810','066570','051910','003670','079550','298040','015760','017670','105560'} else 'KOSDAQ'
            item=calculate(ticker,name,market,df)
            if item: results.append(item)
            else: errors.append(ticker+': insufficient data')
        except Exception as exc: errors.append(f'{ticker}: {str(exc)[:100]}')
        time.sleep(0.3)
    results.sort(key=lambda x:(-x['score'],-x['momentum20']))
    path='data.json'
    if not results:
        raise RuntimeError('No valid data. Keeping previous data.json unchanged. '+ '; '.join(errors[:5]))
    data={'updatedAt':now.isoformat(timespec='seconds'),'asOf':max(x['date'] for x in results),'universeCount':len(WATCH),'successCount':len(results),'errors':errors,'stocks':results}
    with open(path+'.tmp','w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
    os.replace(path+'.tmp',path)
    print('Updated',len(results),'stocks; errors',len(errors))
if __name__=='__main__': main()
