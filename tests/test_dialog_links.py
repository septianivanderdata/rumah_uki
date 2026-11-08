import json
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path

from server import create_app
import test_admin as helpers


class DialogLinkTest(unittest.TestCase):
    setUp = helpers.AdminTest.setUp
    tearDown = helpers.AdminTest.tearDown
    send = helpers.AdminTest.send
    login_admin = helpers.AdminTest.setup

    def data(self):
        return self.client.get('/api/admin/dialog-links').json

    def link(self, **changes):
        return {'section': 'documents', 'title': 'Dokumen tambahan', 'url': 'https://example.org/report',
                'month': None, 'unit': '', 'position': 10, 'active': True,
                'revision': self.data()['revision'], **changes}

    def test_existing_links_migrated_once_and_accounts_preserved(self):
        self.login_admin()
        seed = json.loads(Path('dialog-seeds.json').read_text())
        self.assertEqual(len(self.data()['links']), 27)
        self.assertEqual([m['url'] for m in self.data()['links'] if m['url']], [m['url'] for m in sorted(seed, key=lambda m:m['position']) if m['url']])
        # Simulate the schema before this feature, with an existing administrator and menus.
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute('DROP TABLE dialog_links')
            conn.execute("DELETE FROM metadata WHERE key='dialog_revision'")
            conn.execute("UPDATE menus SET title='Menu pegawai' WHERE id=1")
        new = create_app(self.config).test_client()
        self.assertEqual(len(new.get('/api/dialog-links').json['links']), 27)
        self.assertEqual(new.get('/api/menus').json['menus'][0]['title'], 'Menu pegawai')
        self.assertTrue(self.client.get('/api/admin/session').json['authenticated'])
        create_app(self.config)
        self.assertEqual(len(self.data()['links']), 27)

    def test_authentication_and_csrf(self):
        self.assertEqual(self.client.get('/api/admin/dialog-links').status_code, 401)
        self.assertEqual(self.send('dialog-links').status_code, 401)
        self.login_admin()
        self.assertEqual(self.send('dialog-links', data=self.link(), headers=self.origin).status_code, 403)
        self.assertEqual(self.send('dialog-links', data=self.link(), headers={'Origin':'https://evil.example','X-CSRF-Token':self.csrf}).status_code, 403)
        self.assertEqual(self.client.get('/api/dialog-links').status_code, 200)

    def test_document_crud_hide_order_and_shared_visitor(self):
        self.login_admin()
        response = self.send('dialog-links',data=self.link())
        self.assertEqual(response.status_code,200)
        added = next(l for l in response.json['links'] if l['title']=='Dokumen tambahan')
        visitor = self.app.test_client()
        self.assertIn(added['id'],[l['id'] for l in visitor.get('/api/dialog-links').json['links']])
        hidden = self.send(f"dialog-links/{added['id']}",'PUT',self.link(title='Dokumen diubah',active=False))
        self.assertEqual(hidden.status_code,200)
        self.assertNotIn(added['id'],[l['id'] for l in visitor.get('/api/dialog-links').json['links']])
        ids = [l['id'] for l in self.data()['links'] if l['section']=='documents'][::-1]
        reordered=self.send('dialog-links/reorder',data={'ids':ids,'section':'documents','revision':self.data()['revision']})
        self.assertEqual(reordered.status_code,200)
        self.assertEqual([l['id'] for l in reordered.json['links'] if l['section']=='documents'],ids)
        self.assertEqual(self.send(f"dialog-links/{added['id']}",'DELETE',{'revision':self.data()['revision']}).status_code,200)

    def test_monthly_folders_unique_and_optional_unavailable(self):
        self.login_admin()
        may = next(l for l in self.data()['links'] if l['month']==5)
        updated=self.send(f"dialog-links/{may['id']}",'PUT',self.link(section='monthly',month=5,title='Ignored',url='https://example.org/may'))
        self.assertEqual(updated.status_code,200)
        link=next(l for l in updated.json['links'] if l['id']==may['id'])
        self.assertEqual(link['title'],'Mei')
        self.assertEqual(link['position'],4)
        self.assertEqual(self.send('dialog-links',data=self.link(section='monthly',month=5)).status_code,409)
        self.assertEqual(self.send(f"dialog-links/{may['id']}",'PUT',self.link(section='monthly',month=5,url='')).status_code,200)
        self.assertEqual(self.send(f"dialog-links/{may['id']}",'DELETE',{'revision':self.data()['revision']}).status_code,200)
        self.assertEqual(self.send('dialog-links',data=self.link(section='monthly',month=5,url='')).status_code,200)
        self.assertEqual(len([l for l in self.data()['links'] if l['section']=='monthly']),12)

    def test_new_unit_reports_and_validation(self):
        self.login_admin()
        self.assertEqual(self.send('dialog-links',data=self.link(section='units',unit='Unit baru')).status_code,200)
        for changes in [{'section':'unknown'},{'section':'units','unit':''},{'section':'monthly','month':0},{'section':'monthly','month':True},{'url':'javascript:alert(1)'},{'url':'https://[invalid'},{'url':''},{'title':''},{'active':'false'},{'position':-1},{'unit':'x'*161}]:
            with self.subTest(changes=changes):
                self.assertEqual(self.send('dialog-links',data=self.link(**changes)).status_code,400)

    def test_independent_revisions_conflicts_and_persistence(self):
        self.login_admin()
        navigation=self.client.get('/api/admin/menus').json
        old=self.link()
        self.assertEqual(self.send('dialog-links',data=old).status_code,200)
        self.assertEqual(self.client.get('/api/admin/menus').json,navigation)
        self.assertEqual(self.send('dialog-links',data=old).status_code,409)
        self.assertEqual(self.send('dialog-links/reorder',data={'section':'documents','ids':[],'revision':self.data()['revision']}).status_code,409)
        self.assertEqual(self.send('dialog-links/999','DELETE',{'revision':self.data()['revision']}).status_code,404)
        self.assertEqual(len(create_app(self.config).test_client().get('/api/dialog-links').json['links']),28)
        for link in self.data()['links']:
            self.send(f"dialog-links/{link['id']}",'DELETE',{'revision':self.data()['revision']})
        self.assertEqual(create_app(self.config).test_client().get('/api/dialog-links').json['links'],[])


if __name__=='__main__':
    unittest.main()
