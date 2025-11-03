# Profile 분석 기능 상세 분석

## 개요

BatteryDataTool.py에서 추출할 **Profile 분석 4가지 기능**에 대한 상세 분석 문서입니다.
배터리 성능 데이터 분석을 위한 핵심 기능으로, 전압/전류 프로파일, dQ/dV, DCIR 등을 분석합니다.

---

## 1. 충전 Step 확인

### 1.1 기능 개요
- **원본 함수**: `step_confirm_button()` (line 8833)
- **목적**: Step charge 프로파일 분석
- **연속성**: 비연속 (Discrete) → **연속 추가 필요**
- **데이터 타입**: 성능 (Performance)
- **지원 사이클러**: PNE, Toyo

### 1.2 데이터 처리 흐름
```
1. 파라미터 초기화
   └─> Profile_ini_set() → [firstCrate, mincapacity, CycleNo, smoothdegree, ...]

2. 경로 및 사이클 번호 설정
   ├─> 경로: pne_path_setting()[0]
   └─> 사이클: convert_steplist(self.stepnum.toPlainText())
       예) "3 4 5 8-9" → [3, 4, 5, 8, 9]

3. 데이터 로드 (개별 사이클)
   ├─> PNE: pne_step_Profile_data(FolderBase, Step_CycNo, mincapacity, firstCrate)
   └─> Toyo: toyo_step_Profile_data(FolderBase, Step_CycNo, mincapacity, firstCrate)

4. 추출 데이터
   └─> [mincapacity, df.stepchg]
       df.stepchg 컬럼: [TimeMin, SOC, Vol, Crate, Temp]

5. 그래프 생성 (6 subplot)
   ├─> ax1: Voltage vs Time (3가지 뷰)
   ├─> ax2: Voltage vs Time (반복)
   ├─> ax3: Voltage vs Time (반복)
   ├─> ax4: C-rate vs Time
   ├─> ax5: SOC vs Time
   └─> ax6: Temperature vs Time

6. Excel/ECT 내보내기 (옵션)
   ├─> Excel: TimeMin, SOC, Vol, Crate, Temp 컬럼
   └─> ECT CSV: Time, Voltage, Current, Temp
```

### 1.3 주요 파라미터

#### 입력 파라미터 (Profile_ini_set 반환값)
```python
firstCrate = float(self.ratetext.text())              # 기본값: 0.2
mincapacity = ...                                      # 용량 설정
CycleNo = convert_steplist(self.stepnum.toPlainText()) # [2] 또는 [3,4,5,8,9]
smoothdegree = int(self.smooth.text())                 # 0 (자동)
mincrate = float(self.cutoff.text())                   # 0
dqscale = float(self.dqdvscale.text())                 # 1
vol_y_hlimit = float(self.volrngyhl.text())            # 2.5
vol_y_llimit = float(self.volrngyll.text())            # 4.7
vol_y_gap = float(self.volrnggap.text())               # 0.1
```

#### 그래프 레이아웃 옵션
```python
if self.CycProfile.isChecked():  # 사이클 통합 (기본값)
    # 외부 루프: 폴더
    # 내부 루프: 채널 → 사이클
    # 결과: 폴더별 탭, 각 탭에 모든 채널의 모든 사이클

else:  # self.CellProfile.isChecked() - 셀별 통합
    # 외부 루프: 사이클
    # 내부 루프: 폴더 → 채널
    # 결과: 사이클별 탭, 각 탭에 모든 폴더의 모든 채널
```

### 1.4 출력 구조

#### 그래프 레이아웃 (6 subplot, 2x3)
```
┌─────────────┬─────────────┬─────────────┐
│ Voltage vs  │ Voltage vs  │ Voltage vs  │
│ Time (1)    │ Time (2)    │ Time (3)    │
│             │             │             │
├─────────────┼─────────────┼─────────────┤
│ C-rate vs   │ SOC vs      │ Temperature │
│ Time        │ Time        │ vs Time     │
│             │             │             │
└─────────────┴─────────────┴─────────────┘
```

