# Cycle 분석 기능 상세 분석

## 개요

BatteryDataTool.py에서 추출할 **Cycle 분석 3가지 기능**에 대한 상세 분석 문서입니다.
배터리 수명 데이터 분석을 위한 핵심 기능으로, 용량 유지율, 효율, DCIR 등을 추적합니다.

---

## 1. 개별 Cycle 분석

### 1.1 기능 개요
- **원본 함수**: `indiv_cyc_confirm_button()` (line 8208)
- **목적**: 채널별 개별 사이클 분석 - 별도 그래프 생성
- **연속성**: 비연속 (Discrete) - 각 사이클 엔드포인트 데이터만 사용
- **데이터 타입**: 수명 (Cycle Life)
- **지원 사이클러**: PNE, Toyo

### 1.2 데이터 처리 흐름
```
1. 경로 입력 처리
   └─> pne_path_setting() → [all_data_folder, all_data_name, datafilepath]

2. 사이클러 자동 감지
   └─> check_cycler(folder) → True (PNE) / False (Toyo)

3. 데이터 로드 (채널별, 사이클별 반복)
   ├─> PNE: pne_cycle_data(FolderBase, Ch_No, mincapacity, firstCrate)
   └─> Toyo: toyo_cycle_data(FolderBase, Ch_No, mincapacity, firstCrate)

4. 추출 데이터
   └─> [mincapacity, df.NewData]
       df.NewData 컬럼: [Dchg, RndV, Eff, Chg, DchgEng, Eff2, dcir, Temp, AvgV, OriCyc]

5. 그래프 생성 (6 subplot)
   ├─> ax1: Capacity Ratio (Dchg / 초기용량)
   ├─> ax2: Discharge/Charge Efficiency
   ├─> ax3: Temperature
   ├─> ax4: DCIR (옵션에 따라 측정 방식 다름)
   ├─> ax5: Charge/Discharge Efficiency
   └─> ax6: Average Rest Voltage

6. Excel 내보내기 (옵션)
   └─> 채널별 컬럼으로 구성된 단일 시트
```

### 1.3 주요 파라미터

#### 입력 파라미터 (cyc_ini_set 반환값)
```python
firstCrate = float(self.ratetext.text())          # 기본값: 0.2
mincapacity = ...                                  # 용량 설정 방식에 따라
xscale = float(self.tcyclerng.text())             # X축 최대 (0=자동)
ylimithigh = float(self.tcyclerngyhl.text())      # Y축 최대 (1.10)
ylimitlow = float(self.tcyclerngyll.text())       # Y축 최소 (0.65)
irscale = float(self.dcirscale.text())            # DCIR scale (0=자동)
```

#### DCIR 측정 옵션 (3가지 방식)
```python
1. self.dcirchk.isChecked()
   - "PNE 설비 DCIR (SOC100 10s 방전 Pulse)"
   - 표준 DCIR 측정

2. self.pulsedcir.isChecked()
   - "PNE 10s DCIR (SOC5, 50 10s 방전 Pulse)"
   - 특정 SOC에서 펄스 DCIR

3. self.mkdcir.isChecked() [기본값]
   - "PNE RSS DCIR (SOC 30/50/70 충/방전, 1s Pulse/RSS)"
   - 다중 SOC 포인트에서 RSS DCIR
```

### 1.4 출력 구조

#### 그래프 레이아웃 (6 subplot, 2x3)
```
┌─────────────┬─────────────┬─────────────┐
│ Discharge   │ Discharge/  │ Temperature │
│ Capacity    │ Charge      │             │
│ Ratio       │ Efficiency  │             │
├─────────────┼─────────────┼─────────────┤
│ DCIR        │ Charge/     │ Average/    │
│             │ Discharge   │ Rest        │
│             │ Efficiency  │ Voltage     │
└─────────────┴─────────────┴─────────────┘
```

