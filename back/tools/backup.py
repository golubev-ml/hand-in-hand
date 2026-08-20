"""HIH-5: backup/restore — дамп и загрузка картинок и метаданных.

Использование внутри контейнера api:
    python -m tools.backup dump
    python -m tools.backup load /path/to/uploads-backup-YYYY-MM-DD-HHMM.tar.gz

Архив содержит:
    uploads/           — все файлы (оригинал + версии gallery/mail/mobile)
    pictures.json      — все поля таблицы pictures

Архивы сохраняются в /app/backup/uploads-backup-<datetime>.tar.gz
"""
import json
import shutil
import sys
import tarfile
from datetime import datetime
from pathlib import Path

# путь к пакету back/
_pkg = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_pkg))

from database import SessionLocal  # noqa: E402
from models import Picture  # noqa: E402

UPLOAD_DIR = _pkg / "uploads"
BACKUP_DIR = Path("/app/backup")


def _pic_to_dict(p: Picture) -> dict:
    d = {}
    for c in p.__table__.columns:
        v = getattr(p, c.name)
        if isinstance(v, datetime):
            v = v.isoformat()
        d[c.name] = v
    return d


def dump() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = Path("/tmp/backup-dump")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    (tmp / "uploads").mkdir()

    # 1. Копируем uploads
    if UPLOAD_DIR.exists():
        n = 0
        for f in UPLOAD_DIR.iterdir():
            if f.is_file():
                shutil.copy2(f, tmp / "uploads" / f.name)
                n += 1
        print(f"uploads: скопировано {n} файлов")

    # 2. Pictures JSON
    db = SessionLocal()
    try:
        pics = db.query(Picture).all()
        data = [_pic_to_dict(p) for p in pics]
        with open(tmp / "pictures.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"pictures.json: {len(data)} записей")
    finally:
        db.close()

    # 3. tar.gz
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    out = BACKUP_DIR / f"uploads-backup-{stamp}.tar.gz"
    with tarfile.open(out, "w:gz") as tar:
        tar.add(tmp / "uploads", arcname="uploads")
        tar.add(tmp / "pictures.json", arcname="pictures.json")
    print(f"OK: {out} ({out.stat().st_size / 1024:.1f} KiB)")
    shutil.rmtree(tmp)


def load(path: str) -> None:
    p = Path(path)
    if not p.exists():
        print(f"ERR: файл не найден: {p}", file=sys.stderr)
        sys.exit(1)

    tmp = Path("/tmp/backup-load")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()

    with tarfile.open(p, "r:gz") as tar:
        tar.extractall(tmp)

    # 1. uploads
    src_uploads = tmp / "uploads"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    if src_uploads.exists():
        for f in src_uploads.iterdir():
            if f.is_file():
                shutil.copy2(f, UPLOAD_DIR / f.name)
                n += 1
    print(f"uploads: восстановлено {n} файлов")

    # 2. pictures
    with open(tmp / "pictures.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    db = SessionLocal()
    try:
        for d in data:
            # парсим datetime
            for k in ("time", "sold_at", "status_changed_at"):
                v = d.get(k)
                d[k] = datetime.fromisoformat(v) if v else None
            existing = db.query(Picture).filter(Picture.id == d["id"]).first()
            if existing:
                for k, v in d.items():
                    if k != "id":
                        setattr(existing, k, v)
            else:
                db.add(Picture(**d))
        db.commit()

        # починка sequence
        from sqlalchemy import text
        db.execute(text(
            "SELECT setval('pictures_id_seq', COALESCE((SELECT MAX(id) FROM pictures), 0) + 1, false)"
        ))
        db.commit()
        print(f"pictures: загружено {len(data)} записей (upsert + sequence fix)")
    finally:
        db.close()

    shutil.rmtree(tmp)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("dump", "load"):
        print("Usage: python -m tools.backup dump|load <path>", file=sys.stderr)
        sys.exit(1)
    if sys.argv[1] == "dump":
        dump()
    else:
        if len(sys.argv) < 3:
            print("Usage: python -m tools.backup load <path>", file=sys.stderr)
            sys.exit(1)
        load(sys.argv[2])