#### Excel 구조 (saveok 체크 시)
```
시트명: 폴더명 또는 "전체"
컬럼: TimeMin, SOC, Vol, Crate, Temp
데이터: 선택된 모든 사이클의 시계열 데이터
```

#### ECT CSV 구조 (ect_saveok 체크 시)
```
컬럼: Time, Voltage, Current, Temp
형식: 쉼표 구분 CSV
용도: ECT 소프트웨어 호환
```

### 1.5 연속 경로 지원 추가 필요사항

**현재 상태**: 개별 사이클만 처리 (예: [3, 4, 5])
```python
for Step_CycNo in CycleNo:  # 각 사이클 독립 처리
    temp = pne_step_Profile_data(FolderBase, Step_CycNo, ...)
```

**추가 필요**: 사이클 범위 연속 처리
```python
# 사용자 입력: "3-5" (사이클 3, 4, 5를 하나의 연속 데이터로)
if "-" in self.stepnum.toPlainText():
    Step_CycNo, Step_CycEnd = map(int, cycle_range.split("-"))
    # continue 함수 사용 (이미 존재)
    temp = pne_step_Profile_continue_data(FolderBase, Step_CycNo, Step_CycEnd, ...)
```

---

## 2. 방전 확인

### 2.1 기능 개요
- **원본 함수**: `dchg_confirm_button()` (line 9437)
- **목적**: Discharge 프로파일 상세 분석 (dQ/dV 포함)
- **연속성**: 비연속 (Discrete) → **연속 추가 필요**
- **데이터 타입**: 성능 (Performance)
- **지원 사이클러**: PNE, Toyo

### 2.2 데이터 처리 흐름
```
1. 파라미터 초기화
   └─> Profile_ini_set() (충전 Step과 동일)

2. 데이터 로드
   ├─> PNE: pne_dchg_Profile_data(FolderBase, Step_CycNo, mincapacity, firstCrate)
   └─> Toyo: toyo_dchg_Profile_data(FolderBase, Step_CycNo, mincapacity, firstCrate)

3. 추출 데이터
   └─> [mincapacity, df.Profile]
       df.Profile 컬럼: [TimeMin, SOC, Energy, Vol, Crate, dQdV, dVdQ, Temp]

4. dQ/dV 처리
   ├─> Smoothing: savgol_filter(Vol, smoothdegree, 3)
   ├─> dQ/dV = ΔQ / ΔV
   └─> dV/dQ = ΔV / ΔQ

5. 그래프 생성 (6 subplot)
   ├─> ax1: DOD vs Voltage
   ├─> ax2: dQ/dV vs Voltage (또는 Voltage vs dQ/dV)
   ├─> ax3: DOD vs Voltage (반복)
   ├─> ax4: DOD vs dV/dQ
   ├─> ax5: DOD vs C-rate
   └─> ax6: DOD vs Temperature

6. Excel 내보내기
   └─> DOD(Depth of Discharge), Vol, dQdV, dVdQ, Crate, Temp
```

### 2.3 충전 Step과의 차이점

| 항목 | 충전 Step | 방전 |
|------|----------|------|
| **X축** | SOC (State of Charge) | DOD (Depth of Discharge) |
| **데이터** | stepchg (기본 프로파일) | Profile (dQ/dV 포함) |
| **dQ/dV** | 없음 | ✅ 포함 (smoothing 적용) |
| **Smoothing** | 사용 안 함 | savgol_filter 사용 |
| **에너지** | 없음 | Energy 컬럼 포함 |

### 2.4 dQ/dV 계산 상세

#### Smoothing 파라미터
```python
if smoothdegree == 0:  # 자동
    smoothdegree = len(df.Profile) / 30
    if smoothdegree % 2 == 0:
        smoothdegree += 1  # 홀수로 만들기

Vol_smt = savgol_filter(df.Profile["Vol"], smoothdegree, 3)
```

