"""UKI menu API. Local preview: python3 server.py. See README.md for hosting."""
import argparse
from contextlib import closing
import getpass
import hashlib
import hmac
import ipaddress
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlsplit

from dialog_links import init_dialog, register_dialog_routes

from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

ROOT = Path(__file__).resolve().parent
FIELDS = ('title', 'url', 'description', 'category', 'icon', 'position', 'active', 'show_nav', 'show_card')
SEEDS = [
    ('Beranda', 'index.html', 'Halaman utama portal Unit Kepatuhan Internal.', 'Portal', 'document', 0, 1, 1, 0),
    ('Harta kekayaan', 'lhk.html', 'Panduan pelaporan LHKPN, LHK, dan penyampaian bukti lapor pegawai.', 'Pelaporan', 'document', 1, 1, 1, 1),
    ('Kinerja pegawai', 'pengelolaan-kinerja.html', 'Perjanjian kinerja, indikator, dan dokumen pendukung dalam satu tempat.', 'Pengelolaan', 'chart', 2, 1, 1, 1),
    ('Dialog kinerja', 'dialog-kinerja.html', 'Bahan dialog, laporan risiko, dan capaian kinerja setiap unit kerja.', 'Koordinasi', 'dialogue', 3, 1, 1, 1),
]


class APIError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


