# 국장 시그널 v1.3 — 관리자 승인 로그인 / 비공개 분석 데이터

주요 30개 국내 종목의 일별 기술적 분석 웹앱입니다. 종목별 당일 시가·고가·저가·거래량·등락 흐름과 추천 점수 산정 사유 및 위험 신호를 자동 생성합니다. 뉴스나 공시를 읽어 분석하는 기능은 아닙니다. **관리자가 생성한 Firebase Authentication 계정**만 로그인할 수 있고, **관리자가 Firestore에서 승인한 UID**만 시장 데이터를 읽을 수 있습니다. 사용자 회원가입 화면은 없습니다.

## 1. Firebase 무료 프로젝트 설정
1. https://console.firebase.google.com 에서 프로젝트를 만들고 Spark(무료) 요금제를 선택합니다.
2. Authentication → Sign-in method에서 **Email/Password**를 켭니다. 웹앱에는 회원가입 기능이 없지만 Firebase API 자체는 계정 생성을 지원하므로 **승인 목록**으로 별도 차단합니다.
3. Authentication → Users → Add user에서 관리자용 이메일/비밀번호를 만듭니다. 생성된 사용자 **UID**를 복사합니다.
4. Firestore Database를 만들고 (무료 사용 가능 지역 선택), **Rules**에 동봉된 `firestore.rules` 전체를 붙여넣어 게시합니다. 기본 테스트 모드의 공개 규칙을 사용하면 안 됩니다.
5. Firestore → 데이터 → `approvedUsers` 컬렉션을 만들고 **문서 ID를 위 UID와 똑같이** 설정합니다. 필드 `enabled` (boolean) = `true`로 저장합니다. 계정마다 반복합니다. 중지하려면 `enabled=false`로 변경하거나 문서를 삭제합니다.
6. Firebase 프로젝트 설정 → 웹 앱 등록 후 `firebase-config.js`에 `apiKey`, `authDomain`, `projectId`, `appId`를 입력합니다. 이 값은 공개 클라이언트 설정이며 비밀키가 아닙니다.
7. Authentication → Settings → Authorized domains에 배포할 `사용자명.github.io`를 추가합니다. 로컬 테스트 시 `localhost`도 등록합니다.

## 2. 매일 자동 분석 데이터 업로드 설정
1. Firebase 프로젝트 설정 → 서비스 계정 → 새 비공개 키 생성으로 서비스 계정 JSON을 내려받습니다. **이 파일은 절대 GitHub에 올리지 마세요.**
2. GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret에 이름 `FIREBASE_SERVICE_ACCOUNT_JSON`, 값은 JSON 파일의 **전체 내용**을 입력합니다.
3. GitHub Actions → Daily KRX update → Run workflow를 한 번 실행합니다.
4. Firestore 데이터에 `market/latest` 문서가 생성되고 `stocks` 배열에 실제 종목 데이터가 있는지 확인합니다.
5. 평일 16:40 한국시간에 GitHub Actions가 자동 실행됩니다. 예약 실행은 지연되거나 누락될 수 있습니다.

## 3. GitHub Pages 배포
1. **새 저장소**를 만들어 이 폴더 파일을 업로드합니다. 과거 버전의 `data.json`이 공개 저장소 기록에 남아 있다면 기존 저장소를 재사용하지 마세요.
2. `.github` 폴더도 함께 업로드합니다. `data.json`은 **절대 업로드하지 마세요**. `.gitignore`에 포함되어 있습니다.
3. Settings → Pages → Deploy from a branch → main / root로 설정합니다.
4. 생성된 GitHub Pages 주소에서 로그인합니다. **분석 데이터는 Pages에서 직접 공개되지 않고 Firestore 보안 규칙을 통해 조회**됩니다.

## 보안과 운영 주의
- Firestore Rules에서 승인된 UID에만 읽기를 허용합니다. 브라우저 로그인 화면을 우회해도 미승인 사용자는 데이터를 조회할 수 없습니다.
- Firebase Authentication 이메일/비밀번호 로그인은 별도의 주민등록번호·휴대폰 인증이 필요하지 않습니다. 계정 생성은 관리자 콘솔에서만 수행하세요.
- `enabled=false`는 앱 접근을 차단합니다. 이미 발급된 로그인 세션을 즉시 강제 폐기하는 기능은 아닙니다. 다만 Firestore 데이터 조회는 차단됩니다.
- 비밀번호, 서비스 계정 JSON, API 관리자 비밀키를 HTML/공개 저장소에 저장하지 마세요.
- Firebase 무료 할당량, GitHub 무료 이용 조건, 주가 제공처 제한은 변경될 수 있습니다. 초과 시 실패할 수 있으며 자동 과금을 보장하지 않습니다.
- pykrx 비공식 데이터 수집이 실패하면 갱신되지 않을 수 있습니다. 자동 거래 기능은 없습니다.
- 종목 점수와 목표 가격은 단순 규칙 기반 참고치이며 투자 수익을 보장하지 않습니다.

## v1.3 당일 동향 및 추천 근거
- 각 종목 클릭 시 당일 시가·고가·저가·거래량·등락률, 장중 흐름 요약을 확인합니다.
- 추천 사유는 이동평균선, RSI, 20일 수익률, 거래량 배수 등 점수에 사용한 기술적 지표로 생성됩니다.
- 위험 신호를 별도로 표시하며, 분석 기준일과 데이터 갱신 시각을 함께 확인할 수 있습니다.
- 기존 Firestore 데이터는 새 필드가 없으므로 GitHub Actions의 `Daily KRX update`를 한 번 실행해야 설명이 나타납니다.
- 당일 동향은 실시간 뉴스 요약이 아니라 해당 거래일의 가격·거래량 통계입니다.