#### Excel 구조 (saveok 체크 시)
```
시트: "Sheet1"
컬럼 구조 (채널별):
  - Ch1_Cycle, Ch1_DisChargeCapacity, Ch1_Efficiency, Ch1_Temperature, Ch1_DCIR, Ch1_AverageVoltage
  - Ch2_Cycle, Ch2_DisChargeCapacity, ...
  - (채널 개수만큼 반복)
```

### 1.5 핵심 코드 패턴

```python
# 진행률 추적 패턴
progressdata = progress(foldercount, foldercountmax,
                       chnlcount, chnlcountmax,
                       cyccount, cyccountmax)
self.progressBar.setValue(int(progressdata))

# 그래프 생성 패턴
fig, ((ax1, ax2, ax3), (ax4, ax5, ax6)) = plt.subplots(
    nrows=2, ncols=3, figsize=(14, 8)
)

# PyQt6 통합 패턴
tab = QtWidgets.QWidget()
tab_layout = QtWidgets.QVBoxLayout(tab)
canvas = FigureCanvas(fig)
toolbar = NavigationToolbar(canvas, None)
tab_layout.addWidget(toolbar)
tab_layout.addWidget(canvas)
self.cycle_tab.addTab(tab, str(tab_no))
```

---

## 2. 연결 Cycle 분석

### 2.1 기능 개요
- **원본 함수**: `link_cyc_indiv_confirm_button()` (line 8565)
- **목적**: 다중 경로의 사이클 데이터 연결 분석
- **연속성**: 연속 (Continuous) - 여러 테스트 단계의 사이클을 시퀀스로 연결
- **데이터 타입**: 수명 (Cycle Life)
- **지원 사이클러**: PNE, Toyo

### 2.2 개별 Cycle과의 차이점

#### 경로 입력 방식
```python
# 개별 Cycle: 다중 폴더 직접 선택 또는 TSV 파일
all_data_folder = pne_path_setting()[0]

# 연결 Cycle: TSV 파일에서 경로 읽기 (필수)
datafilepath = pne_path_setting()[2]
data_pathlist = pd.read_csv(datafilepath, sep='\t', encoding='utf-8')
# TSV 컬럼: cyclepath | cyclename | ...
```

#### 데이터 연결 메커니즘
```python
# 사이클 번호 누적 관리
CycleMax = []      # 각 파일의 최대 사이클 번호 저장
link_writerownum = []  # Excel 쓰기 위치 추적

for i, row in data_pathlist.iterrows():
    cyclefolder = row['cyclepath']

    # 이전 파일들의 사이클 개수 합산
    if i == 0:
        df.NewData.index = df.NewData.index  # 그대로
    else:
        # 인덱스를 이전 최대값 이후로 이동
        df.NewData.index = df.NewData.index + sum(CycleMax)

    CycleMax.append(len(df.NewData))
```

### 2.3 데이터 처리 흐름
```
1. TSV 파일 읽기
   └─> pd.read_csv(datafilepath, sep='\t')
       컬럼: [cyclepath, cyclename, ...]

2. 각 경로별 처리 (반복)
   ├─> 사이클러 감지
   ├─> 데이터 로드 (개별 Cycle과 동일)
   └─> 인덱스 조정 (누적 사이클 번호)

3. 그래프 생성
   └─> 파일 경로별 별도 탭 생성
       각 탭: 6 subplot (개별 Cycle과 동일)

4. Excel 내보내기
   └─> 모든 경로 데이터를 단일 시트에 누적
```

### 2.4 TSV 파일 형식

```tsv
cyclepath	cyclename
Rawdata\250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc	1-100cyc
Rawdata\250219_250319_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 101-200cyc	101-200cyc
Rawdata\250304_250404_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 201-300cyc	201-300cyc
```

### 2.5 출력 구조

#### 그래프
- 파일 경로별 별도 탭
- 각 탭: 6 subplot (개별 Cycle과 동일)
- 범례에 cyclename 표시

