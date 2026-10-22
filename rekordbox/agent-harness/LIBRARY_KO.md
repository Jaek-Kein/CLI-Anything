# 로컬 라이브러리 관리 — Jaek-Kein fork

2026-10-22 추가. CLI Hub와 MIDI 드라이버 없이 이 패키지만 사용합니다.
AI의 작품 조사·선곡은 Codex가 수행하고, CLI는 DB 조회와 변경을 담당합니다.
라이선스와 기존 저작권 고지는 원본 저장소의 것을 보존합니다.

## 실행

이 PC에는 아래 폴더의 `.venv`에 Python 3.12와 패키지를 설치했습니다.

```powershell
Set-Location F:\Programming\CLI-Anything\rekordbox\agent-harness
.\rekordbox.ps1 --help
.\rekordbox.ps1 --json status
.\rekordbox.ps1 --json library search "검색어"
.\rekordbox.ps1 --json library info TRACK_ID
.\rekordbox.ps1 library dump --out work\tracks.json
.\rekordbox.ps1 --json tag list
```

직접 실행도 가능합니다: `.\.venv\Scripts\cli-anything-rekordbox.exe`.
자동 탐지가 실패하거나 복사본을 사용하려면 **전역 옵션을 명령 앞에** 지정하세요.
앱이 Z: 등 다른 드라이브에 설치돼 있어도 `rekordbox3.settings`의 라이브러리 경로를 확인합니다.

```powershell
.\rekordbox.ps1 --db 'D:\Library\master.db' --json library count
```

다른 환경에서의 설치: Python 3.11 이상으로 `.venv`를 만들고
`.\.venv\Scripts\python.exe -m pip install -e .`를 실행합니다.
재생 제어가 필요한 경우에만 `-e '.[midi]'`로 MIDI 의존성을 추가합니다.
태그 기능에는 `[windows]`나 MIDI 추가 설치가 필요 없습니다.

## 곡 정보

`library search`, `info`, `dump`는 곡 ID, 제목, 아티스트, 앨범, 장르,
기존 분석 BPM, 키, 길이, 댓글, My Tag, 별점, 발매 연도, 파일 경로를 제공합니다.
`duration_seconds`가 기본 길이이며, `duration_ms`는 그 값의 1,000배입니다.
분석되지 않은 BPM·키는 비어 있을 수 있습니다. 이 CLI는 오디오를 새로 분석하지 않습니다.
출력과 JSON 파일은 UTF-8입니다. 곡 ID는 문자열로 취급합니다.

## 한 곡의 댓글·태그

`tag list`에서 `is_category: true`인 기존 분류의 ID를 확인하세요.
분류 이름과 내용은 자동으로 변경하지 않습니다.
아래 `TRACK_ID`, 분류 ID `4`, 작품명은 실제 값으로 바꿉니다.

```powershell
# 기본 동작은 미리보기: DB 변경과 백업 파일 생성 없음
.\rekordbox.ps1 --json library update TRACK_ID --append-comment '작품: 작품명 / 용도: OP' --add-tag 4 '작품명'

# 확인한 변경 적용: rekordbox를 종료한 상태에서 실행
.\rekordbox.ps1 --json library update TRACK_ID --append-comment '작품: 작품명 / 용도: OP' --add-tag 4 '작품명' --apply

# 연결만 해제. 태그 정의와 음원 파일은 유지
.\rekordbox.ps1 --json library update TRACK_ID --remove-tag 4 '작품명' --apply
```

`--append-comment`는 기존 댓글을 보존하고 동일 문구를 중복 추가하지 않습니다.
`--comment '내용'`은 댓글 전체를 교체합니다. 둘을 함께 지정할 수 없습니다.
`--label '작품명'`은 rekordbox의 **라벨(원래 음반사 정보) 필드**를 설정합니다.
My Tag와 별도이며, 기존 라벨을 바꾸므로 현재 값을 확인한 뒤 사용하세요.
`--clear-label`은 이 필드를 비웁니다. 음원 파일에 기록된 음반사 태그는 바꾸지 않습니다.
라벨은 `library info/search/dump`의 `label`과 `label_id`로 확인합니다.
태그는 기존 분류 아래에서 이름이 일치하면 재사용하고, 없으면 생성합니다.
동명곡은 제목으로 수정하지 않고 정확한 ID를 사용합니다.
이 기능은 rekordbox의 댓글·My Tag만 변경하며 MP3/FLAC 파일의 태그는 건드리지 않습니다.

