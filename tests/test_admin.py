import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path

from server import create_app


class AdminTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'uki.sqlite3'
        self.config = {'TESTING': True, 'DATABASE': str(self.path), 'ALLOW_LOCAL_SETUP': True}
        self.app = create_app(self.config)
        self.client = self.app.test_client()
        self.origin = {'Origin': 'http://localhost'}
        self.csrf = ''

    def tearDown(self):
        self.temp.cleanup()

    def send(self, path, method='POST', data=None, headers=None):
        return self.client.open('/api/admin/' + path, method=method, json=data or {},
            headers=headers if headers is not None else {**self.origin, 'X-CSRF-Token': self.csrf})

    def setup(self):
        response = self.send('setup', data={'username': 'admin', 'password': 'test-password-unique'})
        self.assertEqual(response.status_code, 200)
        self.csrf = response.json['csrf']
        return response

    def dataset(self):
        return self.client.get('/api/admin/menus').json

    def menu(self, **changes):
        return {'title': 'Panduan baru', 'url': 'https://example.org/panduan',
                'description': 'Panduan untuk pegawai', 'category': 'Panduan', 'icon': 'link',
                'position': 4, 'active': True, 'show_nav': True, 'show_card': True,
                'revision': self.dataset()['revision'], **changes}

    def test_setup_login_logout_and_no_default_password(self):
        self.assertTrue(self.client.get('/api/admin/session').json['setup_available'])
        response = self.setup()
        self.assertIn('HttpOnly', response.headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', response.headers['Set-Cookie'])
        self.assertFalse(self.send('setup', data={'username': 'other', 'password': 'long-enough-password'}).status_code == 200)
        self.assertTrue(self.client.get('/api/admin/session').json['authenticated'])
        self.assertEqual(self.send('logout').status_code, 200)
        self.assertEqual(self.client.get('/api/admin/menus').status_code, 401)
        self.csrf = ''
        self.assertEqual(self.send('login', data={'username': 'admin', 'password': 'wrong'}).status_code, 401)
        self.assertEqual(self.send('login', data={'username': 'admin', 'password': 'test-password-unique'}).status_code, 200)
        with closing(sqlite3.connect(self.path)) as conn, conn:
            stored = conn.execute('SELECT password_hash FROM admins').fetchone()[0]
        self.assertNotEqual(stored, 'test-password-unique')
        self.assertTrue(stored.startswith('scrypt:'))

    def test_setup_is_local_only_and_disabled_in_production(self):
        response = self.client.post('/api/admin/setup', json={'username': 'admin', 'password': 'test-password-unique'}, headers=self.origin, environ_overrides={'REMOTE_ADDR': '192.0.2.10'})
        self.assertEqual(response.status_code, 403)
        production = create_app({**self.config, 'ALLOW_LOCAL_SETUP': False, 'PUBLIC_ORIGIN': 'https://portal.example.org'})
        self.assertFalse(production.test_client().get('/api/admin/session').json['setup_available'])
        self.assertEqual(production.test_client().post('/api/admin/setup', json={'username': 'admin', 'password': 'test-password-unique'}, headers={'Origin': 'https://portal.example.org'}).status_code, 403)

    def test_auth_origin_and_csrf_required(self):
        self.assertEqual(self.send('menus').status_code, 401)
        self.setup()
        self.assertEqual(self.send('menus', data=self.menu(), headers={'Origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(self.send('menus', data=self.menu(), headers=self.origin).status_code, 403)
        self.assertEqual(self.send('menus', data=self.menu(), headers={'X-CSRF-Token': self.csrf}).status_code, 403)
        self.assertEqual(self.client.post('/api/admin/menus', data='raw', headers=self.origin).status_code, 415)
        self.assertEqual(self.client.get('/api/menus').status_code, 200)

    def test_crud_hide_reorder_and_separate_visitors(self):
        self.setup()
        response = self.send('menus', data=self.menu())
        self.assertEqual(response.status_code, 200)
        created = response.json['menus'][-1]
        visitor = self.app.test_client()
        self.assertIn(created['id'], [m['id'] for m in visitor.get('/api/menus').json['menus']])
        hidden = self.send(f"menus/{created['id']}", 'PUT', self.menu(title='Nama baru', active=False))
        self.assertEqual(hidden.status_code, 200)
        self.assertNotIn(created['id'], [m['id'] for m in visitor.get('/api/menus').json['menus']])
        current = self.dataset(); ids = [m['id'] for m in current['menus']][::-1]
        ordered = self.send('reorder', data={'ids': ids, 'revision': current['revision']})
        self.assertEqual(ordered.status_code, 200)
        self.assertEqual([m['id'] for m in ordered.json['menus']], ids)
        deleted = self.send(f"menus/{created['id']}", 'DELETE', {'revision': self.dataset()['revision']})
        self.assertEqual(deleted.status_code, 200)
        self.assertNotIn(created['id'], [m['id'] for m in deleted.json['menus']])

    def test_stale_edits_rejected_without_overwriting(self):
        self.setup(); stale = self.menu()
        self.assertEqual(self.send('menus', data=stale).status_code, 200)
        self.assertEqual(self.send('menus', data=stale).status_code, 409)
        current = self.dataset()
        bad = self.send('reorder', data={'ids': [1, 1], 'revision': current['revision']})
        self.assertEqual(bad.status_code, 409)
        self.assertEqual(self.dataset(), current)
        missing = self.send('menus/999', 'DELETE', {'revision': current['revision']})
        self.assertEqual(missing.status_code, 404)

    def test_rejects_unsafe_urls_and_malformed_values(self):
        self.setup()
        for url in ['javascript:alert(1)', 'data:text/html,test', '//evil.example', 'http://example.org', 'https://user:pass@example.org', 'https://', '../server.py', 'https://[bad', 'https://example.org/with space']:
            with self.subTest(url=url):
                self.assertEqual(self.send('menus', data=self.menu(url=url)).status_code, 400)
        for field, value in [('title', ''), ('title', 10), ('title', 'x' * 81), ('position', True), ('position', -1), ('active', 'false'), ('icon', 'unknown')]:
            with self.subTest(field=field, value=value):
                self.assertEqual(self.send('menus', data=self.menu(**{field: value})).status_code, 400)
        self.assertEqual(self.client.post('/api/admin/menus', json=[], headers={**self.origin, 'X-CSRF-Token': self.csrf}).status_code, 400)
        self.assertEqual(self.send('menus', data=self.menu(url='lhk.html', description='Baris pertama\nBaris kedua')).status_code, 200)
        self.assertEqual(self.send('menus', data=self.menu(url='index.html#tentang')).status_code, 200)

    def test_persistence_and_empty_dataset_not_reseeded(self):
        self.setup()
        self.send('menus', data=self.menu())
        second = create_app(self.config).test_client()
        self.assertEqual(len(second.get('/api/menus').json['menus']), 5)
        for menu in self.dataset()['menus']:
            self.send(f"menus/{menu['id']}", 'DELETE', {'revision': self.dataset()['revision']})
        self.assertEqual(create_app(self.config).test_client().get('/api/menus').json['menus'], [])

    def test_private_files_and_admin_cache(self):
        for url in ['/server.py', '/.git/config', '/.data/uki.sqlite3', '/requirements.txt', '/assets/../server.py']:
            self.assertEqual(self.client.get(url).status_code, 404, url)
        response = self.client.get('/admin')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertIn("frame-ancestors 'none'", response.headers['Content-Security-Policy'])
        with self.client.get('/assets/admin.js') as asset_response:
            self.assertEqual(asset_response.status_code, 200)
        response.close()

    def test_expired_sessions_and_login_rate_limit(self):
        self.setup()
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute('UPDATE sessions SET expires=0')
        self.assertEqual(self.client.get('/api/admin/menus').status_code, 401)
        for _ in range(10):
            self.assertEqual(self.send('login', data={'username': 'admin', 'password': 'wrong'}).status_code, 401)
        self.assertEqual(self.send('login', data={'username': 'admin', 'password': 'test-password-unique'}).status_code, 429)

    def test_secure_session_for_https(self):
        self.setup()
        production = create_app({**self.config, 'PUBLIC_ORIGIN': 'https://portal.example.org', 'ALLOW_LOCAL_SETUP': False})
        response = production.test_client().post('/api/admin/login', json={'username': 'admin', 'password': 'test-password-unique'}, headers={'Origin': 'https://portal.example.org'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Secure', response.headers['Set-Cookie'])


if __name__ == '__main__':
    unittest.main()