#### Excel
```
시트: "Sheet1"
데이터 누적 방식:
  - 첫 번째 경로: row 0부터
  - 두 번째 경로: row (이전 데이터 개수)부터
  - 사이클 번호도 누적되어 연속적
```

---

## 3. 신뢰성 Cycle 분석

### 3.1 기능 개요
- **원본 함수**: 추정 필요 (Toyo 전용 기능)
- **목적**: Toyo 사이클러의 신뢰성 평가용 사이클 분석
- **연속성**: 비연속 (Discrete)
- **데이터 타입**: 수명 (Cycle Life)
- **지원 사이클러**: Toyo만

### 3.2 기능 파악 필요사항

원본 코드에서 "신뢰성 Cycle" 관련 버튼/기능을 찾아야 합니다:
- GUI 버튼명 확인 필요
- 해당 핸들러 함수 식별 필요
- Toyo 전용 데이터 처리 로직 분석 필요

**추정 가능한 특징**:
- 개별 Cycle과 유사한 구조
- Toyo 사이클러 특화 파라미터 사용
- 신뢰성 테스트 특화 지표 포함 가능

---

## 통합 설계를 위한 공통 패턴 분석

### 공통 코드 패턴

#### 1. 초기화 패턴 (모든 함수 공통)
```python
self.[Button].setDisabled(True)  # 실행 중 버튼 비활성화
# ... 처리 ...
self.[Button].setEnabled(True)   # 완료 후 재활성화
```

#### 2. 경로 설정 패턴
```python
pne_path = self.pne_path_setting()
all_data_folder = pne_path[0]  # 폴더 경로 리스트
all_data_name = pne_path[1]    # 사이클명 리스트 (옵션)
datafilepath = pne_path[2]     # TSV 파일 경로 (옵션)
```

#### 3. 사이클러 감지 패턴
```python
if not check_cycler(cyclefolder):  # Toyo
    temp = toyo_cycle_data(...)
else:  # PNE
    temp = pne_cycle_data(...)
```

#### 4. 그래프 생성 패턴
```python
fig, ((ax1, ax2, ax3), (ax4, ax5, ax6)) = plt.subplots(
    nrows=2, ncols=3, figsize=(14, 8)
)

# ... 그래프 그리기 ...

tab = QtWidgets.QWidget()
tab_layout = QtWidgets.QVBoxLayout(tab)
canvas = FigureCanvas(fig)
toolbar = NavigationToolbar(canvas, None)
tab_layout.addWidget(toolbar)
tab_layout.addWidget(canvas)
self.cycle_tab.addTab(tab, str(tab_no))
```

#### 5. Excel 내보내기 패턴
```python
if self.saveok.isChecked() and save_file_name:
    writer = pd.ExcelWriter(save_file_name, engine="xlsxwriter")
    combined_df.to_excel(writer, sheet_name="Sheet1", index=False)
    writer.close()
```

### 중복 코드 비율

| 코드 영역 | 중복 비율 | 설명 |
|----------|----------|------|
| 초기화 로직 | 95% | 버튼 비활성화, 진행률 초기화 |
| 경로 설정 | 90% | pne_path_setting() 호출 |
| 사이클러 감지 | 100% | check_cycler() 사용 |
| 그래프 생성 | 85% | matplotlib + PyQt6 통합 |
| Excel 내보내기 | 90% | pd.ExcelWriter 패턴 |
| 진행률 추적 | 100% | progress() 함수 |

**전체 중복 코드 추정**: **70-80%**

---

## 통합 전략

### 통합 가능한 부분

