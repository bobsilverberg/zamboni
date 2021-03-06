import collections

from nose.tools import eq_, ok_


import amo
from amo.utils import attach_trans_dict
from addons.models import Addon


class TestAttachTransDict(amo.tests.TestCase):
    """
    Tests for attach_trans_dict. For convenience, we re-use Addon model instead
    of mocking one from scratch and we rely on internal Translation unicode
    implementation, because mocking django models and fields is just painful.
    """

    def test_basic(self):
        addon = amo.tests.addon_factory(
            name='Name', description='Description <script>alert(42)</script>!',
            eula='', summary='Summary', homepage='http://home.pa.ge',
            developer_comments='Developer Comments', privacy_policy='Policy',
            support_email='sup@example.com', support_url='http://su.pport.url')
        addon.save()

        # Quick sanity checks: is description properly escaped? The underlying
        # implementation should leave localized_string un-escaped but never use
        # it for __unicode__. We depend on this behaviour later in the test.
        ok_('<script>' in addon.description.localized_string)
        ok_(not '<script>' in addon.description.localized_string_clean)
        ok_(not '<script>' in unicode(addon.description))

        # Attach trans dict.
        attach_trans_dict(Addon, [addon])
        ok_(isinstance(addon.translations, collections.defaultdict))
        translations = dict(addon.translations)

        # addon.translations is a defaultdict.
        eq_(addon.translations['whatever'], [])

        # No-translated fields should be absent.
        eq_(addon.thankyou_note_id, None)
        ok_(None not in translations)

        # Build expected translations dict.
        expected_translations = {
            addon.eula_id: [('en-us', unicode(addon.eula))],
            addon.privacy_policy_id:
                [('en-us', unicode(addon.privacy_policy))],
            addon.description_id: [
                ('en-us', unicode(addon.description))],
            addon.developer_comments_id:
                [('en-us', unicode(addon.developer_comments))],
            addon.summary_id: [('en-us', unicode(addon.summary))],
            addon.homepage_id: [('en-us', unicode(addon.homepage))],
            addon.name_id: [('en-us', unicode(addon.name))],
            addon.support_email_id: [('en-us', unicode(addon.support_email))],
            addon.support_url_id: [('en-us', unicode(addon.support_url))]
        }
        eq_(translations, expected_translations)

    def test_multiple_objects_with_multiple_translations(self):
        addon = amo.tests.addon_factory()
        addon.description = {
            'fr': 'French Description',
            'en-us': 'English Description'
        }
        addon.save()
        addon2 = amo.tests.addon_factory(description='English 2 Description')
        addon2.name = {
            'fr': 'French 2 Name',
            'en-us': 'English 2 Name',
            'es': 'Spanish 2 Name'
        }
        addon2.save()
        attach_trans_dict(Addon, [addon, addon2])
        eq_(set(addon.translations[addon.description_id]),
            set([('en-us', 'English Description'),
                 ('fr', 'French Description')]))
        eq_(set(addon2.translations[addon2.name_id]),
            set([('en-us', 'English 2 Name'),
                 ('es', 'Spanish 2 Name'),
                 ('fr', 'French 2 Name')]))


class TestRemoveLinks(amo.tests.TestCase):

    def test_remove_links(self):
        html = 'a <a href="http://example.com">link</a> with markup'
        eq_(amo.utils.remove_links(html), 'a  with markup')

        html = 'a http://example.com text link'
        eq_(amo.utils.remove_links(html), 'a  text link')

        html = ('a <a href="http://example.com" title="title" class="class" '
                'ref="ref">link</a> with markup and '
                'another link without markup: http://other.com, other stuff')
        eq_(amo.utils.remove_links(html),
            'a  with markup and another link without markup: , other stuff')