## Codex의 일괄 작업

1. `library dump`의 곡 정보로 작품·OP/ED·커버·리믹스 여부를 조사합니다.
2. 확인된 곡만 `examples/anime-tags.json` 형식으로 `work/`에 기록합니다.
3. `library apply FILE`로 전체 변경을 미리 봅니다.
4. `library apply FILE --apply`로 저장합니다.

```powershell
.\rekordbox.ps1 --json library apply work\anime-tags.json
.\rekordbox.ps1 --json library apply work\anime-tags.json --apply
```

한 파일에 `changes`를 여러 개 넣을 수 있습니다. `expected_title`은 대상 확인용입니다.
`expected_comment`와 `expected_tags`도 지정하면 기존 값이 달라졌을 때 거부합니다.
`expected_tags`는 `category_id`와 `name`으로 된 객체 배열이며 현재 태그 전체와 비교합니다.
`comment`는 문자열 또는 null, `append_comment`는 비어 있지 않은 문자열입니다.
`add_tags`와 `remove_tags`도 같은 객체 배열을 사용합니다.
`label`(비어 있지 않은 문자열 또는 null), `expected_label`, `expected_artist`도 지원합니다.
예: `{"track_id":"123","expected_label":null,"label":"약캐 토모자키 군"}`.
일괄 변경 시 `expected_label`을 사용하면 기존 라벨을 뜻하지 않게 덮어쓰는 일을 막을 수 있습니다.
오타로 인한 의도치 않은 변경을 막기 위해 알 수 없는 필드는 거부합니다.
같은 곡의 변경은 한 항목으로 합쳐야 합니다.

## 백업과 되돌리기

새 메타데이터 명령은 적용 시 다음을 수행합니다.

- rekordbox 실행 중이면 거부하며, 강제 적용·백업 생략 옵션을 제공하지 않습니다.
- 모든 항목을 먼저 검증하고 하나의 DB 트랜잭션으로 처리합니다.
- DB 옆 `cli-anything-backups/<시각-고유번호>/`에 DB와 존재하는 WAL 파일을 복사합니다.
  SHM은 SQLite가 재생성하는 잠금 인덱스이므로 복사하지 않습니다.
- 같은 폴더에 변경 내역 `changes.json`과 역변경 계획 `undo.json`을 기록합니다.
- 실행 중 오류가 나거나 커밋 직전에 rekordbox 실행이 감지되면 DB 변경을 롤백합니다.

적용 결과의 `undo_file`을 같은 `library apply` 명령으로 미리보기·적용할 수 있습니다.
이후 댓글·태그가 바뀌었거나 다른 DB라면 덮어쓰지 않고 거부합니다.
되돌리기는 해당 곡의 댓글·라벨·태그 연결을 복구합니다. 새로 생성한 라벨·태그 정의는 남깁니다.
역변경 파일은 커밋 전에 준비하므로 적용 결과가 `applied: true`인 작업의 파일만 사용하세요.
`changes.json`의 `applied: false`는 커밋 전에 기록한 계획 상태이며 성공 여부 기록이 아닙니다.

조회·미리보기 연결에는 SQLite `query_only`를 설정합니다.
기존 `playlist create/add/clear`의 즉시 쓰기·`--force` 동작은 그대로이므로 구분하세요.
컬렉션 등록 해제·음원 파일 삭제는 이 버전에서 추가하지 않았습니다.

## 검증 범위

암호화된 임시 DB 테스트와 실제 rekordbox 7.2.14 DB **복사본**에서 읽기,
Unicode 댓글·태그 생성/연결, 중복 실행, 역변경, 무결성을 검증합니다.
실제 라이브러리에 적용하거나 rekordbox GUI·클라우드 동기화·USB Export에 반영되는지는
별도의 확인이 필요합니다. 원본 DB를 테스트 대상으로 쓰지 않습니다.

```powershell
.\.venv\Scripts\python.exe -m pytest cli_anything\rekordbox\tests -q --basetemp work\pytest
```