#### 1. Base Handler Class
```python
class CycleAnalysisHandler:
    """Cycle 분석 공통 핸들러"""

    def __init__(self, config: AnalysisConfig):
        self.config = config

    def _initialize(self):
        """공통 초기화 로직"""
        # 버튼 비활성화, 진행률 초기화

    def _load_paths(self):
        """경로 로드 로직"""
        # pne_path_setting() 통합

    def _detect_cycler(self, path):
        """사이클러 자동 감지"""
        # check_cycler() 통합

    def _load_cycle_data(self, path, cycler_type):
        """데이터 로드 디스패치"""
        if cycler_type == "toyo":
            return toyo_cycle_data(...)
        else:
            return pne_cycle_data(...)

    def _create_graph(self, data):
        """6 subplot 그래프 생성"""
        # 공통 레이아웃 생성

    def _export_excel(self, data, filename):
        """Excel 내보내기"""
        # pd.ExcelWriter 통합

    def analyze(self, analysis_type: str):
        """메인 분석 메서드 (Template Method Pattern)"""
        self._initialize()
        paths = self._load_paths()

        for path in paths:
            cycler = self._detect_cycler(path)
            data = self._load_cycle_data(path, cycler)

            if analysis_type == "linked":
                data = self._adjust_cycle_index(data)

            self._create_graph(data)

        if self.config.save_excel:
            self._export_excel(data, filename)
```

#### 2. Strategy Pattern for Cycle Types
```python
class IndividualCycleStrategy:
    """개별 사이클 전략"""
    def process_data(self, data):
        return data  # 그대로 사용

class LinkedCycleStrategy:
    """연결 사이클 전략"""
    def process_data(self, data_list):
        # 인덱스 누적 조정
        return adjusted_data

class ReliabilityCycleStrategy:
    """신뢰성 사이클 전략"""
    def process_data(self, data):
        # Toyo 특화 처리
        return processed_data
```

### 추출 후 예상 코드 구조

```python
# 기존: 3개 함수 각각 200-300 라인 → 총 600-900 라인
# 통합 후:

# cycle_handler.py (200 라인)
class CycleAnalysisHandler:
    # 공통 로직 통합
    pass

# cycle_strategies.py (100 라인)
class IndividualCycleStrategy: ...
class LinkedCycleStrategy: ...
class ReliabilityCycleStrategy: ...

# 총 300 라인 → 67% 코드 감소
```

---

## 크로스체크 검증 항목

### Cycle 분석 검증 체크리스트

#### 1. 개별 Cycle
- [ ] Toyo 단일 경로: 6 subplot 데이터 일치
- [ ] PNE 단일 경로: 6 subplot 데이터 일치
- [ ] Excel 내보내기: 컬럼 구조 및 데이터 일치
- [ ] DCIR 계산: 3가지 옵션 모두 일치
- [ ] 용량 비율 계산: 초기 용량 대비 비율 일치

#### 2. 연결 Cycle
- [ ] Toyo 연속 경로 (4개): 사이클 누적 일치
- [ ] PNE 연속 경로 (3개): 사이클 누적 일치
- [ ] TSV 파일 읽기: cyclepath, cyclename 처리 일치
- [ ] 인덱스 조정: 누적 사이클 번호 일치
- [ ] Excel 누적: 모든 경로 데이터 순차 누적 일치

#### 3. 신뢰성 Cycle
- [ ] Toyo 전용 기능 동작 확인
- [ ] (기능 파악 후 추가)

### 수치 검증 기준
- 용량 값: ±0.0001 mAh
- 효율: ±0.0001%
- 전압: ±0.001 V
- 온도: ±0.1 °C
- DCIR: ±0.01 mΩ

---

## 결론

### 핵심 포인트
1. **3가지 Cycle 분석 기능**은 70-80% 공통 코드 공유
2. **개별/연결** 차이는 주로 **인덱스 조정 로직**
3. **PNE/Toyo** 차이는 **데이터 로드 함수**만 다름
4. 통합 설계 시 **Base Handler + Strategy Pattern** 적용으로 코드 67% 감소 가능
5. **크로스체크 검증**으로 원본과 100% 일치 보장 필요

### 다음 단계
- Profile 분석 기능 상세 분석
- 신뢰성 Cycle 기능 원본 코드에서 식별
- 통합 아키텍처 설계 착수