#### dQ/dV 및 dV/dQ 계산
```python
# dQ/dV: 전압 변화에 대한 용량 변화율
dQdV = np.gradient(df.Profile.index) / np.gradient(Vol_smt)

# dV/dQ: 용량 변화에 대한 전압 변화율
dVdQ = np.gradient(Vol_smt) / np.gradient(df.Profile.index)
```

#### X/Y 축 교환 옵션
```python
if self.chk_dqdv.isChecked():
    ax2.plot(Vol_smt, dQdV)  # Voltage vs dQ/dV
else:
    ax2.plot(dQdV, Vol_smt)  # dQ/dV vs Voltage (기본)
```

### 2.5 출력 구조

#### 그래프 레이아웃 (6 subplot, 2x3)
```
┌─────────────┬─────────────┬─────────────┐
│ DOD vs      │ dQ/dV vs    │ DOD vs      │
│ Voltage     │ Voltage     │ Voltage     │
│             │ (switchable)│             │
├─────────────┼─────────────┼─────────────┤
│ DOD vs      │ DOD vs      │ DOD vs      │
│ dV/dQ       │ C-rate      │ Temperature │
│             │             │             │
└─────────────┴─────────────┴─────────────┘
```

---

## 3. 율변 충전 확인

### 3.1 기능 개요
- **원본 함수**: `rate_confirm_button()` (line 9013)
- **목적**: Rate capability 프로파일 분석
- **연속성**: 비연속 (Discrete) → **연속 추가 필요**
- **데이터 타입**: 성능 (Performance)
- **지원 사이클러**: PNE, Toyo

### 3.2 데이터 처리 흐름
```
1. 파라미터 초기화
   └─> Profile_ini_set() (충전 Step과 동일)

2. 데이터 로드
   ├─> PNE: pne_rate_Profile_data(FolderBase, Step_CycNo, mincapacity, firstCrate)
   └─> Toyo: toyo_rate_Profile_data(FolderBase, Step_CycNo, mincapacity, firstCrate)

3. 추출 데이터
   └─> [mincapacity, df.rateProfile]
       df.rateProfile 컬럼: [TimeMin, SOC, Vol, Crate, Temp]

4. 그래프 생성 (6 subplot)
   └─> 충전 Step과 동일한 레이아웃

5. ECT CSV 내보내기 지원
   └─> Time, Voltage, Current, Temp
```

### 3.3 충전 Step과의 차이점

| 항목 | 충전 Step | 율변 충전 |
|------|----------|----------|
| **용도** | 일반 Step 충전 | Rate capability 테스트 |
| **데이터** | stepchg | rateProfile |
| **C-rate 변화** | 일정 | 다양한 C-rate 포함 |
| **ECT 내보내기** | ✅ 지원 | ✅ 지원 |

### 3.4 Rate Capability 분석 특징

Rate capability 테스트는 다양한 C-rate에서의 성능을 평가:
- 0.1C, 0.2C, 0.5C, 1C, 2C 등 다양한 속도
- C-rate에 따른 용량 변화 확인
- 그래프에서 C-rate 변화가 명확히 나타남

---

## 4. HPPC/GITT (DCIR)

### 4.1 기능 개요
- **원본 함수**: `dcir_confirm_button()` (line 9813)
- **목적**: DCIR (DC Internal Resistance) 프로파일 분석
- **연속성**: 비연속 (Discrete) → **연속 추가 필요**
- **데이터 타입**: 성능 (Performance)
- **지원 사이클러**: PNE만 (⭐ **Toyo 추가 필요**)