def db():
    if 'db' not in g:
        g.db = sqlite3.connect(g.app_database, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db


def init_database(path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY, admin_id INTEGER NOT NULL REFERENCES admins(id),
            csrf TEXT NOT NULL, expires REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS menus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, url TEXT NOT NULL, description TEXT NOT NULL,
            category TEXT NOT NULL, icon TEXT NOT NULL, position INTEGER NOT NULL,
            active INTEGER NOT NULL, show_nav INTEGER NOT NULL, show_card INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS login_attempts (address TEXT PRIMARY KEY, count INTEGER NOT NULL, expires REAL NOT NULL);
        ''')
        conn.execute('BEGIN IMMEDIATE')
        # A marker prevents deleted menus being resurrected after a server restart.
        if not conn.execute("SELECT 1 FROM metadata WHERE key='revision'").fetchone():
            conn.executemany(f"INSERT INTO menus ({','.join(FIELDS)}) VALUES ({','.join('?' for _ in FIELDS)})", SEEDS)
            conn.execute("INSERT INTO metadata VALUES ('revision', 1)")
        init_dialog(conn)
    path.chmod(0o600)


def credentials(data):
    username, password = data.get('username'), data.get('password')
    if not isinstance(username, str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{3,60}', username):
        raise APIError('Nama pengguna harus 3–60 karakter: huruf, angka, titik, garis bawah, atau tanda minus.')
    if not isinstance(password, str) or not 12 <= len(password) <= 256:
        raise APIError('Gunakan kata sandi dengan panjang 12–256 karakter.')
    return username.lower(), password


def validate_destination(url):
    try:
        parsed = urlsplit(url)
        parsed.port  # Validate ports as well as bracketed hostnames.
    except ValueError:
        raise APIError('Gunakan tautan tujuan yang valid.') from None
    # Absolute HTTPS destinations or local portal pages only; never executable schemes.
    if parsed.scheme == 'https':
        if not parsed.hostname or parsed.username or parsed.password or '\\' in url or any(c.isspace() for c in url):
            raise APIError('Gunakan tautan HTTPS yang valid tanpa kredensial.')
    elif parsed.scheme or parsed.netloc or not re.fullmatch(r'(?:index|lhk|pengelolaan-kinerja|dialog-kinerja)\.html(?:#[a-zA-Z0-9_-]+)?', url):
        raise APIError('Gunakan tautan https:// atau halaman portal seperti lhk.html.')


def validate_menu(data):
    result = {}
    for field, limit in [('title', 80), ('url', 2048), ('description', 500), ('category', 40)]:
        value = data.get(field)
        if not isinstance(value, str) or len(value.strip()) > limit or any(ord(c) < 32 and not (field == 'description' and c in '\n\r\t') for c in value):
            raise APIError(f'Kolom {field} tidak valid atau terlalu panjang.')
        result[field] = value.strip()
    if not result['title'] or not result['url']:
        raise APIError('Nama menu dan tautan tujuan wajib diisi.')
    validate_destination(result['url'])
    if data.get('icon') not in ('document', 'chart', 'dialogue', 'link'):
        raise APIError('Pilih ilustrasi menu yang tersedia.')
    result['icon'] = data['icon']
    if type(data.get('position')) is not int or not 0 <= data['position'] <= 10000:
        raise APIError('Urutan harus angka bulat antara 0 dan 10000.')
    result['position'] = data['position']
    for field in ('active', 'show_nav', 'show_card'):
        if type(data.get(field)) is not bool:
            raise APIError('Pilihan tampilan menu tidak valid.')
        result[field] = int(data[field])
    return result


def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(
        DATABASE=os.environ.get('UKI_DATABASE', str(ROOT / '.data' / 'uki.sqlite3')),
        PUBLIC_ORIGIN=os.environ.get('UKI_PUBLIC_ORIGIN', '').rstrip('/'),
        ALLOW_LOCAL_SETUP=False,
        MAX_CONTENT_LENGTH=16384,
        SESSION_SECONDS=8 * 60 * 60,
    )
    if config:
        app.config.update(config)
    origin = app.config['PUBLIC_ORIGIN']
    if origin:
        parsed_origin = urlsplit(origin)
        if (parsed_origin.scheme != 'https' or not parsed_origin.hostname
                or parsed_origin.path or parsed_origin.query or parsed_origin.fragment
                or parsed_origin.username or parsed_origin.password):
            raise ValueError('UKI_PUBLIC_ORIGIN must be an HTTPS origin without a path.')
    init_database(Path(app.config['DATABASE']))

    @app.before_request
    def prepare():
        g.app_database = app.config['DATABASE']
        if request.path.startswith('/api/') and request.method not in ('GET', 'HEAD', 'OPTIONS'):
            expected = origin or request.host_url.rstrip('/')
            if request.headers.get('Origin') != expected:
                raise APIError('Permintaan berasal dari situs lain. Buka panel admin dari alamat portal.', 403)
            if request.mimetype != 'application/json':
                raise APIError('Permintaan harus berupa JSON.', 415)

    @app.teardown_appcontext
    def close_database(_error):
        conn = g.pop('db', None)
        if conn is not None:
            conn.close()

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        if request.path.startswith('/api/') or request.path.startswith('/admin'):
            response.headers['Cache-Control'] = 'no-store'
        if request.path.startswith('/admin'):
            response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response

    @app.errorhandler(APIError)
    def api_error(error):
        return jsonify(error=error.message), error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith('/api/'):
            return jsonify(error='Permintaan tidak valid.' if error.code != 413 else 'Data terlalu besar.'), error.code
        return error

    def body():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise APIError('Data formulir tidak valid.')
        return data

    def local_setup_allowed():
        try:
            local_client = ipaddress.ip_address(request.remote_addr or '').is_loopback
        except ValueError:
            local_client = False
        return (app.config['ALLOW_LOCAL_SETUP'] and local_client
                and request.host.split(':')[0] in ('127.0.0.1', 'localhost')
                and not db().execute('SELECT 1 FROM admins LIMIT 1').fetchone())

    def auth(required=True):
        token = request.cookies.get('uki_session', '')
        if len(token) > 200:
            token = ''
        digest = hashlib.sha256(token.encode()).hexdigest()
        row = db().execute('''SELECT sessions.*, admins.username FROM sessions
             JOIN admins ON admins.id=sessions.admin_id WHERE token_hash=? AND expires>?''',
             (digest, time.time())).fetchone()
        if required and not row:
            raise APIError('Sesi berakhir. Silakan masuk kembali.', 401)
        if row and request.method not in ('GET', 'HEAD'):
            if not hmac.compare_digest(request.headers.get('X-CSRF-Token', '').encode(), row['csrf'].encode()):
                raise APIError('Sesi formulir tidak valid. Muat ulang panel admin.', 403)
        return row

    def session_response(admin_id, username):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        expires = time.time() + app.config['SESSION_SECONDS']
        conn = db()
        conn.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
        conn.execute('INSERT INTO sessions VALUES (?, ?, ?, ?)',
                     (hashlib.sha256(token.encode()).hexdigest(), admin_id, csrf, expires))
        conn.commit()
        response = jsonify(authenticated=True, username=username, csrf=csrf)
        response.set_cookie('uki_session', token, max_age=app.config['SESSION_SECONDS'], httponly=True,
                            secure=bool(origin), samesite='Strict', path='/')
        return response

    def dataset(public=False):
        sql = 'SELECT * FROM menus' + (' WHERE active=1' if public else '') + ' ORDER BY position,id'
        conn = db()
        conn.execute('BEGIN')
        menus = [dict(row) for row in conn.execute(sql)]
        for menu in menus:
            for key in ('active', 'show_nav', 'show_card'):
                menu[key] = bool(menu[key])
        revision = conn.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]
        conn.commit()
        return dict(menus=menus, revision=revision)

    def begin_edit(data):
        conn = db()
        conn.execute('BEGIN IMMEDIATE')
        revision = conn.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]
        if type(data.get('revision')) is not int or data['revision'] != revision:
            conn.rollback()
            raise APIError('Menu telah diubah di sesi lain. Muat ulang daftar sebelum menyimpan.', 409)
        return conn

    def finish_edit(conn):
        conn.execute("UPDATE metadata SET value=value+1 WHERE key='revision'")
        conn.commit()
        return jsonify(dataset())

    @app.get('/api/menus')
    def public_menus():
        return jsonify(dataset(True))

    @app.get('/api/admin/session')
    def session_info():
        row = auth(False)
        if row:
            return jsonify(authenticated=True, username=row['username'], csrf=row['csrf'])
        return jsonify(authenticated=False, setup_available=bool(local_setup_allowed()))

    @app.post('/api/admin/setup')
    def setup():
        if not local_setup_allowed():
            raise APIError('Pembuatan akun pertama hanya tersedia secara lokal sebelum akun admin dibuat.', 403)
        username, password = credentials(body())
        hashed = generate_password_hash(password, method='scrypt')
        conn = db()
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT 1 FROM admins LIMIT 1').fetchone():
            conn.rollback()
            raise APIError('Akun admin sudah dibuat. Silakan masuk.', 409)
        row = conn.execute('INSERT INTO admins (username,password_hash) VALUES (?,?)', (username, hashed))
        conn.commit()
        return session_response(row.lastrowid, username)

    @app.post('/api/admin/login')
    def login():
        data = body()
        username, password = data.get('username'), data.get('password')
        if not isinstance(username, str) or not isinstance(password, str) or len(username) > 60 or len(password) > 256:
            raise APIError('Nama pengguna atau kata sandi salah.', 401)
        address, now = request.remote_addr or 'unknown', time.time()
        conn = db()
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('DELETE FROM login_attempts WHERE expires<?', (now,))
        attempt = conn.execute('SELECT * FROM login_attempts WHERE address=?', (address,)).fetchone()
        if attempt and attempt['count'] >= 10:
            conn.rollback()
            raise APIError('Terlalu banyak percobaan masuk. Coba lagi dalam 15 menit.', 429)
        conn.execute('''INSERT INTO login_attempts VALUES (?,1,?) ON CONFLICT(address)
                        DO UPDATE SET count=count+1''', (address, now + 900))
        conn.commit()
        user = conn.execute('SELECT * FROM admins WHERE username=?', (username.lower(),)).fetchone()
        # Perform a comparable hash check even for an unknown user.
        hashed = user['password_hash'] if user else app.config['DUMMY_PASSWORD_HASH']
        if not check_password_hash(hashed, password) or not user:
            raise APIError('Nama pengguna atau kata sandi salah.', 401)
        conn.execute('DELETE FROM login_attempts WHERE address=?', (address,)); conn.commit()
        previous = request.cookies.get('uki_session')
        if previous:
            conn.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(previous.encode()).hexdigest(),)); conn.commit()
        return session_response(user['id'], user['username'])

    @app.post('/api/admin/logout')
    def logout():
        row = auth()
        conn = db(); conn.execute('DELETE FROM sessions WHERE token_hash=?', (row['token_hash'],)); conn.commit()
        response = jsonify(authenticated=False)
        response.delete_cookie('uki_session', path='/', samesite='Strict', secure=bool(origin))
        return response

    @app.get('/api/admin/menus')
    def admin_menus():
        auth()
        return jsonify(dataset())

    @app.post('/api/admin/menus')
    def add_menu():
        auth(); data = body(); menu = validate_menu(data)
        conn = begin_edit(data)
        if conn.execute('SELECT COUNT(*) FROM menus').fetchone()[0] >= 100:
            conn.rollback(); raise APIError('Batas 100 menu tercapai.')
        conn.execute(f"INSERT INTO menus ({','.join(FIELDS)}) VALUES ({','.join('?' for _ in FIELDS)})", [menu[k] for k in FIELDS])
        return finish_edit(conn)

    @app.put('/api/admin/menus/<int:menu_id>')
    def edit_menu(menu_id):
        auth(); data = body(); menu = validate_menu(data); conn = begin_edit(data)
        row = conn.execute(f"UPDATE menus SET {','.join(k+'=?' for k in FIELDS)} WHERE id=?", [menu[k] for k in FIELDS] + [menu_id])
        if not row.rowcount:
            conn.rollback(); raise APIError('Menu tidak ditemukan.', 404)
        return finish_edit(conn)

    @app.delete('/api/admin/menus/<int:menu_id>')
    def delete_menu(menu_id):
        auth(); conn = begin_edit(body())
        if not conn.execute('DELETE FROM menus WHERE id=?', (menu_id,)).rowcount:
            conn.rollback(); raise APIError('Menu tidak ditemukan.', 404)
        return finish_edit(conn)

    @app.post('/api/admin/reorder')
    def reorder_menus():
        auth(); data = body(); ids = data.get('ids')
        if not isinstance(ids, list) or not all(type(i) is int for i in ids) or len(ids) > 100:
            raise APIError('Urutan menu tidak valid.')
        conn = begin_edit(data)
        existing = {row[0] for row in conn.execute('SELECT id FROM menus')}
        if len(ids) != len(existing) or set(ids) != existing:
            conn.rollback(); raise APIError('Daftar menu berubah. Muat ulang sebelum mengurutkan.', 409)
        conn.executemany('UPDATE menus SET position=? WHERE id=?', enumerate(ids))
        return finish_edit(conn)

    @app.get('/')
    def home():
        return send_from_directory(ROOT, 'index.html')

    @app.get('/admin')
    @app.get('/admin/')
    @app.get('/admin.html')
    def admin_page():
        return send_from_directory(ROOT, 'admin.html')

    @app.get('/<page>')
    def portal_page(page):
        if page not in ('index.html', 'lhk.html', 'pengelolaan-kinerja.html', 'dialog-kinerja.html'):
            raise APIError('Halaman tidak ditemukan.', 404)
        return send_from_directory(ROOT, page)

    @app.get('/assets/<path:filename>')
    def assets(filename):
        if any(part.startswith('.') for part in Path(filename).parts):
            raise APIError('Berkas tidak ditemukan.', 404)
        return send_from_directory(ROOT / 'assets', filename)

    register_dialog_routes(app, db, auth, body, APIError, validate_destination)

    app.config['DUMMY_PASSWORD_HASH'] = generate_password_hash(secrets.token_urlsafe(24), method='scrypt')
    return app


def manage_admin(app, username):
    password = getpass.getpass('Kata sandi baru (minimal 12 karakter): ')
    if password != getpass.getpass('Ulangi kata sandi: '):
        raise SystemExit('Kata sandi tidak cocok.')
    username, password = credentials(dict(username=username, password=password))
    with closing(sqlite3.connect(app.config['DATABASE'])) as conn, conn:
        conn.execute('''INSERT INTO admins (username,password_hash) VALUES (?,?)
                        ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash''',
                     (username, generate_password_hash(password, method='scrypt')))
        conn.execute('DELETE FROM sessions WHERE admin_id=(SELECT id FROM admins WHERE username=?)', (username,))
    print('Akun admin tersimpan. Sesi lama akun tersebut telah diakhiri.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--database', help='Override the private SQLite database path')
    parser.add_argument('--admin', help='Create or reset an administrator from the server terminal')
    args = parser.parse_args()
    settings = {'ALLOW_LOCAL_SETUP': args.host in ('127.0.0.1', 'localhost')}
    if args.database:
        settings['DATABASE'] = args.database
    app = create_app(settings)
    if args.admin:
        manage_admin(app, args.admin)
    else:
        print(f'Portal: http://{args.host}:{args.port}/ — Admin: http://{args.host}:{args.port}/admin', flush=True)
        app.run(host=args.host, port=args.port, debug=False)
