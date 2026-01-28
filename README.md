# sportslab

스포츠 관련 실험용 프로젝트 모음입니다. 현재 리포에는 간단한 백엔드(파이썬), 프론트엔드(Next.js), Docker/CI 설정이 포함되어 있습니다.

## 구성 요소

### 1) Docker Compose (루트)
- 파일: `docker-comporse.yml`
- 서비스: `dashboard`
  - 이미지: `python:3.9-slim`
  - 컨테이너명: `sportslab`
  - 포트: `3010:3010`
  - 동작: `pip install -r requirements.txt` 후 `streamlit run app.py --server.port 3010`

> 참고
> - `docker-comporse.yml` 파일명은 일반적인 `docker-compose.yml`과 다릅니다.
> - 루트에 `requirements.txt` 및 `app.py`가 있어야 정상 구동됩니다. 현재 저장소에는 `backend/app.py`만 존재합니다.

### 2) 백엔드 (backend)
- 파일: `backend/Dockerfile`
  - 베이스 이미지: `python:3.9-slim`
  - 실행: `python app.py`
- 파일: `backend/app.py`
  - 콘솔 출력 및 60초 간격 루프를 도는 간단한 예제 코드

### 3) 프론트엔드 (frontend)
- Next.js 기반 (React 19)
- 주요 스크립트
  - `pnpm dev` / `npm run dev`: 개발 서버
  - `pnpm build` / `npm run build`: 빌드
  - `pnpm start` / `npm run start`: 프로덕션 실행
  - `pnpm lint` / `npm run lint`: 린트
- 버전 (package.json 기준)
  - `next`: 16.1.6
  - `react`, `react-dom`: 19.2.3

### 4) GitHub Actions
- 파일: `.github/workflows/deploy.yml`
- 동작: `main` 브랜치 push 시 Docker 이미지 빌드 및 Docker Hub로 push
- 이미지 태그 예시: `mydockerid/sports-dashboard:latest`
  - 실제 사용 시 본인 Docker Hub ID/리포지토리명으로 변경 필요

## 실행 방법

### 프론트엔드
```bash
cd frontend
pnpm dev
```

### 백엔드 (로컬)
```bash
cd backend
python app.py
```

### Docker Compose
```bash
docker compose -f docker-comporse.yml up
```

## 디렉터리 구조
```
/
  docker-comporse.yml
  backend/
    Dockerfile
    app.py
  frontend/
    package.json
    ...
  .github/
    workflows/
      deploy.yml
```