### 4.2 데이터 처리 흐름
```
1. 파라미터 초기화
   └─> Profile_ini_set()

2. 사이클 범위 파싱 (연속 처리 지원)
   └─> if "-" in self.stepnum.toPlainText():
       Step_CycNo, Step_CycEnd = map(int, cycle_range.split("-"))

3. 사이클러 감지 및 차단
   └─> if not check_cycler(cyclefolder):  # Toyo
       err_msg("PNE 충방전기 사용 요청", "DCIR은 PNE...")
       continue  # Toyo는 현재 지원 안 함

4. 데이터 로드 (PNE만)
   └─> pne_dcir_Profile_data(FolderBase, Step_CycNo, Step_CycEnd,
                             mincapacity, firstCrate)

5. 추출 데이터
   └─> [mincapacity, df]
       df: SOC별 DCIR 값 (0.1s, 1s, 10s, 20s, RSS)

6. 그래프 생성 (4 subplot)
   ├─> ax1: SOC vs OCV/CCV
   ├─> ax2: SOC vs DCIR (5개 시간 스케일)
   ├─> ax3: Voltage vs SOC
   └─> ax4: OCV vs DCIR

7. Excel 내보내기
   └─> SOC, OCV, CCV, DCIR_0.1s, DCIR_1s, DCIR_10s, DCIR_20s, DCIR_RSS
```

### 4.3 DCIR 측정 원리

#### 펄스 타이밍 분석
```python
# PNE 데이터에서 20초 펄스 종료점 감지
dcir_base = Profileraw.loc[Profileraw["StepTime"] == 20]

# 4개 펄스 전류 추출
Curr1, Curr2, Curr3, Curr4 = dcir_base["Curr"].values[:4]

# C-rate 계산
Crate = [abs(c) * 1000 / mincapacity for c in [Curr1, Curr2, Curr3, Curr4]]
```

#### DCIR 계산 (5가지 시간 스케일)
```python
# 특정 시간대 전압 추출
times = [0.0, 0.2, 1.0, 10.0, 20.0]  # 초
voltages_at_times = {}

for t in times:
    voltages_at_times[t] = extract_voltage_at_time(profile, t)

# DCIR = ΔV / I
DCIR_0_1s = (V_rest - V_0_1s) / Current  # mΩ
DCIR_1s = (V_rest - V_1s) / Current
DCIR_10s = (V_rest - V_10s) / Current
DCIR_20s = (V_rest - V_20s) / Current

# RSS (Root Sum Square)
DCIR_RSS = sqrt(DCIR_10s^2 + DCIR_1s^2)
```

### 4.4 OCV/CCV 개념

- **OCV (Open Circuit Voltage)**: 개방 회로 전압 (휴지 상태)
- **CCV (Closed Circuit Voltage)**: 폐쇄 회로 전압 (부하 인가)
- **DCIR**: (OCV - CCV) / Current

### 4.5 Toyo DCIR 구현 필요사항

#### 현재 차단 코드 (line 9862)
```python
if not check_cycler(cyclefolder):
    err_msg("PNE 충방전기 사용 요청",
            "DCIR은 PNE 충방전기를 사용하여 측정 부탁 드립니다.")
    continue
```

#### 구현 필요 항목
1. **`toyo_dcir_Profile_data()` 함수 생성**
   - Toyo 데이터 구조에서 펄스 감지
   - Condition 변화를 이용한 휴지/펄스 구분
   - StepTime 대신 시간 차이 계산

2. **Toyo 펄스 감지 로직**
   ```python
   # PNE: StepTime 컬럼 사용
   dcir_base = Profileraw.loc[Profileraw["StepTime"] == 20]

   # Toyo: Condition 변화 + 시간 차이 계산
   # Condition: 0=휴지, 1=충전, 2=방전
   rest_to_pulse = (Condition == 0) → (Condition == 2)
   pulse_duration = TimeDiff == 20초
   ```

3. **데이터 구조 차이 처리**
   - PNE: 컬럼명이 명확 (StepTime, Curr, Vol)
   - Toyo: 다른 컬럼명 사용 가능 (매핑 필요)

### 4.6 출력 구조

