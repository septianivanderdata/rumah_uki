"""Database migration and authenticated administration for Dialog Kinerja links."""
import json
import sqlite3
from pathlib import Path

FIELDS = ('section', 'title', 'url', 'month', 'unit', 'position', 'active')
MONTHS = ('Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember')


def init_dialog(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS dialog_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section TEXT NOT NULL CHECK(section IN ('documents','monthly','units')),
        title TEXT NOT NULL, url TEXT NOT NULL, month INTEGER,
        unit TEXT NOT NULL, position INTEGER NOT NULL,
        active INTEGER NOT NULL CHECK(active IN (0,1))
    )''')
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS dialog_month ON dialog_links(month) WHERE section='monthly'")
    if not conn.execute("SELECT 1 FROM metadata WHERE key='dialog_revision'").fetchone():
        seeds = json.loads(Path(__file__).with_name('dialog-seeds.json').read_text())
        conn.executemany(f"INSERT INTO dialog_links ({','.join(FIELDS)}) VALUES ({','.join('?' for _ in FIELDS)})",
                         [[item[field] for field in FIELDS] for item in seeds])
        conn.execute("INSERT INTO metadata VALUES ('dialog_revision',1)")


def register_dialog_routes(app, db, auth, body, error, validate_url):
    from flask import jsonify

    def validate(data):
        section = data.get('section')
        if section not in ('documents', 'monthly', 'units'):
            raise error('Pilih bagian Dialog Kinerja yang tersedia.')
        result = {'section': section}
        for key, limit in [('title', 80), ('url', 2048), ('unit', 160)]:
            value = data.get(key)
            if not isinstance(value, str) or len(value.strip()) > limit or any(ord(c) < 32 for c in value):
                raise error('Nama dokumen, unit, atau tautan tidak valid atau terlalu panjang.')
            result[key] = value.strip()
        month = data.get('month')
        if section == 'monthly':
            if type(month) is not int or not 1 <= month <= 12:
                raise error('Pilih bulan yang valid.')
            result.update(month=month, title=MONTHS[month - 1], unit='', position=month - 1)
        else:
            result['month'] = None
            if not result['title']:
                raise error('Nama dokumen wajib diisi.')
            if type(data.get('position')) is not int or not 0 <= data['position'] <= 10000:
                raise error('Urutan harus angka bulat antara 0 dan 10000.')
            result['position'] = data['position']
            if section == 'units' and not result['unit']:
                raise error('Nama unit kerja wajib diisi.')
            if section == 'documents':
                result['unit'] = ''
        if result['url']:
            validate_url(result['url'])
        elif section != 'monthly':
            raise error('Tautan dokumen wajib diisi.')
        if type(data.get('active')) is not bool:
            raise error('Pilihan tampilan tidak valid.')
        result['active'] = int(data['active'])
        return result

    def dataset(public=False):
        conn = db(); conn.execute('BEGIN')
        rows = conn.execute('SELECT * FROM dialog_links' + (' WHERE active=1' if public else '') + ' ORDER BY position,id')
        links = [dict(row) for row in rows]
        for link in links:
            link['active'] = bool(link['active'])
        revision = conn.execute("SELECT value FROM metadata WHERE key='dialog_revision'").fetchone()[0]
        conn.commit()
        return dict(links=links, revision=revision)

    def begin(data):
        conn = db(); conn.execute('BEGIN IMMEDIATE')
        revision = conn.execute("SELECT value FROM metadata WHERE key='dialog_revision'").fetchone()[0]
        if type(data.get('revision')) is not int or data['revision'] != revision:
            conn.rollback()
            raise error('Tautan telah diubah di sesi lain. Muat ulang daftar sebelum menyimpan.', 409)
        return conn

    def finish(conn):
        conn.execute("UPDATE metadata SET value=value+1 WHERE key='dialog_revision'")
        conn.commit()
        return jsonify(dataset())

    def save(data, link_id=None):
        link = validate(data); conn = begin(data)
        try:
            if link_id is None:
                if conn.execute('SELECT COUNT(*) FROM dialog_links').fetchone()[0] >= 300:
                    conn.rollback(); raise error('Batas 300 tautan tercapai.')
                conn.execute(f"INSERT INTO dialog_links ({','.join(FIELDS)}) VALUES ({','.join('?' for _ in FIELDS)})", [link[k] for k in FIELDS])
            else:
                row = conn.execute(f"UPDATE dialog_links SET {','.join(k+'=?' for k in FIELDS)} WHERE id=?", [link[k] for k in FIELDS] + [link_id])
                if not row.rowcount:
                    conn.rollback(); raise error('Tautan tidak ditemukan.', 404)
        except sqlite3.IntegrityError:
            conn.rollback()
            raise error('Bulan tersebut sudah ada. Edit tautan bulan yang tersedia dalam daftar.', 409) from None
        return finish(conn)

    @app.get('/api/dialog-links')
    def public_dialog_links():
        return jsonify(dataset(True))

    @app.get('/api/admin/dialog-links')
    def admin_dialog_links():
        auth()
        return jsonify(dataset())

    @app.post('/api/admin/dialog-links')
    def add_dialog_link():
        auth()
        return save(body())

    @app.put('/api/admin/dialog-links/<int:link_id>')
    def edit_dialog_link(link_id):
        auth()
        return save(body(), link_id)

    @app.delete('/api/admin/dialog-links/<int:link_id>')
    def delete_dialog_link(link_id):
        auth(); conn = begin(body())
        if not conn.execute('DELETE FROM dialog_links WHERE id=?', (link_id,)).rowcount:
            conn.rollback(); raise error('Tautan tidak ditemukan.', 404)
        return finish(conn)

    @app.post('/api/admin/dialog-links/reorder')
    def reorder_dialog_links():
        auth(); data = body(); section = data.get('section'); ids = data.get('ids')
        if section not in ('documents', 'units') or not isinstance(ids, list) or not all(type(i) is int for i in ids) or len(ids) > 300:
            raise error('Urutan tautan tidak valid. Folder bulanan mengikuti urutan kalender.')
        conn = begin(data)
        existing = {row[0] for row in conn.execute('SELECT id FROM dialog_links WHERE section=?', (section,))}
        if len(ids) != len(existing) or set(ids) != existing:
            conn.rollback(); raise error('Daftar tautan berubah. Muat ulang sebelum mengurutkan.', 409)
        conn.executemany('UPDATE dialog_links SET position=? WHERE id=?', enumerate(ids))
        return finish(conn)
