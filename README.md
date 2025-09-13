```
factors/
├─ README.md
├─ LICENSE
├─ CITATION.cff
├─ REPRODUCIBILITY.md              # 원클릭/원커맨드 재현 절차 요약
├─ CONTRIBUTING.md
├─ CODE_OF_CONDUCT.md
├─ .gitignore
├─ .dockerignore
├─ Makefile                         # make setup / make test / make reproduce / make docker-*
├─ pyproject.toml                   # 패키지/의존성(또는 setup.cfg/requirements.txt로 대체)
│
├─ .github/
│  └─ workflows/
│     ├─ ci.yml                     # 일반 CI: lint, unit test, 최소 통합 테스트(주로 CPU)
│     └─ docker-ci.yml              # Docker CI: CPU/GPU 이미지 빌드·태그·푸시
│
├─ docker/
│  ├─ Dockerfile.cpu                # CPU 전용 이미지(예: pytorch-cpu 또는 slim python)
│  ├─ Dockerfile.gpu                # GPU 전용 이미지(예: nvidia/cuda + pytorch)
│  ├─ entrypoint.sh                 # 공통 엔트리포인트(인자: config 경로 등)
│  ├─ compose.dev.cpu.yml           # 로컬 개발용(바인드 마운트, CPU)
│  ├─ compose.dev.gpu.yml           # 로컬 개발용(바인드 마운트, --gpus all)
│  └─ README.md                     # 이미지 빌드/실행 가이드
│
├─ envs/
│  ├─ conda-cpu.yml
│  ├─ conda-gpu.yml
│  ├─ pip-cpu.txt
│  └─ pip-gpu.txt
│
├─ src/
│  └─ factors/
│     ├─ __init__.py
│     ├─ effects.py                 # 주효과/교호작용 추정(CM 경로)
│     ├─ shap_fit.py                # SHAP-fit 최소제곱 복원(SF 경로)
│     ├─ score.py                   # 2-요인 근사 f̃, 목적함수 J, 벌점 R/C
│     ├─ optimizer.py               # 좌표개선/빔 탐색/제약 반영
│     ├─ pci.py                     # PCI 계산/표준화
│     ├─ bootstrap.py               # 불확실성·신뢰구간
│     ├─ io.py                      # 로그/결과/아티팩트 저장 규약
│     └─ utils.py                   # 시드고정, 타이머, 체크포인트 등
│
├─ configs/
│  ├─ global.yaml                   # 공통 가정/기준분포/로깅 디렉토리 규약
│  ├─ datasets/
│  │  ├─ concrete.yaml
│  │  ├─ car.yaml
│  │  └─ fmnist.yaml
│  ├─ ablations/
│  │  ├─ shrinkage_{low,mid,high}.yaml
│  │  ├─ risk_lambda_sweep.yaml
│  │  └─ design_{balanced,skewed}.yaml
│  └─ runs/
│     ├─ main.yaml                  # 메인 실험(논문 표/그림 재현)
│     └─ sanity.yaml                # CI에서 빠르게 도는 스모크 테스트 설정
│
├─ scripts/
│  ├─ download_data.sh              # 공개 데이터셋 자동 다운로드
│  ├─ run_experiment.py             # 단일 설정 실행(–config, –seed, –out)
│  ├─ reproduce_all.sh              # 논문 전표/그림/표 재현 파이프라인
│  ├─ make_tables_figs.py           # 결과에서 표/그림 생성
│  └─ check_env.py                  # CUDA/드라이버/버전 점검
│
├─ data/                            # (대용량은 비추적) 각 폴더에 README와 .gitkeep만
│  ├─ raw/.gitkeep
│  └─ processed/.gitkeep
│
├─ experiments/                     # 실행 산출물(가벼운 텍스트만 추적; 대용량은 .gitignore)
│  ├─ main/
│  │  ├─ concrete/
│  │  ├─ car/
│  │  └─ fmnist/
│  └─ ablation/
│     ├─ shrinkage/
│     ├─ risk_lambda/
│     └─ design/
│
├─ results/
│  ├─ logs/                         # 텍스트 로그
│  ├─ metrics/                      # csv/json (표/그림 생성에 사용)
│  ├─ figures/                      # 논문용 png/pdf
│  └─ tables/                       # 논문용 csv/tex
│
├─ tests/
│  ├─ unit/
│  │  ├─ test_effects.py
│  │  ├─ test_shap_fit.py
│  │  ├─ test_score.py
│  │  └─ test_optimizer.py
│  └─ integration/
│     └─ test_end_to_end_sanity.py  # configs/runs/sanity.yaml 로 빠른 e2e
│
├─ notebooks/
│  └─ analysis.ipynb                # 추가 해석/그림 스케치(선택)
│
└─ paper/
   ├─ FACTORS.tex                   # 논문 LaTeX(원한다면)
   ├─ sections/
   └─ images/
```