#### 그래프 레이아웃 (4 subplot, 2x2)
```
┌──────────────────┬──────────────────┐
│ SOC vs OCV/CCV   │ SOC vs DCIR      │
│                  │ (5 time scales)  │
│                  │                  │
├──────────────────┼──────────────────┤
│ Voltage vs SOC   │ OCV vs DCIR      │
│                  │                  │
│                  │                  │
└──────────────────┴──────────────────┘
```

#### Excel 구조
```
컬럼: SOC, OCV, CCV, DCIR_0.1s, DCIR_1s, DCIR_10s, DCIR_20s, DCIR_RSS
데이터: SOC별 저항 값
용도: SOC-DCIR 관계 분석
```

---

## 통합 설계를 위한 공통 패턴 분석

### 공통 코드 패턴

#### 1. 초기화 패턴 (모든 Profile 함수 공통)
```python
self.[Button].setDisabled(True)
firstCrate, mincapacity, CycleNo, smoothdegree, mincrate, dqscale, dvscale = self.Profile_ini_set()
```

#### 2. 사이클 번호 파싱 패턴
```python
# 현재: 공백/개별 숫자만
CycleNo = convert_steplist(self.stepnum.toPlainText())
# 예) "3 4 5 8-9" → [3, 4, 5, 8, 9]

# DCIR만: 범위 지원
if "-" in self.stepnum.toPlainText():
    Step_CycNo, Step_CycEnd = map(int, cycle_range.split("-"))
```

#### 3. 데이터 로드 패턴
```python
if not check_cycler(cyclefolder):  # Toyo
    temp = toyo_XXX_Profile_data(...)
else:  # PNE
    temp = pne_XXX_Profile_data(...)

mincapacity = temp[0]
df = temp[1]
```

#### 4. 그래프 생성 패턴
```python
# Step/Rate/Chg/Dchg: 6 subplot
fig, ((ax1, ax2, ax3), (ax4, ax5, ax6)) = plt.subplots(
    nrows=2, ncols=3, figsize=(14, 8)
)

# DCIR: 4 subplot
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(
    nrows=2, ncols=2, figsize=(14, 8)
)
```

#### 5. ECT 내보내기 패턴 (Step/Rate만)
```python
if self.ect_saveok.isChecked() and save_file_name:
    ect_df = pd.DataFrame({
        'Time': df.stepchg["TimeMin"] * 60,  # 분 → 초
        'Voltage': df.stepchg["Vol"],
        'Current': df.stepchg["Crate"] * mincapacity / 1000,
        'Temp': df.stepchg["Temp"]
    })
    ect_df.to_csv(ect_filename, index=False)
```

### 중복 코드 비율

| 코드 영역 | 중복 비율 | 설명 |
|----------|----------|------|
| 초기화 로직 | 98% | Profile_ini_set() 공통 |
| 경로 설정 | 95% | pne_path_setting() 공통 |
| 사이클러 감지 | 100% | check_cycler() 공통 |
| 그래프 생성 | 80% | 6 subplot vs 4 subplot |
| Excel 내보내기 | 85% | pd.ExcelWriter 패턴 |
| ECT 내보내기 | 100% | Step/Rate 동일 |
| 진행률 추적 | 100% | progress() 함수 |

**전체 중복 코드 추정**: **75-85%**

---

## 연속 경로 지원 통합 전략

### 현재 vs 목표

#### 현재 상태
```python
# Step/Rate/Chg/Dchg: 개별 사이클만
for Step_CycNo in CycleNo:  # [3, 4, 5, 8, 9]
    temp = pne_step_Profile_data(FolderBase, Step_CycNo, ...)

# DCIR: 범위 지원
if "-" in self.stepnum.toPlainText():
    Step_CycNo, Step_CycEnd = map(int, cycle_range.split("-"))
    temp = pne_dcir_Profile_data(FolderBase, Step_CycNo, Step_CycEnd, ...)
```

