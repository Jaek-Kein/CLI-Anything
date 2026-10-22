# RekordboxCLI

rekordbox 컬렉션을 조회하고 곡의 라벨·댓글·My Tag를 관리하는 독립 CLI입니다.
[CLI-Anything](https://github.com/HKUDS/CLI-Anything)의 rekordbox 패키지에서 분리했습니다.
CLI Hub나 다른 앱의 코드를 설치할 필요가 없습니다.

이 프로젝트는 [Jaek-Kein/CLI-Anything의 RecordboxCLI 브랜치](https://github.com/Jaek-Kein/CLI-Anything/tree/RecordboxCLI)에서 개발합니다.
`main`은 기존 CLI-Anything 구조를 유지합니다. 브랜치 이름은 **RecordboxCLI**입니다.

## 설치

Python 3.11 이상과 rekordbox 6/7이 필요합니다. 이 PC에서는 Python 3.12와 rekordbox 7.2.14로 사용했습니다.

```powershell
git clone --branch RecordboxCLI --single-branch https://github.com/Jaek-Kein/CLI-Anything.git RekordboxCLI
cd RekordboxCLI
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\rekordbox.exe --help
```

가상환경을 활성화하면 `rekordbox`를 바로 실행할 수 있습니다.
기존 `cli-anything-rekordbox` 명령과 `python -m cli_anything.rekordbox`도 지원합니다.
프로젝트에 포함된 `rekordbox.ps1`은 가상환경 Python으로 CLI를 실행합니다.

## 라이브러리 관리

```powershell
rekordbox --json library search "ClariS" --limit 100
rekordbox --json library info TRACK_ID
rekordbox --json tag list

# 기본값은 변경 미리보기입니다.
rekordbox --json library update TRACK_ID --label "작품명"

# rekordbox 저장·종료 후 실제 적용합니다.
rekordbox --json library update TRACK_ID --label "작품명" --apply
rekordbox --json library apply changes.json --apply
```

- 원본 라이브러리의 제목·아티스트·앨범·BPM·조성·라벨·댓글·My Tag 등을 조회합니다.
- 라벨은 rekordbox의 음반사 필드이며 My Tag와 별도입니다.
- 메타데이터 수정은 미리보기가 기본이고, 적용 시 백업과 되돌리기 manifest를 생성합니다.
- 곡의 음원 파일을 수정하지 않습니다. DB 수정 전에는 rekordbox를 저장하고 종료합니다.
- 작품명 조사와 선곡은 Codex가 수행하고 CLI가 확인·변경을 담당합니다.

상세 사용법은 [한국어 라이브러리 가이드](LIBRARY_KO.md),
명령 전체는 [기능 문서](REKORDBOX.md)를 참고하세요.
에이전트용 지침은 [SKILL.md](skills/cli-anything-rekordbox/SKILL.md)에 있습니다.

## 선택 기능과 개발

라이브러리 관리에는 MIDI 드라이버가 필요하지 않습니다.
MIDI 재생 제어를 사용하는 경우에만 `pip install -e '.[midi]'`로 추가 의존성을 설치합니다.
가상 MIDI 포트와 rekordbox 매핑 설정도 별도로 필요합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m pytest
```

자동 테스트는 가상 암호화 DB를 사용하며 실제 음악 컬렉션을 수정하지 않습니다.
실제 곡을 대상으로 테스트할 때는 먼저 사용자에게 대상 곡을 확인합니다.

## 출처와 라이선스

상위 저장소의 [Apache-2.0 LICENSE](LICENSE), 원래 패키지의 MIT 표기 및 저작권 고지를 보존했습니다.
상위 저장소와 패키지의 라이선스 표기가 서로 다르므로 이 분리가 라이선스 변경을 의미하지는 않습니다.
상세 출처와 수정 사항은 [NOTICE](NOTICE)를 참고하세요.