#### 목표 상태
```python
# 모든 Profile 함수에 범위 지원 추가
cycle_input = self.stepnum.toPlainText()

if "-" in cycle_input:
    # 연속 처리
    Step_CycNo, Step_CycEnd = parse_cycle_range(cycle_input)
    temp = pne_XXX_Profile_continue_data(FolderBase, Step_CycNo, Step_CycEnd, ...)
else:
    # 개별 처리
    CycleNo = convert_steplist(cycle_input)
    for Step_CycNo in CycleNo:
        temp = pne_XXX_Profile_data(FolderBase, Step_CycNo, ...)
```

### 구현 필요 함수

#### PNE (일부 이미 존재)
- ✅ `pne_Profile_continue_data()` - 이미 존재 (line 1050)
- 🔨 `pne_step_Profile_continue_data()` - 생성 필요
- 🔨 `pne_rate_Profile_continue_data()` - 생성 필요
- 🔨 `pne_chg_Profile_continue_data()` - 생성 필요
- 🔨 `pne_dchg_Profile_continue_data()` - 생성 필요
- ✅ `pne_dcir_Profile_data()` - 이미 범위 지원

#### Toyo
- ⚠️ `toyo_Profile_continue_data()` - 존재하지만 비활성화 (line 948)
- 🔨 `toyo_step_Profile_continue_data()` - 생성 필요
- 🔨 `toyo_rate_Profile_continue_data()` - 생성 필요
- 🔨 `toyo_chg_Profile_continue_data()` - 생성 필요
- 🔨 `toyo_dchg_Profile_continue_data()` - 생성 필요
- 🔨 `toyo_dcir_Profile_data()` - 생성 필요 (현재 미지원)

---

## 통합 전략

### 통합 가능한 부분

#### 1. Base Handler Class
```python
class ProfileAnalysisHandler:
    """Profile 분석 공통 핸들러"""

    def __init__(self, config: AnalysisConfig):
        self.config = config

    def _initialize(self):
        """공통 초기화 - Profile_ini_set()"""
        pass

    def _parse_cycle_input(self, cycle_input: str):
        """사이클 입력 파싱"""
        if "-" in cycle_input:
            return "continuous", parse_range(cycle_input)
        else:
            return "discrete", convert_steplist(cycle_input)

    def _load_profile_data(self, path, cycler_type, profile_mode, cycle_info):
        """데이터 로드 디스패치"""
        mode, cycles = cycle_info

        if mode == "continuous":
            start, end = cycles
            if cycler_type == "toyo":
                return self._load_toyo_continuous(path, profile_mode, start, end)
            else:
                return self._load_pne_continuous(path, profile_mode, start, end)
        else:
            return self._load_discrete(path, cycler_type, profile_mode, cycles)

    def _create_graph(self, data, profile_mode):
        """그래프 생성 - 프로파일 모드별 레이아웃"""
        if profile_mode == "dcir":
            return self._create_4subplot(data)
        else:
            return self._create_6subplot(data)

    def analyze(self, profile_mode: str):
        """메인 분석 메서드"""
        self._initialize()
        cycle_info = self._parse_cycle_input(self.config.cycle_input)
        paths = self._load_paths()

        for path in paths:
            cycler = self._detect_cycler(path)
            data = self._load_profile_data(path, cycler, profile_mode, cycle_info)
            self._create_graph(data, profile_mode)

        self._export_data(data)
```

#### 2. Strategy Pattern for Profile Types
```python
class StepProfileStrategy:
    """충전 Step 전략"""
    subplot_count = 6
    data_attr = "stepchg"
    supports_ect = True

class RateProfileStrategy:
    """율변 충전 전략"""
    subplot_count = 6
    data_attr = "rateProfile"
    supports_ect = True

class ChargeProfileStrategy:
    """충전 프로파일 전략"""
    subplot_count = 6
    data_attr = "Profile"
    requires_dqdv = True
    supports_ect = False

class DischargeProfileStrategy:
    """방전 프로파일 전략"""
    subplot_count = 6
    data_attr = "Profile"
    requires_dqdv = True
    use_dod = True  # SOC 대신 DOD 사용

class DCIRProfileStrategy:
    """DCIR 전략"""
    subplot_count = 4
    requires_pulse_detection = True
    supports_continuous = True  # 이미 범위 지원
```

### 추출 후 예상 코드 구조

```python
# 기존: 4개 함수 각각 250-350 라인 → 총 1,000-1,400 라인
# 통합 후:

# profile_handler.py (300 라인)
class ProfileAnalysisHandler:
    # 공통 로직 통합
    pass

# profile_strategies.py (200 라인)
class StepProfileStrategy: ...
class RateProfileStrategy: ...
class ChargeProfileStrategy: ...
class DischargeProfileStrategy: ...
class DCIRProfileStrategy: ...

# continuous_profile.py (150 라인)
# 연속 경로 처리 로직

# toyo_dcir.py (100 라인)
# Toyo DCIR 구현

# 총 750 라인 → 46% 코드 감소
```

---

## 크로스체크 검증 항목

### Profile 분석 검증 체크리스트

#### 1. 충전 Step
- [ ] Toyo/PNE 단일 경로: 6 subplot 데이터 일치
- [ ] Excel: TimeMin, SOC, Vol, Crate, Temp 일치
- [ ] ECT CSV: Time, Voltage, Current, Temp 포맷 일치
- [ ] 연속 경로 추가 후: 범위 처리 검증

#### 2. 방전
- [ ] dQ/dV 계산: smoothing 파라미터 일치
- [ ] dV/dQ 계산: 수치 정밀도 일치
- [ ] X/Y 축 교환: chk_dqdv 옵션 동작 일치
- [ ] DOD 계산: SOC 대신 DOD 축 일치
- [ ] 연속 경로 추가 후: 범위 처리 검증

#### 3. 율변 충전
- [ ] Rate profile 데이터: C-rate 변화 일치
- [ ] ECT CSV: 포맷 일치
- [ ] 연속 경로 추가 후: 범위 처리 검증

#### 4. HPPC/GITT
- [ ] PNE DCIR 계산: 5가지 시간 스케일 일치
- [ ] OCV/CCV 추출: 휴지/부하 전압 일치
- [ ] Toyo DCIR 추가 후: 펄스 감지 및 계산 검증
- [ ] 연속 경로: 이미 지원, 기존 로직 검증

### 수치 검증 기준
- 전압: ±0.001 V
- 전류: ±0.001 A
- SOC/DOD: ±0.0001%
- C-rate: ±0.001
- dQ/dV: ±0.001
- DCIR: ±0.01 mΩ
- 온도: ±0.1 °C

---

## 확장 기능 구현 우선순위

### Priority 1: Toyo DCIR 구현
1. Toyo 데이터 구조 분석
2. Condition 기반 펄스 감지 알고리즘
3. 시간 차이 계산 로직
4. DCIR 계산 (5가지 시간 스케일)
5. 크로스체크 검증

### Priority 2: Profile 연속 경로 지원
1. Step/Rate/Chg/Dchg에 범위 파싱 추가
2. PNE continue 함수 생성/활용
3. Toyo continue 함수 활성화
4. 크로스체크 검증

### Priority 3: 통합 아키텍처 구현
1. Base Handler 구현
2. Strategy Pattern 적용
3. 코드 중복 제거
4. 전체 크로스체크

---

## 결론

### 핵심 포인트
1. **4가지 Profile 분석 기능**은 75-85% 공통 코드 공유
2. **연속 경로 지원**이 DCIR에만 있고 나머지는 없음 → 통합 필요
3. **Toyo DCIR**이 없음 → 새로 구현 필요
4. **dQ/dV 처리**는 Chg/Dchg만 해당 → Strategy Pattern으로 분리
5. 통합 설계 시 **46% 코드 감소** 가능
6. **크로스체크 검증**으로 원본과 100% 일치 보장 필요

### 다음 단계
- 입력 인터페이스 분석 문서 작성
- 아키텍처 설계 문서 작성
- Toyo DCIR 구현 방안 상세 설계
